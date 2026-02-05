# Skills API Specification

This document defines the interface contracts for all agent skills. Each skill is an autonomous function that agents call to perform specific actions within the Chimera system.

## Core Principles

- **Idempotent**: Same input produces same output (or idempotent side effects)
- **Typed**: Input/output schemas are JSON Schema compliant
- **Observable**: All calls logged with duration, error codes, retry attempts
- **Resilient**: Built-in retry logic with exponential backoff
- **Timeout-Safe**: All operations have explicit timeouts

---

## Skill Inventory

| Skill | Agent | Input | Output | Timeout | Error Codes |
|-------|-------|-------|--------|---------|-------------|
| fetch_trends | Trend Analyst | {platform, limit, timeWindow} | TrendData[] | 30s | PLATFORM_UNAVAILABLE, RATE_LIMITED, INVALID_PLATFORM |
| semantic_filter | Orchestrator | {trends, campaign_goals} | Trend[] | 10s | FILTER_TIMEOUT, INVALID_INPUT |
| generate_content | Content Creator | {trend, persona, platform} | ContentPackage | 45s | GENERATION_TIMEOUT, INVALID_PERSONA |
| validate_content | Judge | {content} | {valid: bool, issues: string[]} | 5s | VALIDATION_ERROR |
| publish_content | Distribution | {content, approval_token, platform} | {post_id, url} | 15s | PUBLISH_FAILED, INVALID_TOKEN |
| get_agent_profile | Orchestrator | {agent_id} | AgentProfile | 2s | AGENT_NOT_FOUND |
| update_agent_state | Orchestrator | {agent_id, state_updates} | AgentProfile | 5s | CONCURRENCY_ERROR, AGENT_NOT_FOUND |
| fetch_wallet_balance | CFO Judge | {wallet_address} | {balance: number, currency: string} | 5s | WALLET_ERROR, NETWORK_ERROR |
| debit_wallet | CFO Judge | {wallet_address, amount, tx_description} | {tx_id, success: bool} | 10s | INSUFFICIENT_BALANCE, TX_FAILED |
| register_openclaw_profile | Orchestrator | {agent_profile} | {registered: bool, profile_url: string} | 10s | REGISTRATION_FAILED |

---

## Skill Specifications

### 1. `fetch_trends`

**Agent**: Trend Analyst  
**Purpose**: Fetch trending topics from MCP resources

#### Input Schema
```json
{
  "platform": {
    "type": "string",
    "enum": ["twitter", "news", "market", "reddit", "tiktok"],
    "required": true,
    "description": "Social platform source"
  },
  "limit": {
    "type": "integer",
    "minimum": 1,
    "maximum": 500,
    "default": 50,
    "description": "Maximum trends to return"
  },
  "timeWindow": {
    "type": "string",
    "pattern": "^[0-9]+(h|d)$",
    "default": "24h",
    "required": false,
    "description": "Time window for trend detection (e.g., '4h', '1d')"
  },
  "minEngagement": {
    "type": "integer",
    "minimum": 0,
    "default": 10000,
    "required": false,
    "description": "Minimum engagement_score threshold"
  },
  "excludeTopics": {
    "type": "array",
    "items": { "type": "string" },
    "maxItems": 50,
    "required": false,
    "description": "Topics to explicitly filter out"
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "trends": {
      "type": "array",
      "items": { "$ref": "TrendData Schema from 2-design.md" }
    },
    "fetched_at": { "type": "string", "format": "ISO8601" },
    "platform": { "type": "string" },
    "count": { "type": "integer" },
    "truncated": {
      "type": "boolean",
      "description": "True if more trends available beyond limit"
    }
  }
}
```

#### Behavior
- **Timeout**: 30 seconds (10s per platform if multiple platforms)
- **Retry**: Up to 3 attempts with exponential backoff (1s, 2s, 4s)
- **Idempotency**: Same input within 5 minutes returns cached results
- **Fallback**: If primary platform unavailable, try fallback platform (e.g., twitter → twitter/feed/general)

#### Error Codes
| Code | HTTP | Recovery | Example |
|------|------|----------|---------|
| PLATFORM_UNAVAILABLE | 503 | Retry with fallback | Twitter API down |
| RATE_LIMITED | 429 | Exponential backoff, then human escalation | >100 requests/hour |
| INVALID_PLATFORM | 400 | Reject request immediately | platform="unknown" |
| VALIDATION_FAILED | 422 | Log and return empty | Malformed response from MCP |
| TIMEOUT | 504 | Retry, then fallback | No response within 30s |
| NETWORK_ERROR | 503 | Exponential backoff, max 3 retries | Connection refused |

#### Example Call
```python
result = fetch_trends(
    platform="twitter",
    limit=100,
    timeWindow="4h",
    minEngagement=5000
)
# Returns: { trends: [TrendData, ...], count: 87, truncated: False }
```

---

### 2. `semantic_filter`

**Agent**: Orchestrator / Trend Analyst  
**Purpose**: Score trend relevance to campaign goals using LLM

#### Input Schema
```json
{
  "trends": {
    "type": "array",
    "items": { "$ref": "TrendData Schema" },
    "required": true,
    "minItems": 1,
    "maxItems": 1000
  },
  "campaign_goals": {
    "type": "array",
    "items": { "type": "string" },
    "required": true,
    "minItems": 1,
    "maxItems": 10,
    "description": "Campaign objectives (e.g., ['fashion', 'luxury_brands', 'Ethiopia'])"
  },
  "relevance_threshold": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "default": 0.75,
    "required": false,
    "description": "Only return trends with score ≥ threshold"
  },
  "model": {
    "type": "string",
    "enum": ["gemini-3-flash", "gpt-4o-mini"],
    "default": "gemini-3-flash",
    "required": false
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "filtered_trends": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "trend": { "$ref": "TrendData Schema" },
          "relevance_score": { "type": "number", "minimum": 0, "maximum": 1 },
          "reasoning": { "type": "string", "maxLength": 500 }
        }
      }
    },
    "total_input": { "type": "integer" },
    "total_output": { "type": "integer" },
    "filtered_at": { "type": "string", "format": "ISO8601" }
  }
}
```

#### Behavior
- **Timeout**: 10 seconds for LLM inference (3s per trend batch)
- **Batching**: Process trends in groups of 100 to optimize LLM calls
- **Caching**: Cache scores for same trend + goals combo (30 min TTL)
- **Idempotency**: Same input produces consistent scores (deterministic LLM seed)

#### Error Codes
| Code | HTTP | Recovery |
|------|------|----------|
| FILTER_TIMEOUT | 504 | Return partial results (up to last successful batch) |
| INVALID_INPUT | 400 | Reject; return detailed validation error |
| LLM_ERROR | 503 | Retry with fallback model |
| INVALID_GOALS | 422 | Reject; goals must be non-empty strings |

#### Example Call
```python
result = semantic_filter(
    trends=[trend1, trend2, trend3],
    campaign_goals=["fashion", "luxury", "Africa"],
    relevance_threshold=0.75
)
# Returns: { filtered_trends: [
#   {trend: trend1, relevance_score: 0.92, reasoning: "..."},
#   {trend: trend3, relevance_score: 0.81, reasoning: "..."}
# ]}
```

---

### 3. `generate_content`

**Agent**: Content Creator  
**Purpose**: Generate content (script, media URLs, captions) from trend + persona

#### Input Schema
```json
{
  "trend": {
    "type": "object",
    "$ref": "TrendData Schema",
    "required": true
  },
  "persona": {
    "type": "object",
    "$ref": "Persona Schema (from Section 5 below)",
    "required": true
  },
  "platform": {
    "type": "string",
    "enum": ["twitter", "tiktok", "instagram", "youtube"],
    "required": true
  },
  "content_type": {
    "type": "string",
    "enum": ["video_script", "carousel", "single_post", "thread"],
    "default": "video_script",
    "required": false
  },
  "media_generation": {
    "type": "boolean",
    "default": true,
    "required": false,
    "description": "Generate images/videos or use text-only"
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "content": { "$ref": "Content Package Schema from 2-design.md" },
    "generation_time_ms": { "type": "integer" },
    "model_used": { "type": "string" },
    "confidence_score": { "type": "number", "minimum": 0, "maximum": 1 }
  }
}
```

#### Behavior
- **Timeout**: 45 seconds (15s LLM + 30s media generation)
- **Media Generation**: Calls `ideogram` (images) or `runwayml` (videos) via MCP
- **Safety**: Scans output for offensive content; if detected, retries with safety prompt
- **Determinism**: Same input produces structurally identical output (script length, hashtag count)

#### Error Codes
| Code | HTTP | Recovery |
|------|------|----------|
| GENERATION_TIMEOUT | 504 | Return partial content with low confidence_score |
| INVALID_PERSONA | 400 | Reject; return persona validation errors |
| MEDIA_GENERATION_FAILED | 502 | Retry up to 2x; if still fails, omit media URLs |
| SAFETY_VIOLATION | 422 | Reject entire content; increment rejection counter |
| LLM_ERROR | 503 | Retry with fallback model (max 2 retries) |

#### Example Call
```python
result = generate_content(
    trend=trend_data,
    persona=agent_persona,
    platform="tiktok",
    content_type="video_script",
    media_generation=True
)
# Returns: ContentPackage with script, media_urls, captions, hashtags, confidence_score
```

---

### 4. `validate_content`

**Agent**: Judge Agent  
**Purpose**: Validate content package against safety/quality rules

#### Input Schema
```json
{
  "content": {
    "type": "object",
    "$ref": "Content Package Schema",
    "required": true
  },
  "validation_rules": {
    "type": "object",
    "required": false,
    "properties": {
      "check_offensive_language": { "type": "boolean", "default": true },
      "check_misinformation": { "type": "boolean", "default": true },
      "check_copyright": { "type": "boolean", "default": true },
      "check_platform_compliance": { "type": "boolean", "default": true }
    }
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "valid": { "type": "boolean" },
    "confidence_score": { "type": "number", "minimum": 0, "maximum": 1 },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "rule": { "type": "string" },
          "severity": { "type": "string", "enum": ["error", "warning", "info"] },
          "message": { "type": "string" }
        }
      }
    },
    "requires_human_review": { "type": "boolean" },
    "validation_time_ms": { "type": "integer" }
  }
}
```

#### Behavior
- **Timeout**: 5 seconds
- **Caching**: Cache validation results for same content_id (6h TTL)
- **Confidence**: Aggregate multiple checks into single confidence_score
- **Escalation**: If any error-level issue, set requires_human_review=true

#### Error Codes
| Code | HTTP | Recovery |
|------|------|----------|
| VALIDATION_ERROR | 422 | Return with valid=false and issues list |
| SAFETY_CHECK_TIMEOUT | 504 | Assume worst case (requires_human_review=true) |
| INVALID_CONTENT | 400 | Reject; content missing required fields |

#### Example Call
```python
result = validate_content(
    content=content_package,
    validation_rules={"check_offensive_language": True, "check_misinformation": True}
)
# Returns: { valid: True, confidence_score: 0.92, issues: [], requires_human_review: False }
```

---

### 5. `publish_content`

**Agent**: Distribution Manager  
**Purpose**: Publish content to social platform

#### Input Schema
```json
{
  "content": {
    "type": "object",
    "$ref": "Content Package Schema",
    "required": true
  },
  "approval_token": {
    "type": "string",
    "format": "jwt",
    "required": true,
    "description": "Cryptographically signed approval from human reviewer"
  },
  "platform": {
    "type": "string",
    "enum": ["twitter", "tiktok", "instagram", "youtube"],
    "required": true
  },
  "schedule_time": {
    "type": "string",
    "format": "ISO8601",
    "required": false,
    "description": "Publish at specific time (default: immediate)"
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "post_id": { "type": "string" },
    "post_url": { "type": "string", "format": "uri" },
    "platform": { "type": "string" },
    "published_at": { "type": "string", "format": "ISO8601" },
    "engagement_snapshot": {
      "type": "object",
      "properties": {
        "likes": { "type": "integer" },
        "comments": { "type": "integer" },
        "shares": { "type": "integer" }
      }
    }
  }
}
```

#### Behavior
- **Timeout**: 15 seconds per platform
- **Idempotency**: Same content + approval_token published only once (check by content_id)
- **Token Validation**: Verify JWT signature and expiration (max 2h TTL)
- **Auditing**: Log publication action with reviewer_id, timestamp, content_id

#### Error Codes
| Code | HTTP | Recovery |
|------|------|----------|
| PUBLISH_FAILED | 502 | Retry up to 3x with exponential backoff |
| INVALID_TOKEN | 401 | Reject immediately (no retry) |
| TOKEN_EXPIRED | 401 | Reject (request new approval) |
| PLATFORM_ERROR | 503 | Retry with fallback platform |
| DUPLICATE_CONTENT | 409 | Return existing post_id (idempotent) |

#### Example Call
```python
result = publish_content(
    content=content_package,
    approval_token=jwt_token,
    platform="tiktok",
    schedule_time=None
)
# Returns: { success: True, post_id: "12345", post_url: "https://...", published_at: "2025-..." }
```

---

### 6. `get_agent_profile`

**Agent**: Orchestrator  
**Purpose**: Fetch agent profile (status, capabilities, wallet)

#### Input Schema
```json
{
  "agent_id": {
    "type": "string",
    "format": "uuid",
    "required": true
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "$ref": "Agent Profile Schema from 2-design.md"
}
```

#### Behavior
- **Timeout**: 2 seconds
- **Caching**: Cache for 10 seconds (agents rarely change mid-operation)
- **Fallback**: If unavailable, return stale cached version + warning flag

#### Error Codes
| Code | HTTP | Recovery |
|------|------|----------|
| AGENT_NOT_FOUND | 404 | Return error (agent doesn't exist) |
| UNAVAILABLE | 503 | Return cached version if available |

---

### 7. `update_agent_state`

**Agent**: Orchestrator  
**Purpose**: Update agent state (status, pending_tasks, wallet_balance)

#### Input Schema
```json
{
  "agent_id": {
    "type": "string",
    "format": "uuid",
    "required": true
  },
  "state_updates": {
    "type": "object",
    "required": true,
    "properties": {
      "status": { "type": "string", "enum": ["active", "busy", "paused", "error"] },
      "pending_tasks": { "type": "integer", "minimum": 0 },
      "last_execution": { "type": "string", "format": "ISO8601" },
      "wallet_balance": { "type": "number", "minimum": 0 }
    }
  },
  "expected_version": {
    "type": "integer",
    "required": false,
    "description": "For optimistic locking (prevent concurrent update conflicts)"
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "updated_profile": { "$ref": "Agent Profile Schema" },
    "new_version": { "type": "integer" }
  }
}
```

#### Behavior
- **Timeout**: 5 seconds
- **Optimistic Locking**: If expected_version doesn't match current, reject with CONCURRENCY_ERROR
- **Atomic**: All updates in state_updates must succeed together or none succeed
- **Audit**: Log state changes to audit_log table

#### Error Codes
| Code | HTTP | Recovery |
|------|------|----------|
| CONCURRENCY_ERROR | 409 | Retry with fresh expected_version |
| AGENT_NOT_FOUND | 404 | Return error |
| INVALID_STATE_TRANSITION | 422 | Reject (e.g., can't go from 'paused' to 'error' without reason) |

---

### 8. `fetch_wallet_balance`

**Agent**: CFO Judge  
**Purpose**: Check agent's wallet balance

#### Input Schema
```json
{
  "wallet_address": {
    "type": "string",
    "pattern": "^0x[a-fA-F0-9]{40}$",
    "required": true,
    "description": "Ethereum/Base wallet address"
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "wallet_address": { "type": "string" },
    "balance": { "type": "number", "minimum": 0 },
    "currency": { "type": "string", "enum": ["USDC", "ETH", "BASE"] },
    "last_updated": { "type": "string", "format": "ISO8601" },
    "network": { "type": "string", "enum": ["mainnet", "base", "sepolia"] }
  }
}
```

#### Behavior
- **Timeout**: 5 seconds
- **Caching**: Cache for 30 seconds (balance may update slowly on chain)
- **Network**: Default to Base mainnet

#### Error Codes
| Code | HTTP | Recovery |
|------|------|----------|
| WALLET_ERROR | 500 | Retry up to 2x; escalate if persistent |
| NETWORK_ERROR | 503 | Use cached balance or block transaction |
| INVALID_ADDRESS | 400 | Reject request |

---

### 9. `debit_wallet`

**Agent**: CFO Judge  
**Purpose**: Deduct cost from agent's wallet (for OpenClaw payments)

#### Input Schema
```json
{
  "wallet_address": { "type": "string", "pattern": "^0x[a-fA-F0-9]{40}$", "required": true },
  "amount": { "type": "number", "minimum": 0.01, "required": true },
  "currency": { "type": "string", "enum": ["USDC", "ETH", "BASE"], "required": true },
  "tx_description": { "type": "string", "maxLength": 200, "required": true, "description": "e.g., 'OpenClaw RFP-123 payment'" },
  "idempotency_key": { "type": "string", "format": "uuid", "required": true, "description": "Prevents duplicate charges if retried" }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "tx_id": { "type": "string", "description": "Blockchain transaction ID" },
    "amount_deducted": { "type": "number" },
    "new_balance": { "type": "number" },
    "confirmed_at": { "type": "string", "format": "ISO8601" }
  }
}
```

#### Behavior
- **Timeout**: 10 seconds (wait for blockchain confirmation)
- **Idempotency**: If idempotency_key seen before, return cached result (no double charge)
- **Insufficient Funds**: Reject immediately; do not attempt partial debit
- **Audit**: Every debit logged to audit_log with tx_id + description

#### Error Codes
| Code | HTTP | Recovery |
|------|------|----------|
| INSUFFICIENT_BALANCE | 402 | Reject; escalate to human (agent needs funding) |
| TX_FAILED | 502 | Retry up to 3x; if persistent, escalate |
| INVALID_ADDRESS | 400 | Reject immediately |
| NETWORK_ERROR | 503 | Retry with exponential backoff |

---

### 10. `register_openclaw_profile`

**Agent**: Orchestrator (on startup)  
**Purpose**: Register agent with OpenClaw network

#### Input Schema
```json
{
  "agent_profile": {
    "type": "object",
    "$ref": "Agent Profile Schema from 2-design.md",
    "required": true
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "registered": { "type": "boolean" },
    "profile_url": { "type": "string", "format": "uri" },
    "directory_id": { "type": "string" },
    "registered_at": { "type": "string", "format": "ISO8601" }
  }
}
```

#### Behavior
- **Timeout**: 10 seconds
- **Idempotency**: Re-registering same agent_id updates profile (no duplicates)
- **Signature**: Profile must be cryptographically signed by agent's private key

#### Error Codes
| Code | HTTP | Recovery |
|------|------|----------|
| REGISTRATION_FAILED | 502 | Retry up to 3x; if fails, continue with warning |
| INVALID_PROFILE | 422 | Reject; fix profile schema |
| NETWORK_ERROR | 503 | Retry with backoff |

---

## Retry Strategy (All Skills)

Default retry behavior unless specified otherwise:

```python
def retry_skill(skill_func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return skill_func()
        except RetryableError as e:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            if attempt < max_retries - 1:
                sleep(wait_time + random(0, 1))  # Jitter
            else:
                raise
        except NonRetryableError as e:
            raise  # Fail immediately
```

**Retryable Errors**: TIMEOUT, RATE_LIMITED, NETWORK_ERROR, PLATFORM_UNAVAILABLE, TX_FAILED  
**Non-Retryable Errors**: INVALID_INPUT, INVALID_PLATFORM, AGENT_NOT_FOUND, INSUFFICIENT_BALANCE

---

## Observability

All skill calls MUST log:

```python
{
  "skill_name": "fetch_trends",
  "agent_id": "agent-123",
  "timestamp": "2025-02-05T14:30:00Z",
  "input_hash": "sha256(serialized_input)",
  "output_hash": "sha256(serialized_output)",
  "duration_ms": 2543,
  "error_code": null,
  "retry_count": 0,
  "success": true
}
```

Key metrics:
- `skill_{name}_duration_ms` (histogram)
- `skill_{name}_errors_total` (counter by error_code)
- `skill_{name}_retries_total` (counter)
- `skill_{name}_success_rate` (gauge)

---

## Versioning & Deprecation

Skills use semantic versioning: `skill@v1.0`

**Deprecation Policy**:
- Minor changes (new optional parameters): backward compatible
- Major changes (required parameter changes): new major version required
- Orchestrator supports last 2 versions
- 30-day deprecation notice before removing old version

