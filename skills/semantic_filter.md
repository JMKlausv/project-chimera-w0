# Skill: semantic_filter

## Overview
Filter trends by relevance to campaign goals using lightweight LLM scoring. This gates which trends proceed to content generation.

**Agent**: Orchestrator / Trend Analyst  
**FR**: FR-1.1 (Semantic Filtering & Relevance Scoring)  
**Timeout**: 10s | **P95 Target**: 3s

---

## Input Schema

```json
{
  "trends": [
    {
      "id": "uuid4",
      "platform": "string",
      "content": "string",
      "engagement_score": 15000,
      "decay_score": 0.7,
      "created_at": "2026-02-06T10:30:00Z",
      "metadata": {}
    }
  ],
  "campaign_goals": {
    "primary_goal": "increase_followers",
    "target_audience": "Gen Z",
    "topics_of_interest": ["technology", "fashion", "finance"],
    "sentiment_preference": "positive|neutral|mixed",
    "minimum_relevance_threshold": 0.75
  }
}
```

**Validation Rules**:
- ✅ `trends` must be non-empty array of TrendData
- ✅ `campaign_goals.primary_goal` must be valid goal type
- ✅ `campaign_goals.minimum_relevance_threshold` must be 0.0-1.0 (default 0.75)
- ✅ `campaign_goals.topics_of_interest` max 20 items
- ✅ `campaign_goals.sentiment_preference` must be enum: positive|neutral|mixed

---

## Output Schema

```json
{
  "filtered_trends": [
    {
      "id": "uuid4",
      "relevance_score": 0.87,
      "relevance_reasoning": "Aligns with target audience interest in tech + 15K engagement",
      "should_process": true,
      "campaign_fit": "high|medium|low",
      "audience_fit": "high|medium|low",
      "engagement_potential": 0.85,
      "original_trend": { ...TrendData... }
    }
  ],
  "filtered_count": 12,
  "accepted_count": 8,
  "rejected_count": 4,
  "filtering_confidence": 0.89,
  "processed_at": "2026-02-06T10:35:00Z"
}
```

**Output Requirements**:
- `relevance_score`: Float 0.0-1.0 (higher = more relevant)
- `should_process`: Boolean (true if score ≥ minimum_relevance_threshold)
- `campaign_fit`: Discrete enum (high/medium/low)
- `audience_fit`: Discrete enum (high/medium/low)
- `engagement_potential`: Float 0.0-1.0 (how likely audience will engage)
- `relevance_reasoning`: String explanation for debugging
- All trends returned (accepted + rejected) for audit trail

---

## Filtering Criteria

Score trends on 0.0-1.0 scale considering:

| Factor | Weight | Description |
|--------|--------|-------------|
| Topic alignment | 30% | Trend topic matches `topics_of_interest` |
| Engagement potential | 25% | Normalized engagement_score (15K=high, <1K=low) |
| Audience match | 20% | Trend appeals to `target_audience` demographics |
| Sentiment alignment | 15% | Trend sentiment matches `sentiment_preference` |
| Recency/decay | 10% | Recent trends (high decay_score) score higher |

**Calculation**:
```
relevance_score = (
    0.30 * topic_score +
    0.25 * engagement_score +
    0.20 * audience_score +
    0.15 * sentiment_score +
    0.10 * recency_score
)
```

**Decision Rule** (FR-1.1):
- If `relevance_score ≥ campaign_goals.minimum_relevance_threshold` → `should_process = true`
- Else → `should_process = false` (don't automatically respond)

---

## LLM Integration

Use **Gemini 3 Flash** (lightweight) for scoring:

```python
prompt = f"""
Analyze this trend for relevance to the following campaign:

Trend: {trend['content']}
Platform: {trend['platform']}
Engagement: {trend['engagement_score']}

Campaign:
- Primary Goal: {campaign_goals['primary_goal']}
- Target Audience: {campaign_goals['target_audience']}
- Topics of Interest: {', '.join(campaign_goals['topics_of_interest'])}
- Sentiment Preference: {campaign_goals['sentiment_preference']}

Score relevance on 0.0-1.0 scale (0=irrelevant, 1=perfect fit).
Also score each factor (topic, engagement, audience, sentiment, recency) separately.
Provide brief reasoning.

Return JSON:
{{
  "relevance_score": 0.87,
  "topic_score": 0.9,
  "engagement_score": 0.8,
  "audience_score": 0.85,
  "sentiment_score": 0.75,
  "recency_score": 0.9,
  "reasoning": "..."
}}
"""

response = gemini_client.generate(
    prompt=prompt,
    temperature=0.3,  # Low temperature for consistent scoring
    timeout=8  # Leave headroom for post-processing
)
```

**Cost Optimization**:
- Use Flash model (fastest inference)
- Batch score multiple trends in one LLM call if > 10 trends
- Cache scores for identical trend topics (same topic + goal within 24h)

---

## Error Handling

| Error Code | HTTP | Cause | Recovery |
|-----------|------|-------|----------|
| `FILTER_TIMEOUT` | 504 | LLM timeout | Return unscored trends with `filtering_confidence=0` |
| `INVALID_INPUT` | 422 | Schema validation failed | Don't filter, return error |
| `LLM_SERVICE_UNAVAILABLE` | 503 | Gemini API down | Return all trends (accept all) |

**Fallback**: If LLM unavailable:
- Return all trends with `should_process=true`
- Set `filtering_confidence=0` 
- Log warning: "Filtering disabled; returning all trends"

---

## Implementation Checklist

### 1. Input Validation
- [ ] Validate `trends` is non-empty array
- [ ] Validate each trend has required TrendData fields
- [ ] Validate `campaign_goals` structure
- [ ] Validate `minimum_relevance_threshold` is 0.0-1.0
- [ ] Validate `topics_of_interest` max 20 items
- [ ] Set default: `minimum_relevance_threshold=0.75`

### 2. Batch Processing
- [ ] If > 10 trends, batch LLM calls (5 trends per call)
- [ ] If ≤ 10 trends, process in single LLM call
- [ ] Parallelize batches if processing > 50 trends

### 3. LLM Scoring
- [ ] Call Gemini 3 Flash with prompt (see LLM Integration above)
- [ ] Parse response JSON (handle malformed responses)
- [ ] Validate score is 0.0-1.0 (clamp if needed)
- [ ] Log LLM call: duration, token count, confidence

### 4. Decision Making
- [ ] For each trend:
  - [ ] If `relevance_score ≥ threshold` → `should_process=true`
  - [ ] Else → `should_process=false`
- [ ] Assign discrete categories:
  - [ ] `campaign_fit`: high if score ≥ 0.8, medium if ≥ 0.6, else low
  - [ ] `audience_fit`: high if audience_score ≥ 0.8, medium if ≥ 0.6, else low

### 5. Output Formatting
- [ ] Return all trends (accepted + rejected) in `filtered_trends`
- [ ] Sort by `relevance_score` descending (highest first)
- [ ] Calculate aggregates:
  - [ ] `filtered_count` = total trends input
  - [ ] `accepted_count` = trends with should_process=true
  - [ ] `rejected_count` = trends with should_process=false
- [ ] Calculate `filtering_confidence`:
  - [ ] If all LLM calls succeeded → 0.95
  - [ ] If 1 batch failed → 0.85
  - [ ] If LLM unavailable → 0.0

### 6. Logging & Metrics
- [ ] Log at START: `semantic_filter_start` with {campaign_id, trend_count, threshold}
- [ ] Log at SUCCESS: `semantic_filter_success` with {accepted_count, rejected_count, avg_score}
- [ ] Log each trend scored (for audit): {trend_id, score, reasoning}
- [ ] Track metric: `semantic_filter_duration_ms` (should be < 3000 for P95)
- [ ] Track metric: `semantic_filter_acceptance_rate` (monitor threshold calibration)

---

## Example Implementation Pattern

```python
from typing import TypedDict
import json

class FilteredTrend(TypedDict):
    id: str
    relevance_score: float
    relevance_reasoning: str
    should_process: bool
    campaign_fit: str
    audience_fit: str
    engagement_potential: float
    original_trend: dict

def semantic_filter(
    trends: list,
    campaign_goals: dict
) -> dict:
    """
    Filter trends by relevance to campaign goals.
    
    Implements: skill_semantic_filter from 4-skills-api.md
    FR: FR-1.1 (Semantic Filtering & Relevance Scoring)
    Timeout: 10s | P95 Target: 3s
    
    Args:
        trends: List of TrendData objects from fetch_trends
        campaign_goals: Campaign configuration with goals, audience, topics
    
    Returns:
        Dict with filtered_trends, counts, confidence
    """
    start_time = time.time()
    
    # 1. Validate input
    validate_input(trends, campaign_goals)
    threshold = campaign_goals.get('minimum_relevance_threshold', 0.75)
    
    # 2. Batch LLM scoring
    filtered_trends = []
    
    # Split into batches of 5 for LLM efficiency
    batch_size = 5
    batches = [trends[i:i+batch_size] for i in range(0, len(trends), batch_size)]
    
    accepted_count = 0
    total_score = 0
    
    for batch in batches:
        # Call LLM for batch
        try:
            with timeout(8):
                batch_scores = score_batch_with_llm(batch, campaign_goals)
        except TimeoutError:
            logger.warning("semantic_filter_timeout", trend_count=len(batch))
            # Fallback: accept all
            batch_scores = [{
                'id': t['id'],
                'relevance_score': threshold,
                'should_process': True,
                'reasoning': 'LLM timeout; default accept'
            } for t in batch]
        
        # Process batch results
        for trend, score_result in zip(batch, batch_scores):
            relevance_score = score_result['relevance_score']
            should_process = relevance_score >= threshold
            
            if should_process:
                accepted_count += 1
            
            total_score += relevance_score
            
            # Assign discrete categories
            if relevance_score >= 0.8:
                campaign_fit = 'high'
            elif relevance_score >= 0.6:
                campaign_fit = 'medium'
            else:
                campaign_fit = 'low'
            
            filtered_trend = FilteredTrend(
                id=trend['id'],
                relevance_score=relevance_score,
                relevance_reasoning=score_result['reasoning'],
                should_process=should_process,
                campaign_fit=campaign_fit,
                audience_fit=score_result.get('audience_fit', 'medium'),
                engagement_potential=score_result.get('engagement_score', 0.5),
                original_trend=trend
            )
            filtered_trends.append(filtered_trend)
    
    # Sort by relevance (highest first)
    filtered_trends.sort(key=lambda t: t['relevance_score'], reverse=True)
    
    # 3. Format output
    result = {
        'filtered_trends': filtered_trends,
        'filtered_count': len(trends),
        'accepted_count': accepted_count,
        'rejected_count': len(trends) - accepted_count,
        'filtering_confidence': 0.95 if len(batches) > 0 else 0.0,
        'processed_at': datetime.utcnow().isoformat()
    }
    
    # 4. Log success
    duration_ms = (time.time() - start_time) * 1000
    avg_score = total_score / len(trends) if trends else 0
    logger.info(
        'semantic_filter_success',
        accepted_count=accepted_count,
        rejected_count=result['rejected_count'],
        avg_score=avg_score,
        duration_ms=duration_ms
    )
    metrics.record('semantic_filter_duration_ms', duration_ms)
    metrics.record('semantic_filter_acceptance_rate', accepted_count / len(trends) if trends else 0)
    
    return result
```

---

## Testing Requirements

**Unit Tests**:
- [ ] Test threshold filtering (score 0.75 accepted, 0.74 rejected)
- [ ] Test discrete category assignment (0.8+ = high, 0.6+ = medium)
- [ ] Test all trends returned (no data loss)
- [ ] Test campaign_fit/audience_fit assignments
- [ ] Test LLM timeout fallback (return all trends)
- [ ] Test batch processing (1 trend, 5 trends, 25 trends)

**Integration Tests**:
- [ ] Mock Gemini API and verify prompt structure
- [ ] Verify cached scores used for duplicate topics
- [ ] Verify acceptance rate ~ 40-60% under normal load (tunable)
- [ ] Verify LLM token usage reasonable (not exceeding quota)

**Performance Tests**:
- [ ] P95 latency < 3s (spec: 10s timeout)
- [ ] Batch processing latency scales linearly (not exponential)
- [ ] Cache hit rate > 60% for repeated campaigns

---

## Debugging & Escalation

**If acceptance rate too high (>80%)**:
- Threshold may be too low; increase `minimum_relevance_threshold` to 0.8
- Or LLM may be over-generous; review LLM prompt

**If acceptance rate too low (<20%)**:
- Threshold may be too high; decrease to 0.6
- Or campaign goals too restrictive; review topic list

**If LLM cost too high**:
- Reduce batch size
- Implement topic-based pre-filter (reject obvious non-matches before LLM)
- Increase cache TTL

---

## References

- **API Spec**: [specs/4-skills-api.md#2-semantic_filter](../specs/4-skills-api.md)
- **Functional Req**: [specs/1-functional.md#fr-1-1](../specs/1-functional.md)
- **Design**: [specs/2-design.md#semantic-filter-pipeline](../specs/2-design.md)
- **Error Codes**: [specs/7-error-codes.md](../specs/7-error-codes.md)
- **Verification**: [specs/3-verification.md#fr-1-edge-cases](../specs/3-verification.md)
