# Error Codes Specification

This document defines all error codes that can occur in the Chimera system, their HTTP status mappings, recovery strategies, and escalation procedures. Standardized error handling enables consistent behavior across all agents and external systems.

## Error Code Categories

Errors are organized by domain:

1. **External Integration Errors** (EXT_*)
2. **Data Validation Errors** (VAL_*)
3. **Resource Errors** (RES_*)
4. **State Errors** (STATE_*)
5. **Security Errors** (SEC_*)
6. **Platform Errors** (PLAT_*)
7. **Financial Errors** (FIN_*)
8. **Network Errors** (NET_*)

---

## Error Code Catalog

### External Integration Errors (EXT_*)

#### EXT_PLATFORM_UNAVAILABLE
- **HTTP Status**: 503 Service Unavailable
- **Cause**: MCP resource or external API unreachable
- **Recovery**: Exponential backoff (1s, 2s, 4s), max 3 retries
- **Fallback**: Use cached data or alternative MCP server
- **Example**: Twitter API server down, news service offline
- **Escalation**: If >5 min persistent, alert ops

```python
if error.code == "EXT_PLATFORM_UNAVAILABLE":
    if attempt < 3:
        sleep(2 ** attempt)
        retry()
    else:
        use_fallback_or_cached_data()
```

#### EXT_RATE_LIMITED
- **HTTP Status**: 429 Too Many Requests
- **Cause**: Exceeded platform rate limit
- **Recovery**: Check `Retry-After` header; exponential backoff with jitter
- **Fallback**: Use cached data; pause new requests
- **Example**: Twitter 100 requests/hour exceeded
- **Escalation**: If recurring, reduce request frequency or increase quota

```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    sleep(retry_after + random(0, 10))  # Jitter
    retry()
```

#### EXT_INVALID_PLATFORM
- **HTTP Status**: 400 Bad Request
- **Cause**: Platform name not recognized
- **Recovery**: Reject immediately; return error to caller
- **Fallback**: None (configuration error)
- **Example**: platform="tiktok-x" (typo)
- **Escalation**: Check configuration; human fix required

#### EXT_AUTH_FAILED
- **HTTP Status**: 401 Unauthorized
- **Cause**: Invalid API key, token expired
- **Recovery**: Refresh credentials; if still fails, escalate
- **Fallback**: Use cached data (read-only mode)
- **Example**: Twitter API key invalid
- **Escalation**: Ops team must rotate credentials

#### EXT_FORBIDDEN
- **HTTP Status**: 403 Forbidden
- **Cause**: Authenticated but lacking permission
- **Recovery**: Check scope of API key; may require manual approval
- **Fallback**: Use lower-permission fallback endpoint
- **Example**: API key doesn't have "tweet_write" scope
- **Escalation**: Ops team must update API key permissions

---

### Data Validation Errors (VAL_*)

#### VAL_SCHEMA_INVALID
- **HTTP Status**: 422 Unprocessable Entity
- **Cause**: Data doesn't match required schema
- **Recovery**: Log detailed validation error; reject and notify caller
- **Fallback**: None
- **Example**: TrendData missing required `trend_id` field
- **Escalation**: Alert ops if systematic (possible data corruption)

**Validation errors**:
```python
if not validate_against_schema(data, TrendDataSchema):
    raise ValidationError(
        code="VAL_SCHEMA_INVALID",
        message=f"Missing required field: {missing_fields}",
        schema_version="TrendData v1.0"
    )
```

#### VAL_ENGAGEMENT_FORMULA_MISMATCH
- **HTTP Status**: 422 Unprocessable Entity
- **Cause**: `engagement_score != likes + (comments*2) + (shares*3)`
- **Recovery**: Reject data; log warning (may indicate data corruption)
- **Fallback**: Request data refresh from source
- **Example**: platform reports engagement_score=100 but likes=10, comments=5, shares=2 (calculated=22)
- **Escalation**: If >5% of trends fail, investigate platform data quality

#### VAL_NEGATIVE_ENGAGEMENT
- **HTTP Status**: 422 Unprocessable Entity
- **Cause**: engagement_score < 0
- **Recovery**: Clamp to 0; log as data quality issue
- **Fallback**: Accept with warning
- **Example**: Platform returns engagement_score=-50 (impossible)
- **Escalation**: Contact platform for data quality investigation

#### VAL_TIMESTAMP_INVALID
- **HTTP Status**: 422 Unprocessable Entity
- **Cause**: Timestamp in future, too old, or malformed
- **Recovery**: Reject data; request correction
- **Fallback**: None (timestamp is critical for freshness)
- **Example**: timestamp="2099-01-01T00:00:00Z" (future date)
- **Escalation**: Log as data quality issue

#### VAL_MISSING_REQUIRED_FIELD
- **HTTP Status**: 422 Unprocessable Entity
- **Cause**: Required field absent (e.g., trend_id, content_id)
- **Recovery**: Reject; return field name in error
- **Fallback**: None
- **Example**: TrendData without `platform` field
- **Escalation**: If widespread, check MCP server schema compliance

#### VAL_TYPE_MISMATCH
- **HTTP Status**: 422 Unprocessable Entity
- **Cause**: Field type doesn't match schema (e.g., string instead of integer)
- **Recovery**: Attempt type coercion; if fails, reject
- **Fallback**: None
- **Example**: `limit="100"` (string) instead of `limit=100` (integer)
- **Escalation**: Log as client integration issue

---

### Resource Errors (RES_*)

#### RES_NOT_FOUND
- **HTTP Status**: 404 Not Found
- **Cause**: Resource doesn't exist (e.g., agent_id not found)
- **Recovery**: Return 404; inform caller
- **Fallback**: None
- **Example**: Get agent profile for agent_id="nonexistent-uuid"
- **Escalation**: If expected resource missing, check database

#### RES_ALREADY_EXISTS
- **HTTP Status**: 409 Conflict
- **Cause**: Resource already exists (e.g., duplicate registration)
- **Recovery**: Return existing resource ID (idempotent)
- **Fallback**: None
- **Example**: Register same OpenClaw profile twice
- **Escalation**: Check for concurrent operations

#### RES_QUOTA_EXCEEDED
- **HTTP Status**: 429 Too Many Requests
- **Cause**: Resource quota exceeded (e.g., max agents per account)
- **Recovery**: Reject request; inform user of quota
- **Fallback**: None
- **Example**: Account has max 10 agents; trying to create 11th
- **Escalation**: User must upgrade account or delete agents

#### RES_RESOURCE_LOCKED
- **HTTP Status**: 423 Locked
- **Cause**: Resource being modified by another process
- **Recovery**: Retry with exponential backoff
- **Fallback**: None
- **Example**: Content draft locked for editing
- **Escalation**: If lock >5 min, check process health

---

### State Errors (STATE_*)

#### STATE_INVALID_TRANSITION
- **HTTP Status**: 409 Conflict
- **Cause**: Attempted invalid state transition
- **Recovery**: Reject; return valid next states
- **Fallback**: None
- **Example**: Try to publish content in "GENERATION_FAILED" state
- **Escalation**: Check orchestrator logic

#### STATE_CONFLICT
- **HTTP Status**: 409 Conflict
- **Cause**: Optimistic locking version mismatch
- **Recovery**: Refresh state; retry with new version
- **Fallback**: None
- **Example**: Update agent_state with stale version number
- **Escalation**: If frequent, consider distributed locking

```python
while True:
    state = fetch_agent_state(agent_id)
    try:
        update_agent_state(agent_id, updates, expected_version=state.version)
        break
    except StateConflict:
        continue  # Retry
```

#### STATE_SLA_EXCEEDED
- **HTTP Status**: 504 Gateway Timeout
- **Cause**: Resource stuck in state beyond SLA
- **Recovery**: Escalate to next handler; force state transition
- **Fallback**: Move to escalation state (e.g., REVIEW_PENDING → escalated to supervisor)
- **Example**: Content in APPROVAL_PENDING >2 minutes
- **Escalation**: Auto-assign to supervisor

---

### Security Errors (SEC_*)

#### SEC_INVALID_TOKEN
- **HTTP Status**: 401 Unauthorized
- **Cause**: JWT token invalid or malformed
- **Recovery**: Reject immediately; request new token
- **Fallback**: None (no security bypass)
- **Example**: approval_token with invalid signature
- **Escalation**: Log as potential security incident

#### SEC_TOKEN_EXPIRED
- **HTTP Status**: 401 Unauthorized
- **Cause**: JWT token past expiration time
- **Recovery**: Reject; request fresh approval
- **Fallback**: None
- **Example**: approval_token expired >2 hours ago
- **Escalation**: Normal; user must re-approve

#### SEC_INSUFFICIENT_PERMISSIONS
- **HTTP Status**: 403 Forbidden
- **Cause**: Agent lacks permission for action
- **Recovery**: Reject; list required permissions
- **Fallback**: None
- **Example**: Agent attempts to debit wallet without CFO_JUDGE role
- **Escalation**: Check RBAC configuration

#### SEC_SIGNATURE_INVALID
- **HTTP Status**: 401 Unauthorized
- **Cause**: Cryptographic signature verification failed
- **Recovery**: Reject immediately
- **Fallback**: None (integrity violation)
- **Example**: Content signature doesn't match content hash
- **Escalation**: Log as potential tampering; investigate

#### SEC_CHECKSUM_MISMATCH
- **HTTP Status**: 422 Unprocessable Entity
- **Cause**: Data integrity check failed
- **Recovery**: Reject; request data refresh
- **Fallback**: None
- **Example**: OpenClaw heartbeat checksum invalid
- **Escalation**: Possible MITM attack; increase monitoring

#### SEC_AUDIT_TAMPER_DETECTED
- **HTTP Status**: 500 Internal Server Error
- **Cause**: Audit log entry modified after creation
- **Recovery**: Halt operations; escalate to security team
- **Fallback**: None (audit integrity critical)
- **Example**: Audit log timestamp changed post-log
- **Escalation**: Immediate investigation required

---

### Platform Errors (PLAT_*)

#### PLAT_PUBLISH_FAILED
- **HTTP Status**: 502 Bad Gateway
- **Cause**: Platform rejected content (policy violation, invalid format)
- **Recovery**: Retry up to 3x; if fails, escalate to human review
- **Fallback**: None (must publish to intended platform)
- **Example**: TikTok rejects video as "spam"
- **Escalation**: Human review of rejection reason

#### PLAT_DUPLICATE_CONTENT
- **HTTP Status**: 409 Conflict
- **Cause**: Content already published (idempotent check)
- **Recovery**: Return existing post_id (idempotent success)
- **Fallback**: None
- **Example**: Same script published twice → platform detects duplicate
- **Escalation**: Check orchestrator deduplication logic

#### PLAT_CONTENT_MODERATED
- **HTTP Status**: 451 Unavailable For Legal Reasons
- **Cause**: Content removed by platform moderation
- **Recovery**: Alert agent; content can be resubmitted with changes
- **Fallback**: None (moderation decision is final)
- **Example**: Instagram removes video for policy violation
- **Escalation**: Human review + policy feedback

#### PLAT_ACCOUNT_SUSPENDED
- **HTTP Status**: 403 Forbidden
- **Cause**: Platform account suspended
- **Recovery**: Halt publishing; escalate to ops
- **Fallback**: None (no publishing possible)
- **Example**: Twitter account suspended for spam
- **Escalation**: Immediate ops intervention required

---

### Financial Errors (FIN_*)

#### FIN_INSUFFICIENT_BALANCE
- **HTTP Status**: 402 Payment Required
- **Cause**: Agent wallet insufficient funds
- **Recovery**: Reject transaction; escalate to funding
- **Fallback**: None (cannot proceed without funds)
- **Example**: Debit 100 USDC but balance = 50 USDC
- **Escalation**: Alert agent + ops for account top-up

#### FIN_TRANSACTION_FAILED
- **HTTP Status**: 502 Bad Gateway
- **Cause**: Blockchain transaction failed (network issue, gas too low)
- **Recovery**: Retry up to 3x with exponential backoff
- **Fallback**: None (must complete transaction)
- **Example**: Ethereum transaction reverted
- **Escalation**: If persistent, check gas prices + network congestion

#### FIN_WALLET_ERROR
- **HTTP Status**: 500 Internal Server Error
- **Cause**: Wallet service unreachable or broken
- **Recovery**: Retry with backoff; use cached balance if available
- **Fallback**: Block transactions until wallet recovers
- **Example**: Coinbase AgentKit API down
- **Escalation**: Alert ops + financial team

#### FIN_INVALID_WALLET_ADDRESS
- **HTTP Status**: 400 Bad Request
- **Cause**: Wallet address malformed or invalid
- **Recovery**: Reject immediately; return error
- **Fallback**: None
- **Example**: wallet_address="not-a-valid-ethereum-address"
- **Escalation**: Configuration error; human fix

#### FIN_CURRENCY_CONVERSION_ERROR
- **HTTP Status**: 500 Internal Server Error
- **Cause**: Cannot convert between currency types
- **Recovery**: Retry; if fails, use fallback exchange rate
- **Fallback**: Use last-known exchange rate (cached)
- **Example**: Cannot convert USDC → ETH due to oracle down
- **Escalation**: Check oracle service health

---

### Network Errors (NET_*)

#### NET_TIMEOUT
- **HTTP Status**: 504 Gateway Timeout
- **Cause**: Request exceeded timeout threshold
- **Recovery**: Retry up to 3x with exponential backoff; then fail
- **Fallback**: Use cached data if available
- **Example**: MCP server doesn't respond within 10s
- **Escalation**: If >10% timeouts, check service health

```python
try:
    result = fetch_with_timeout(url, timeout=10)
except Timeout:
    for attempt in range(3):
        sleep(2 ** attempt)
        try:
            result = fetch_with_timeout(url, timeout=15)  # Increase timeout
            break
        except Timeout:
            continue
    else:
        use_cached_data()
```

#### NET_CONNECTION_REFUSED
- **HTTP Status**: 503 Service Unavailable
- **Cause**: Connection refused (service not running or port blocked)
- **Recovery**: Retry with backoff; escalate if persistent
- **Fallback**: Use cached data; try alternative endpoint
- **Example**: Cannot reach MCP server on port 8000
- **Escalation**: Check service health + network routing

#### NET_DNS_FAILURE
- **HTTP Status**: 503 Service Unavailable
- **Cause**: DNS resolution failed
- **Recovery**: Retry with backoff; try alternative DNS
- **Fallback**: Use cached IP address
- **Example**: Cannot resolve "api.twitter.com"
- **Escalation**: Check DNS configuration + ISP

#### NET_TLS_CERTIFICATE_INVALID
- **HTTP Status**: 495 SSL Certificate Error
- **Cause**: SSL/TLS certificate verification failed
- **Recovery**: Reject; do not bypass certificate check
- **Fallback**: None (security critical)
- **Example**: Self-signed certificate on HTTPS endpoint
- **Escalation**: Verify certificate or update root CA bundle

---

## Error Response Format

All errors MUST follow standardized format:

```json
{
  "error": {
    "code": "VAL_SCHEMA_INVALID",
    "message": "Missing required field: trend_id",
    "http_status": 422,
    "timestamp": "2025-02-05T14:30:00Z",
    "request_id": "uuid",
    "details": {
      "field": "trend_id",
      "schema_version": "TrendData v1.0",
      "constraint_violated": "required"
    },
    "recovery": {
      "strategy": "REJECT",
      "fallback": "NONE",
      "escalation": "Alert ops if >5% of requests fail",
      "retry_safe": false
    }
  }
}
```

### Error Response Fields

- **code**: Standardized error code (e.g., VAL_SCHEMA_INVALID)
- **message**: Human-readable explanation
- **http_status**: HTTP status code (400-599)
- **timestamp**: When error occurred (ISO8601)
- **request_id**: Trace ID for debugging
- **details**: Context-specific error information
- **recovery**: Recovery strategy (strategy, fallback, escalation, retry_safe)

---

## Recovery Strategy Matrix

| Error | Retry Safe? | Max Retries | Backoff | Escalation |
|-------|-------------|------------|---------|------------|
| EXT_PLATFORM_UNAVAILABLE | ✅ Yes | 3 | Exponential | ops if >5 min |
| EXT_RATE_LIMITED | ✅ Yes | 3 | Exponential + jitter | reduce frequency |
| EXT_AUTH_FAILED | ❌ No | 0 | N/A | rotate credentials |
| VAL_SCHEMA_INVALID | ❌ No | 0 | N/A | alert ops if systematic |
| STATE_CONFLICT | ✅ Yes | ∞ | Exponential | distributed locking |
| SEC_INVALID_TOKEN | ❌ No | 0 | N/A | request new approval |
| FIN_INSUFFICIENT_BALANCE | ❌ No | 0 | N/A | funding team |
| NET_TIMEOUT | ✅ Yes | 3 | Exponential | monitor service |

---

## Escalation Procedures

### Level 1: Automatic Retry
- Transient errors (timeout, rate_limited, connection_refused)
- Retry with exponential backoff
- Max 3 retries
- If all fail → Level 2

### Level 2: Fallback or Cached Data
- Use alternative MCP server / cached data
- Log warning
- If all fallbacks exhausted → Level 3

### Level 3: Human Alert
- Send alert to ops team (Slack, email)
- Include error code, context, suggested action
- Human investigates / decides next step

### Level 4: Circuit Breaker
- Service errors >10% in 5-minute window
- Halt new requests to failing service
- Return cached data only
- Auto-resume after 10 minutes if errors drop <5%

### Level 5: Safety Mode
- Critical security/financial errors
- Halt agent execution
- Require manual approval to continue
- Example: SEC_AUDIT_TAMPER_DETECTED, FIN_INSUFFICIENT_BALANCE

---

## Error Handling Best Practices

### 1. Classify Errors on Receipt
```python
def classify_error(response):
    if response.status_code == 429:
        return ErrorCategory.TRANSIENT, "EXT_RATE_LIMITED"
    elif response.status_code == 401:
        return ErrorCategory.SECURITY, "SEC_INVALID_TOKEN"
    elif response.status_code == 503:
        return ErrorCategory.TRANSIENT, "EXT_PLATFORM_UNAVAILABLE"
    else:
        return ErrorCategory.UNKNOWN, "UNKNOWN_ERROR"
```

### 2. Implement Retry Logic
```python
def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = min(2 ** attempt + random(0, 1), 30)  # Cap at 30s
            sleep(wait_time)
```

### 3. Log All Errors
```python
logger.error(
    "API call failed",
    error_code=error.code,
    http_status=error.status,
    request_id=request.id,
    duration_ms=elapsed,
    retry_count=attempt,
    agent_id=agent_id
)
```

### 4. Escalate Systematically
```python
if error_rate_5min > 0.1:  # >10% errors
    circuit_breaker.open()
    alert_ops(
        service=service_name,
        error_rate=error_rate_5min,
        recent_errors=last_10_errors
    )
```

### 5. User-Facing Error Messages
```python
def user_message(error_code):
    if error_code == "FIN_INSUFFICIENT_BALANCE":
        return "Wallet balance too low. Please add funds before retrying."
    elif error_code == "SEC_TOKEN_EXPIRED":
        return "Your approval token expired. Please re-approve content."
    else:
        return "An error occurred. Please contact support."
```

---

## Monitoring & Alerts

Track error metrics:

```
chimera_error_rate_5m{service, error_code}
chimera_error_retry_total{error_code, attempt}
chimera_error_escalation_total{error_code, escalation_level}
chimera_circuit_breaker_state{service}
```

Alert thresholds:
- Error rate >5% → Page ops team
- Security error (SEC_*) → Page security team immediately
- Circuit breaker opened → Alert ops + platform team
- Audit tamper detected (SEC_AUDIT_TAMPER_DETECTED) → Page security + legal immediately

