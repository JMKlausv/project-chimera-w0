# MCP Resources Specification

This document defines all Model Context Protocol (MCP) resources that Chimera agents use to fetch data from external systems. Each resource is accessed via standardized endpoints with defined rate limits, schemas, and fallback chains.

## Core Principles

- **MCP-First**: All external data fetched exclusively via MCP (no direct API calls)
- **Graceful Degradation**: Fallback chains ensure service continues when primary source unavailable
- **Rate-Limited**: Respect platform rate limits with client-side throttling
- **Cached**: Minimize redundant calls with configurable TTLs
- **Monitored**: All fetches logged for observability and cost tracking

---

## Resource Inventory

| Resource | MCP Server | Purpose | Rate Limit | Response Schema | Fallback |
|----------|-----------|---------|-----------|-----------------|----------|
| twitter://mentions/recent | mcp-server-twitter | Recent mentions of agent | 100/hr | TrendData[] | twitter://feed/{user_id} |
| twitter://feed/{user_id} | mcp-server-twitter | User timeline with trending posts | 300/hr | TrendData[] | none |
| news://global/trends | mcp-server-news | Global trending topics | 50/hr | TrendData[] | news://category/general |
| news://region/{region}/trends | mcp-server-news | Region-specific trends | 100/hr | TrendData[] | news://global/trends |
| news://category/{category}/trends | mcp-server-news | Category trends (fashion, tech, crypto) | 150/hr | TrendData[] | news://global/trends |
| market://crypto/{asset}/trending | mcp-server-market | Cryptocurrency trending topics | 200/hr | TrendData[] | news://category/finance |
| weaviate://vector/search | mcp-server-weaviate | Vector similarity search for RAG | 1000/min | {results: Document[]} | none (local fallback) |
| blockchain://base/transactions | mcp-server-coinbase | Recent Base/Ethereum transactions | 500/hr | {tx: Transaction[]} | none (query cache) |
| openclaw://heartbeat | mcp-server-openclaw | OpenClaw network heartbeat | 4/day | {instructions: Instruction[]} | none (critical) |
| openclaw://arp/discover | mcp-server-openclaw | Agent Relay Protocol discovery | 100/hr | {agents: Agent[]} | local_registry |

---

## Resource Specifications

### 1. `twitter://mentions/recent`

**MCP Server**: mcp-server-twitter  
**Purpose**: Fetch recent mentions of this agent on Twitter

#### Request
```json
{
  "resource": "twitter://mentions/recent",
  "method": "GET",
  "query_params": {
    "limit": 100,
    "max_results": 100,
    "tweet_fields": ["author_id", "created_at", "public_metrics", "entities"],
    "expansions": ["author_id"],
    "user_fields": ["username", "public_metrics"]
  }
}
```

#### Response Schema
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "id": { "type": "string" },
      "text": { "type": "string" },
      "author_id": { "type": "string" },
      "author_username": { "type": "string" },
      "created_at": { "type": "string", "format": "ISO8601" },
      "public_metrics": {
        "type": "object",
        "properties": {
          "like_count": { "type": "integer" },
          "retweet_count": { "type": "integer" },
          "reply_count": { "type": "integer" },
          "quote_count": { "type": "integer" }
        }
      },
      "entities": {
        "type": "object",
        "properties": {
          "hashtags": { "type": "array", "items": { "type": "string" } },
          "urls": { "type": "array", "items": { "type": "string" } },
          "mentions": { "type": "array", "items": { "type": "string" } }
        }
      }
    }
  }
}
```

#### Rate Limit & Caching
- **Rate Limit**: 100 requests/hour (Twitter API v2 limit)
- **Min Interval**: 36 seconds between calls (100/3600)
- **Cache TTL**: 5 minutes (mentions update frequently)
- **Timeout**: 10 seconds

#### Retry Policy
```
Attempt 1: Immediate
Attempt 2: After 5 seconds (if rate limited or timeout)
Attempt 3: After 30 seconds (if still rate limited)
Max retries: 3
Backoff: Linear (5s, 30s) → then fail to fallback
```

#### Fallback Chain
1. Primary: `twitter://mentions/recent`
2. Secondary: `twitter://feed/{agent_twitter_id}` (query for agent mentions manually)
3. Tertiary: Return cached results from last 1 hour
4. Fallback: Return empty array

#### Error Codes & Recovery
| Code | Cause | Recovery | Escalation |
|------|-------|----------|------------|
| 429 | Rate limited | Exponential backoff, check rate_reset_header | Check if limit too aggressive |
| 401 | Invalid credentials | Fail immediately; escalate to ops | Refresh Twitter API key |
| 503 | Twitter API down | Retry with exponential backoff; use fallback | Alert ops |
| Timeout | Network slow | Retry once; then fallback | Monitor network |

---

### 2. `twitter://feed/{user_id}`

**MCP Server**: mcp-server-twitter  
**Purpose**: Fetch user timeline for trend discovery

#### Request
```json
{
  "resource": "twitter://feed/{user_id}",
  "method": "GET",
  "path_params": {
    "user_id": "string (Twitter user ID)"
  },
  "query_params": {
    "max_results": 100,
    "tweet_fields": ["author_id", "created_at", "public_metrics", "entities"],
    "expansions": ["author_id"]
  }
}
```

#### Response Schema
Same as `twitter://mentions/recent` (returns array of tweets)

#### Rate Limit & Caching
- **Rate Limit**: 300 requests/hour (Twitter API v2)
- **Cache TTL**: 10 minutes
- **Timeout**: 10 seconds

#### Fallback Chain
1. Primary: `twitter://feed/{user_id}`
2. Secondary: `twitter://mentions/recent` (switch to mentions if feed unavailable)
3. Tertiary: Cached feed from last 2 hours
4. Fallback: Empty array

---

### 3. `news://global/trends`

**MCP Server**: mcp-server-news  
**Purpose**: Fetch global trending topics from news sources

#### Request
```json
{
  "resource": "news://global/trends",
  "method": "GET",
  "query_params": {
    "limit": 50,
    "timeWindow": "24h",
    "sortBy": "engagement_score"
  }
}
```

#### Response Schema
```json
{
  "type": "array",
  "items": { "$ref": "TrendData Schema" }
}
```

#### Rate Limit & Caching
- **Rate Limit**: 50 requests/hour
- **Min Interval**: 72 seconds between calls
- **Cache TTL**: 30 minutes
- **Timeout**: 15 seconds

#### Fallback Chain
1. Primary: `news://global/trends`
2. Secondary: `news://category/general`
3. Tertiary: Cached trends from last 4 hours
4. Fallback: Empty array

#### Notes
- Returns global trends aggregated from Reuters, AP, BBC, etc.
- Engagement metrics normalized across sources
- Timestamp = when trend was first reported globally

---

### 4. `news://region/{region}/trends`

**MCP Server**: mcp-server-news  
**Purpose**: Fetch region-specific trending topics

#### Request
```json
{
  "resource": "news://region/{region}/trends",
  "method": "GET",
  "path_params": {
    "region": "enum [US, EU, LATAM, APAC, AFRICA, MENA, ethiopia]"
  },
  "query_params": {
    "limit": 50,
    "timeWindow": "24h"
  }
}
```

#### Response Schema
```json
{
  "type": "array",
  "items": { "$ref": "TrendData Schema with geographic_origin = region" }
}
```

#### Rate Limit & Caching
- **Rate Limit**: 100 requests/hour per region
- **Cache TTL**: 30 minutes
- **Timeout**: 15 seconds

#### Fallback Chain
1. Primary: `news://region/{requested_region}`
2. Secondary: `news://region/global` or nearest adjacent region
3. Tertiary: `news://global/trends`
4. Fallback: Empty array

#### Notes
- Ethiopia has dedicated regional news coverage
- Useful for localized campaigns (e.g., Ethiopia fashion trends)

---

### 5. `news://category/{category}/trends`

**MCP Server**: mcp-server-news  
**Purpose**: Fetch category-specific trends

#### Request
```json
{
  "resource": "news://category/{category}/trends",
  "method": "GET",
  "path_params": {
    "category": "enum [technology, fashion, finance, entertainment, news, crypto, sports, health, other]"
  },
  "query_params": {
    "limit": 100,
    "timeWindow": "48h"
  }
}
```

#### Response Schema
```json
{
  "type": "array",
  "items": { "$ref": "TrendData Schema with metadata.category = category" }
}
```

#### Rate Limit & Caching
- **Rate Limit**: 150 requests/hour per category
- **Cache TTL**: 20 minutes
- **Timeout**: 15 seconds

#### Fallback Chain
1. Primary: `news://category/{requested_category}`
2. Secondary: `news://category/general`
3. Tertiary: `news://global/trends`
4. Fallback: Empty array

#### Notes
- Fashion category heavily populated (Chimera's strength)
- Crypto category volatile; shorter cache TTL (10min)

---

### 6. `market://crypto/{asset}/trending`

**MCP Server**: mcp-server-market  
**Purpose**: Fetch cryptocurrency trending topics

#### Request
```json
{
  "resource": "market://crypto/{asset}/trending",
  "method": "GET",
  "path_params": {
    "asset": "string (e.g., 'bitcoin', 'ethereum', 'base')"
  },
  "query_params": {
    "limit": 50,
    "timeWindow": "24h",
    "sources": ["twitter", "reddit", "coinmarketcap"]
  }
}
```

#### Response Schema
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "trend": { "$ref": "TrendData Schema" },
      "price_change": { "type": "number", "description": "% change in asset price" },
      "volume_change": { "type": "number", "description": "% change in trading volume" },
      "sentiment_score": { "type": "number", "minimum": -1, "maximum": 1 }
    }
  }
}
```

#### Rate Limit & Caching
- **Rate Limit**: 200 requests/hour
- **Cache TTL**: 5 minutes (crypto volatile)
- **Timeout**: 10 seconds

#### Fallback Chain
1. Primary: `market://crypto/{asset}/trending`
2. Secondary: `market://crypto/bitcoin/trending` (fall back to major asset)
3. Tertiary: `news://category/crypto/trends`
4. Fallback: Empty array

#### Notes
- Real-time price correlation: high engagement during volatility
- Useful for crypto/finance influencer campaigns

---

### 7. `weaviate://vector/search`

**MCP Server**: mcp-server-weaviate  
**Purpose**: Vector similarity search for semantic RAG (memory retrieval)

#### Request
```json
{
  "resource": "weaviate://vector/search",
  "method": "POST",
  "body": {
    "query_embedding": [0.1, 0.2, ..., 0.8],  // 1536-dim OpenAI embedding
    "limit": 10,
    "certainty": 0.7,  // Similarity threshold (0-1)
    "collection": "trends"  // or "content_cache", "campaigns"
  }
}
```

#### Response Schema
```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "content": { "type": "object" },  // Original document
          "distance": { "type": "number" },  // 0 = identical, 1 = opposite
          "certainty": { "type": "number", "minimum": 0, "maximum": 1 }
        }
      }
    },
    "search_time_ms": { "type": "integer" }
  }
}
```

#### Rate Limit & Caching
- **Rate Limit**: 1000 requests/minute (Weaviate local instance)
- **Cache TTL**: Not applicable (Weaviate is local)
- **Timeout**: 5 seconds

#### Fallback Chain
1. Primary: Weaviate local instance
2. Secondary: Fall back to MongoDB text search
3. Tertiary: Return empty results

#### Notes
- Weaviate hosted locally (not external MCP)
- Embeddings updated in real-time as trends ingested
- Critical for RAG: "Find similar campaigns to improve content quality"

---

### 8. `blockchain://base/transactions`

**MCP Server**: mcp-server-coinbase  
**Purpose**: Query recent Base/Ethereum blockchain transactions

#### Request
```json
{
  "resource": "blockchain://base/transactions",
  "method": "GET",
  "query_params": {
    "limit": 100,
    "wallet_address": "0x...",  // Optional filter
    "timeWindow": "24h"
  }
}
```

#### Response Schema
```json
{
  "type": "object",
  "properties": {
    "transactions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "tx_id": { "type": "string" },
          "from": { "type": "string" },
          "to": { "type": "string" },
          "amount": { "type": "number" },
          "currency": { "type": "string", "enum": ["USDC", "ETH", "BASE"] },
          "timestamp": { "type": "string", "format": "ISO8601" },
          "status": { "type": "string", "enum": ["pending", "confirmed", "failed"] }
        }
      }
    }
  }
}
```

#### Rate Limit & Caching
- **Rate Limit**: 500 requests/hour
- **Cache TTL**: 10 minutes (transactions immutable once confirmed)
- **Timeout**: 10 seconds

#### Fallback Chain
1. Primary: Live blockchain query
2. Secondary: Query cache (transactions already seen)
3. Tertiary: Return empty array (no transaction info available)

#### Notes
- Used by CFO Judge to verify payments
- Immutable record for audit trail

---

### 9. `openclaw://heartbeat`

**MCP Server**: mcp-server-openclaw  
**Purpose**: Fetch network heartbeat with instructions for agent

#### Request
```json
{
  "resource": "openclaw://heartbeat",
  "method": "GET",
  "query_params": {
    "agent_id": "uuid"
  }
}
```

#### Response Schema
```json
{
  "type": "object",
  "properties": {
    "heartbeat_id": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "ISO8601" },
    "agent_status_required": { "type": "string", "enum": ["online", "maintenance", "update_required"] },
    "instructions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "instruction_id": { "type": "string" },
          "command": { "type": "string", "enum": ["post_update", "respond_to_query", "execute_campaign"] },
          "payload": { "type": "object" },
          "checksum": { "type": "string", "description": "SHA256 for integrity" }
        }
      }
    },
    "next_heartbeat_due": { "type": "string", "format": "ISO8601" }
  }
}
```

#### Rate Limit & Caching
- **Rate Limit**: 4 requests/day (fixed schedule: every 6 hours)
- **Cache TTL**: Not applicable (scheduled fetch)
- **Timeout**: 30 seconds (critical path)

#### Fallback Chain
1. Primary: `openclaw://heartbeat`
2. Secondary: None (failure to fetch heartbeat = critical)
3. Tertiary: N/A

#### Error Handling
- If heartbeat unreachable for >24h: agent enters offline mode (pauses external ops)
- If checksum invalid: reject instructions (security), escalate to ops
- If agent_status_required = "update_required": pause new work, prepare for update

#### Notes
- **CRITICAL RESOURCE**: Agent MUST execute heartbeat fetch every 4 hours ± 5 minutes
- Instructions must be sandboxed (cannot access privileged functions)
- All instruction executions logged to audit_log

---

### 10. `openclaw://arp/discover`

**MCP Server**: mcp-server-openclaw  
**Purpose**: Agent Relay Protocol discovery of other agents

#### Request
```json
{
  "resource": "openclaw://arp/discover",
  "method": "GET",
  "query_params": {
    "capability": "enum [trend_analysis, content_creation, distribution, quality_control]",
    "region": "enum [global, US, EU, LATAM, APAC, AFRICA]",
    "limit": 50
  }
}
```

#### Response Schema
```json
{
  "type": "array",
  "items": { "$ref": "Agent Profile Schema" }
}
```

#### Rate Limit & Caching
- **Rate Limit**: 100 requests/hour
- **Cache TTL**: 30 minutes (agent profiles change slowly)
- **Timeout**: 5 seconds

#### Fallback Chain
1. Primary: `openclaw://arp/discover`
2. Secondary: Local agent registry (cached from last 2 hours)
3. Tertiary: Return empty array

#### Notes
- Used for collaborative RFPs ("find another content_creator to partner")
- Filters by capability + region

---

## Client-Side Rate Limiting

All agents MUST implement client-side rate limiting to respect MCP server quotas:

```python
class RateLimiter:
    def __init__(self, resource_url, rate_limit_per_hour):
        self.resource = resource_url
        self.rate_limit = rate_limit_per_hour
        self.request_times = deque()
    
    def acquire(self):
        """Block until safe to make request"""
        now = time.time()
        hour_ago = now - 3600
        
        # Remove old requests
        while self.request_times and self.request_times[0] < hour_ago:
            self.request_times.popleft()
        
        if len(self.request_times) >= self.rate_limit:
            # Wait until oldest request expires
            sleep_time = self.request_times[0] + 3600 - now
            sleep(sleep_time + 1)
            self.acquire()  # Recursive retry
        
        self.request_times.append(now)
```

---

## Caching Strategy

All resources cached locally in Redis with TTLs:

```python
cache_key = f"mcp:{resource}:{hash(request_params)}"
cached = redis.get(cache_key)

if cached:
    return json.loads(cached)

# Fetch from MCP
result = mcp_client.fetch(resource, request_params)

# Store with TTL
redis.setex(cache_key, ttl_seconds, json.dumps(result))
return result
```

**Cache Eviction**: LRU policy when cache exceeds 1GB

---

## Observability

All MCP calls logged:

```python
{
  "resource": "twitter://mentions/recent",
  "agent_id": "agent-123",
  "timestamp": "2025-02-05T14:30:00Z",
  "duration_ms": 2543,
  "cache_hit": false,
  "result_count": 87,
  "error_code": null,
  "retry_attempt": 0,
  "rate_limit_remaining": 42
}
```

Key metrics:
- `mcp_{resource}_duration_ms` (histogram)
- `mcp_{resource}_cache_hit_rate` (gauge)
- `mcp_{resource}_errors_total` (counter by error_code)
- `mcp_{resource}_rate_limit_remaining` (gauge)

