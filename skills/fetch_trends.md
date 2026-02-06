# Skill: fetch_trends

## Overview
Fetch trending topics from social platforms via MCP resources. This is the primary data ingestion point for the Trend Analyst agent.

**Agent**: Trend Analyst  
**FR**: FR-1.0, FR-1.3 (Active Resource Monitoring, High-Engagement Thresholding)  
**Timeout**: 30s | **P95 Target**: 8s

---

## Input Schema

```json
{
  "platform": {
    "type": "string",
    "enum": ["twitter", "news", "market", "reddit", "tiktok"],
    "required": true
  },
  "limit": {
    "type": "integer",
    "minimum": 1,
    "maximum": 500,
    "default": 50
  },
  "timeWindow": {
    "type": "string",
    "pattern": "^[0-9]+(h|d)$",
    "default": "24h"
  },
  "minEngagement": {
    "type": "integer",
    "minimum": 0,
    "default": 10000
  },
  "excludeTopics": {
    "type": "array",
    "items": { "type": "string" },
    "maxItems": 50
  }
}
```

**Validation Rules**:
- ✅ `platform` must be one of the 5 enum values
- ✅ `limit` must be 1-500 (enforce max 500)
- ✅ `timeWindow` must match pattern (e.g., "4h", "1d", "7d")
- ✅ `minEngagement` must be non-negative (default 10000 per FR-1.3)
- ✅ `excludeTopics` max 50 items for performance

---

## Output Schema

```json
{
  "trends": [
    {
      "id": "uuid4",
      "platform": "twitter|news|market|reddit|tiktok",
      "content": "string",
      "trend_velocity": 1.5,
      "engagement_score": 15000,
      "decay_score": 0.3,
      "created_at": "2026-02-06T10:30:00Z",
      "geographic_origin": "US|Ethiopia|Global",
      "metadata": {
        "platform_post_id": "123456",
        "source_url": "https://..."
      }
    }
  ],
  "fetched_at": "2026-02-06T10:35:00Z",
  "platform": "twitter",
  "count": 42,
  "truncated": false
}
```

**TrendData Schema Requirements** (from 2-design.md):
- `id`: UUID4, unique identifier
- `platform`: Must match input platform
- `content`: The trend topic or snippet
- `trend_velocity`: Float ≥ 0 (trends/minute)
- `engagement_score`: Integer 0-100, **must be ≥ minEngagement threshold**
- `decay_score`: Float 0-1 (recency factor)
- `created_at`: ISO8601 timestamp
- `geographic_origin`: Optional, e.g., "Ethiopia", "US", "Global"
- `metadata`: Dict with max 10 keys, max 256 bytes per value

---

## MCP Resources Used

### Primary Resources (5-mcp-resources.md)

| Platform | Resource | Rate Limit | Cache TTL | Fallback |
|----------|----------|-----------|-----------|----------|
| twitter | `twitter://mentions/recent` | 100/hr | 5min | `twitter://feed/{user_id}` |
| news | `news://global/trends` | 50/hr | 10min | `news://region/US/trends` |
| market | `market://crypto/{asset}/trending` | 200/hr | 5min | `market://trending/all` |
| reddit | `reddit://r/{subreddit}/trending` | 100/hr | 10min | `reddit://r/all/trending` |
| tiktok | `tiktok://trends/global` | 50/hr | 15min | `tiktok://trends/{region}` |

**Implementation**: 
1. Check rate limiter before MCP call (client-side enforcement)
2. Check cache (TTL per table above)
3. Call primary resource with 10s timeout
4. On timeout/unavailable, call fallback resource
5. On fallback timeout, return stale cache if available
6. If all fail, raise `EXT_PLATFORM_UNAVAILABLE` (7-error-codes.md)

---

## Error Handling

| Error Code | HTTP | Cause | Recovery |
|-----------|------|-------|----------|
| `EXT_PLATFORM_UNAVAILABLE` | 503 | MCP resource down | Retry with backoff (max 3x) |
| `EXT_RATE_LIMITED` | 429 | Hit rate limit | Backoff exponentially (2^attempt + jitter), max 30s |
| `EXT_INVALID_PLATFORM` | 400 | Platform not supported | Don't retry, escalate |
| `VAL_SCHEMA_INVALID` | 422 | Input validation failed | Don't retry, check input |
| `NET_TIMEOUT` | 504 | MCP call timeout | Retry with backoff |

**Retry Strategy** (per 7-error-codes.md):
```python
for attempt in range(3):
    try:
        return fetch_primary_resource()
    except (EXT_PLATFORM_UNAVAILABLE, NET_TIMEOUT):
        if attempt < 2:
            wait_time = min(2 ** attempt + random(0, 1), 30)
            sleep(wait_time)
        else:
            # Last attempt: try fallback, then stale cache, then raise
            try:
                return fetch_fallback_resource()
            except:
                stale = cache.get_expired(resource_key)
                if stale:
                    return stale
                raise EXT_PLATFORM_UNAVAILABLE()
```

---

## Implementation Checklist

### 1. Input Validation
- [ ] Validate `platform` is enum value (raise `VAL_SCHEMA_INVALID` if not)
- [ ] Validate `limit` 1-500 (raise `VAL_SCHEMA_INVALID` if not)
- [ ] Validate `timeWindow` matches `^[0-9]+(h|d)$` (raise `VAL_SCHEMA_INVALID` if not)
- [ ] Set defaults: `limit=50`, `timeWindow="24h"`, `minEngagement=10000`
- [ ] Validate `excludeTopics` max 50 items

### 2. Rate Limiting & Caching
- [ ] Initialize `RateLimiter(resource, rate_limit_per_hour)` for platform
- [ ] Call `rate_limiter.acquire()` (blocks if limit exceeded)
- [ ] Check `cache.get(cache_key, ttl=...)` per table above
- [ ] Return cached result if available (update metrics: cache_hit=true)
- [ ] If not cached, proceed to MCP call

### 3. MCP Resource Fetching
- [ ] Call primary resource with `timeout=10s`
- [ ] Parse response into intermediate list
- [ ] On TimeoutError: Try fallback resource with `timeout=10s`
- [ ] On fallback TimeoutError: Check `cache.get_expired(cache_key)` (stale cache)
- [ ] If stale cache available, return with `stale=true` flag in metadata
- [ ] If all fail, raise `EXT_PLATFORM_UNAVAILABLE`

### 4. TrendData Filtering & Transformation
- [ ] Filter results by `minEngagement` threshold (FR-1.3)
- [ ] Filter by `excludeTopics` if provided
- [ ] Transform MCP response to TrendData schema:
  - [ ] Generate `id` as UUID4
  - [ ] Set `platform` to input platform
  - [ ] Extract `content` (topic name/snippet)
  - [ ] Calculate `trend_velocity` (trends per minute = engagement/time_window_minutes)
  - [ ] Parse `engagement_score` from platform (normalize to 0-100 if needed)
  - [ ] Calculate `decay_score` (recency factor: 1.0 if < 1hr old, decay by 0.1 per hour)
  - [ ] Set `created_at` to ISO8601 timestamp
  - [ ] Extract `geographic_origin` if available (else "Global")
  - [ ] Populate `metadata` with platform-specific info

### 5. Response Formatting
- [ ] Return array of TrendData sorted by engagement_score (descending)
- [ ] Respect `limit` parameter (max 50 by default)
- [ ] Set `truncated=true` if more results available beyond limit
- [ ] Set `fetched_at` to current ISO8601 timestamp
- [ ] Set `count` to number of trends returned

### 6. Logging & Metrics
- [ ] Log at START: `fetch_trends_start` with {platform, limit, timeWindow, minEngagement}
- [ ] Log at SUCCESS: `fetch_trends_success` with {platform, count, duration_ms, cache_hit}
- [ ] Log at ERROR: `fetch_trends_error` with {platform, error_code, retry_count, duration_ms}
- [ ] Track metric: `fetch_trends_duration_ms` (should be < 8000 for P95)
- [ ] Track metric: `fetch_trends_cache_hit_rate` (higher is better for throughput)

---

## Example Implementation Pattern

```python
from typing import TypedDict
from datetime import datetime, timedelta
import uuid
import time

class FetchTrendsInput(TypedDict):
    platform: str
    limit: int
    timeWindow: str
    minEngagement: int
    excludeTopics: list[str]

class FetchTrendsOutput(TypedDict):
    trends: list  # TrendData[]
    fetched_at: str
    platform: str
    count: int
    truncated: bool

def fetch_trends(
    platform: str,
    limit: int = 50,
    timeWindow: str = "24h",
    minEngagement: int = 10000,
    excludeTopics: list[str] = None
) -> FetchTrendsOutput:
    """
    Fetch trending data from platform.
    
    Implements: skill_fetch_trends from 4-skills-api.md
    FR: FR-1.0 (Active Resource Monitoring), FR-1.3 (High-Engagement)
    Timeout: 30s | P95 Target: 8s
    
    Raises:
        VAL_SCHEMA_INVALID: Input validation failed
        EXT_PLATFORM_UNAVAILABLE: All resource fetches failed
        EXT_RATE_LIMITED: Hit rate limit (automatic retry)
    """
    start_time = time.time()
    
    # 1. Validate input
    validate_input(platform, limit, timeWindow, minEngagement)
    
    # 2. Rate limiting
    rate_limiter = get_rate_limiter(platform)
    rate_limiter.acquire()
    
    # 3. Check cache
    cache_key = f"{platform}:trends:{timeWindow}:{minEngagement}"
    cached = cache.get(cache_key)
    if cached:
        logger.info("fetch_trends_cache_hit", platform=platform)
        metrics.record("fetch_trends_cache_hit_rate", 1)
        return cached
    
    # 4. Fetch from MCP
    try:
        primary_resource = get_primary_resource(platform)
        with timeout(10):
            raw_data = mcp_client.fetch(primary_resource)
    except (TimeoutError, MCPError):
        logger.warning("fetch_trends_fallback", platform=platform)
        fallback_resource = get_fallback_resource(platform)
        try:
            with timeout(10):
                raw_data = mcp_client.fetch(fallback_resource)
        except:
            stale = cache.get_expired(cache_key)
            if stale:
                return stale
            raise SpecError(code="EXT_PLATFORM_UNAVAILABLE", http_status=503)
    
    # 5. Transform to TrendData
    trends = []
    for item in raw_data:
        if item['engagement_score'] >= minEngagement:
            if excludeTopics and item['content'] in excludeTopics:
                continue
            trend = transform_to_trend_data(item, platform)
            trends.append(trend)
    
    # 6. Format output
    trends.sort(key=lambda t: t['engagement_score'], reverse=True)
    truncated = len(trends) > limit
    trends = trends[:limit]
    
    result = {
        "trends": trends,
        "fetched_at": datetime.utcnow().isoformat(),
        "platform": platform,
        "count": len(trends),
        "truncated": truncated
    }
    
    # 7. Cache result
    cache.set(cache_key, result, ttl=get_cache_ttl(platform))
    
    # 8. Log success
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "fetch_trends_success",
        platform=platform,
        count=len(trends),
        duration_ms=duration_ms,
        cache_hit=False
    )
    metrics.record("fetch_trends_duration_ms", duration_ms)
    
    return result
```

---

## Testing Requirements

**Unit Tests** (from 3-verification.md):
- [ ] Test valid platform enum (twitter, news, market, reddit, tiktok)
- [ ] Test invalid platform (raise VAL_SCHEMA_INVALID)
- [ ] Test limit boundaries (1, 50, 500, 501 → reject > 500)
- [ ] Test timeWindow validation (valid: "1h", "4h", "24h", "7d"; invalid: "1w", "30min")
- [ ] Test minEngagement filtering (only return trends with score ≥ threshold)
- [ ] Test excludeTopics filtering
- [ ] Test engagement_score 0-100 normalization
- [ ] Test truncated flag (true when more results available)

**Integration Tests**:
- [ ] Mock MCP resources and verify fallback chain works
- [ ] Verify rate limiting (block after limit exceeded)
- [ ] Verify caching (return same result within TTL)
- [ ] Verify stale cache return on all failures
- [ ] Verify timeout recovery with exponential backoff

**Performance Tests**:
- [ ] P95 latency < 8s (spec: 30s timeout)
- [ ] Cache hit rate > 70% under normal load
- [ ] Memory usage < 50MB for 500 trends

---

## Debugging & Escalation

**If cache hit rate < 50%**:
Check TTL values in table above (may need to increase per platform demand patterns)

**If P95 > 8s**:
Profile which resource is slow (twitter vs news vs market), add parallelization if fetching multiple platforms

**If rate limit errors**:
Verify rate_limiter.acquire() is called before every MCP call; check concurrent request load

**If stale cache returned frequently**:
Indicates resource availability issue; escalate to platform support

---

## References

- **API Spec**: [specs/4-skills-api.md#1-fetch_trends](../specs/4-skills-api.md)
- **MCP Resources**: [specs/5-mcp-resources.md](../specs/5-mcp-resources.md)
- **Error Codes**: [specs/7-error-codes.md](../specs/7-error-codes.md)
- **Functional Req**: [specs/1-functional.md#fr-1](../specs/1-functional.md)
- **Design**: [specs/2-design.md#trend-data-schema](../specs/2-design.md)
- **Verification**: [specs/3-verification.md#fr-1-trend-discovery](../specs/3-verification.md)
