# Skill: publish_content

## Overview
Publish approved content to social platforms via MCP resources. Final step in the content distribution pipeline.

**Agent**: Distribution Manager  
**FR**: FR-1, FR-4 (Content Publishing, OpenClaw Integration)  
**Timeout**: 15s | **P95 Target**: 10s

---

## Input Schema

```json
{
  "content_id": "uuid4",
  "script": "string",
  "platform": "twitter|tiktok|instagram|reddit",
  "approval_token": "jwt_token_signed_by_human_reviewer",
  "metadata": {
    "agent_id": "uuid4",
    "campaign_id": "uuid4",
    "content_type": "post|caption|video_script",
    "scheduled_time": "2026-02-06T15:00:00Z"  # Optional, for scheduling
  }
}
```

**Validation Rules**:
- ✅ `content_id` must be valid UUID4
- ✅ `script` must be non-empty string
- ✅ `platform` must be enum (twitter, tiktok, instagram, reddit)
- ✅ `approval_token` must be valid JWT signed by approver
  - [ ] Verify signature with public key
  - [ ] Check expiration (valid for 24 hours)
  - [ ] Check token references correct content_id
- ✅ `metadata.agent_id` must be valid UUID4

---

## Output Schema

```json
{
  "content_id": "uuid4",
  "post_id": "platform_post_id_123456",
  "post_url": "https://twitter.com/agent/status/123456",
  "platform": "twitter",
  "published_at": "2026-02-06T15:00:30Z",
  "metrics": {
    "initial_engagement": {
      "likes": 12,
      "retweets": 3,
      "replies": 2,
      "impressions": 500
    },
    "timestamp": "2026-02-06T15:00:30Z"
  }
}
```

**Output Requirements**:
- `post_id`: Platform-specific post ID (for tracking)
- `post_url`: Direct link to published post
- `published_at`: ISO8601 timestamp of publication
- `metrics.initial_engagement`: Engagement snapshot at publish time

---

## MCP Resources Used

| Platform | Resource | Request | Response | Timeout |
|----------|----------|---------|----------|---------|
| twitter | `twitter://post` | {text, reply_to_id?} | {post_id, url, created_at} | 10s |
| tiktok | `tiktok://upload` | {video_url, caption} | {video_id, url, status} | 15s |
| instagram | `instagram://post` | {image_url, caption} | {post_id, url} | 12s |
| reddit | `reddit://submit` | {subreddit, title, text} | {post_id, url} | 10s |

**Rate Limits** (from 5-mcp-resources.md):
- Twitter: 300 posts/15min (20 posts/min)
- TikTok: 10 uploads/day
- Instagram: 200 posts/24hr
- Reddit: 9 posts/10min

---

## Approval Token Verification

**JWT Structure**:
```json
{
  "alg": "RS256",
  "typ": "JWT"
}
.
{
  "iss": "chimera.approver",
  "sub": "human_reviewer_id",
  "content_id": "uuid4",
  "approval_time": "2026-02-06T10:35:00Z",
  "expires_at": "2026-02-07T10:35:00Z",
  "approval_type": "APPROVED|APPROVED_WITH_EDITS",
  "edits": {
    "script": "edited_text_if_applicable"
  }
}
```

**Verification Steps**:
1. Verify JWT signature with public key (from secure key store)
2. Check expiration: `expires_at > now()`
3. Check content_id matches: `token.content_id == input.content_id`
4. If `approval_type=APPROVED_WITH_EDITS`, use `token.edits.script` instead of input script

---

## Error Handling

| Error Code | HTTP | Cause | Recovery |
|-----------|------|-------|----------|
| `INVALID_TOKEN` | 401 | Token expired, signature invalid, or mismatch | Don't publish, return error |
| `EXT_PLATFORM_UNAVAILABLE` | 503 | Platform API down | Retry with backoff (max 3x) |
| `RATE_LIMITED` | 429 | Hit rate limit for platform | Queue and retry later |
| `PUBLISH_FAILED` | 500 | Platform rejected content | Log error and escalate |

**Retry Strategy**:
```python
for attempt in range(3):
    try:
        with timeout(15):
            result = publish_to_platform()
        return result
    except (EXT_PLATFORM_UNAVAILABLE, RATE_LIMITED):
        if attempt < 2:
            wait_time = min(2**attempt + random(0, 1), 60)
            sleep(wait_time)
        else:
            # Queue for later retry (max 24h backoff)
            queue_for_retry(content_id, platform, max_retries=10)
            raise
```

---

## Implementation Checklist

### 1. Input Validation
- [ ] Validate `content_id` is UUID4
- [ ] Validate `script` is non-empty
- [ ] Validate `platform` is enum
- [ ] Validate `approval_token` format (JWT)
- [ ] Validate `metadata.agent_id` is UUID4

### 2. Token Verification
- [ ] Load public key from secure key store
- [ ] Verify JWT signature
  - [ ] Raise `INVALID_TOKEN` if signature invalid
- [ ] Check expiration
  - [ ] Raise `INVALID_TOKEN` if expired
- [ ] Check content_id matches
  - [ ] Raise `INVALID_TOKEN` if mismatch
- [ ] Extract approval type (APPROVED or APPROVED_WITH_EDITS)
- [ ] If APPROVED_WITH_EDITS, use `token.edits.script`

### 3. Rate Limiting Check
- [ ] Check current rate limit usage for platform
- [ ] If at limit, queue for later (don't fail)
  - [ ] Return pending status
  - [ ] Background worker retries later

### 4. Platform-Specific Publishing
- [ ] Determine MCP resource URL per platform
- [ ] Build request payload per platform spec
- [ ] Call MCP resource with timeout
- [ ] Parse response (handle platform-specific fields)

**Twitter Publishing**:
```python
mcp_request = {
    "text": script,
    "reply_to_id": metadata.get('reply_to_id')
}
response = mcp_client.post("twitter://post", mcp_request)
post_id = response['post_id']
post_url = response['url']  # e.g., https://twitter.com/user/status/123
```

**TikTok Publishing**:
```python
# TikTok requires video upload (more complex)
mcp_request = {
    "video_url": metadata.get('video_url'),
    "caption": script
}
response = mcp_client.post("tiktok://upload", mcp_request)
# Wait for processing (may return "processing" status)
```

### 5. Post-Publish Actions
- [ ] Fetch initial engagement metrics
  - [ ] Twitter: likes, retweets, replies, impressions
  - [ ] TikTok: views, likes (may delay)
  - [ ] Instagram: likes, comments
  - [ ] Reddit: upvotes, comments
- [ ] Record `published_at` timestamp
- [ ] Store post_id + post_url for tracking

### 6. Logging & Metrics
- [ ] Log at START: `publish_content_start` with {platform, content_id}
- [ ] Log at SUCCESS: `publish_content_success` with {post_id, post_url, duration_ms}
- [ ] Log at QUEUE: If rate limited, `publish_content_queued` for retry
- [ ] Track metric: `publish_content_duration_ms` (should be < 10000 for P95)
- [ ] Track metric: `publish_content_success_rate` per platform
- [ ] Track metric: `publish_content_initial_engagement` (likes, impressions, etc.)

### 7. Campaign Tracking
- [ ] Update campaign metrics with published post
- [ ] Link post_id to campaign_id for analytics
- [ ] Enable engagement tracking (pull metrics periodically)

---

## Example Implementation Pattern

```python
from typing import TypedDict
import jwt
from datetime import datetime

class PublishContentInput(TypedDict):
    content_id: str
    script: str
    platform: str
    approval_token: str
    metadata: dict

class PublishContentOutput(TypedDict):
    content_id: str
    post_id: str
    post_url: str
    platform: str
    published_at: str
    metrics: dict

def publish_content(
    content_id: str,
    script: str,
    platform: str,
    approval_token: str,
    metadata: dict
) -> PublishContentOutput:
    """
    Publish content to social platform.
    
    Implements: skill_publish_content from 4-skills-api.md
    FR: FR-1 (Content Publishing)
    Timeout: 15s | P95 Target: 10s
    
    Requires valid approval_token signed by human reviewer.
    """
    start_time = time.time()
    
    # 1. Validate input
    validate_input(content_id, script, platform, approval_token, metadata)
    
    # 2. Verify approval token
    try:
        public_key = get_public_key('approver')
        token_payload = jwt.decode(
            approval_token,
            public_key,
            algorithms=['RS256']
        )
    except jwt.ExpiredSignatureError:
        raise SpecError(code="INVALID_TOKEN", http_status=401)
    except jwt.InvalidSignatureError:
        raise SpecError(code="INVALID_TOKEN", http_status=401)
    
    # Check content_id matches
    if token_payload['content_id'] != content_id:
        raise SpecError(code="INVALID_TOKEN", http_status=401)
    
    # Check expiration
    if datetime.fromisoformat(token_payload['expires_at']) < datetime.utcnow():
        raise SpecError(code="INVALID_TOKEN", http_status=401)
    
    # Use edited script if provided
    if token_payload.get('approval_type') == 'APPROVED_WITH_EDITS':
        script = token_payload['edits']['script']
    
    # 3. Check rate limit
    rate_limit_info = check_rate_limit(platform)
    if rate_limit_info['usage'] >= rate_limit_info['limit']:
        # Queue for later retry
        queue_for_retry(content_id, platform)
        logger.info('publish_content_queued', platform=platform, content_id=content_id)
        return {
            'content_id': content_id,
            'status': 'QUEUED',
            'retry_at': calculate_retry_time(platform)
        }
    
    # 4. Build platform-specific request
    if platform == 'twitter':
        mcp_request = {
            'text': script,
            'reply_to_id': metadata.get('reply_to_id')
        }
        mcp_resource = 'twitter://post'
    elif platform == 'tiktok':
        mcp_request = {
            'video_url': metadata['video_url'],
            'caption': script
        }
        mcp_resource = 'tiktok://upload'
    elif platform == 'instagram':
        mcp_request = {
            'image_url': metadata['image_url'],
            'caption': script
        }
        mcp_resource = 'instagram://post'
    elif platform == 'reddit':
        mcp_request = {
            'subreddit': metadata['subreddit'],
            'title': metadata.get('title', ''),
            'text': script
        }
        mcp_resource = 'reddit://submit'
    
    # 5. Publish with retry
    for attempt in range(3):
        try:
            with timeout(15):
                response = mcp_client.post(mcp_resource, mcp_request)
            break
        except (TimeoutError, MCPError) as e:
            if attempt < 2:
                wait_time = min(2**attempt + random(0, 1), 60)
                logger.warning(f"publish_retry {attempt+1}/3", platform=platform)
                sleep(wait_time)
            else:
                # Queue for background retry
                queue_for_retry(content_id, platform)
                raise SpecError(code="EXT_PLATFORM_UNAVAILABLE", http_status=503)
    
    # 6. Extract platform-specific response
    post_id = response['post_id']
    post_url = response.get('url') or response.get('post_url')
    published_at = response.get('created_at', datetime.utcnow().isoformat())
    
    # 7. Fetch initial metrics
    initial_metrics = fetch_engagement_metrics(platform, post_id)
    
    result = PublishContentOutput(
        content_id=content_id,
        post_id=post_id,
        post_url=post_url,
        platform=platform,
        published_at=published_at,
        metrics={
            'initial_engagement': initial_metrics,
            'timestamp': published_at
        }
    )
    
    # 8. Update campaign tracking
    update_campaign_metrics(metadata['campaign_id'], post_id, platform)
    
    # 9. Log success
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        'publish_content_success',
        content_id=content_id,
        post_id=post_id,
        platform=platform,
        duration_ms=duration_ms
    )
    metrics.record('publish_content_duration_ms', duration_ms)
    
    return result
```

---

## Testing Requirements

**Unit Tests**:
- [ ] Valid approval token → publish succeeds
- [ ] Expired token → `INVALID_TOKEN` error
- [ ] Invalid signature → `INVALID_TOKEN` error
- [ ] Content_id mismatch → `INVALID_TOKEN` error
- [ ] Token with edits → use edited script
- [ ] Rate limit reached → queue for retry
- [ ] All 4 platforms (twitter, tiktok, instagram, reddit)

**Integration Tests**:
- [ ] Mock MCP resources and verify request format
- [ ] Verify retry logic (exponential backoff)
- [ ] Verify initial metrics fetched
- [ ] Verify campaign tracking updated
- [ ] Verify approval token validation with real JWT library

**Performance Tests**:
- [ ] P95 latency < 10s (spec: 15s timeout)
- [ ] Can publish 50 posts/min under load
- [ ] Rate limiting respected per platform

---

## Debugging & Escalation

**If approval_token keeps failing**:
- Check public key is correct and fresh
- Verify JWT library version compatible
- Check token expiration settings

**If P95 > 10s**:
- Profile which platform is slow
- Consider parallelizing metric fetches
- Check network latency to MCP

**If rate limit errors frequent**:
- Reduce publish frequency or distribute across time
- Verify rate_limiter.check() accurate per platform
- Consider batching if platform supports it

**If initial metrics not available**:
- Some platforms have delay in metrics availability
- May need to refetch metrics after 30-60 seconds
- Document platform-specific delays

---

## References

- **API Spec**: [specs/4-skills-api.md#5-publish_content](../specs/4-skills-api.md)
- **MCP Resources**: [specs/5-mcp-resources.md](../specs/5-mcp-resources.md)
- **Functional Req**: [specs/1-functional.md#fr-1](../specs/1-functional.md)
- **Error Codes**: [specs/7-error-codes.md](../specs/7-error-codes.md)
- **Verification**: [specs/3-verification.md#fr-4-distribution](../specs/3-verification.md)
