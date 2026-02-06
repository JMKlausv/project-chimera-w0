# Skill: generate_content

## Overview
Generate platform-specific content (video scripts, captions, posts) based on trends and agent personas. This is the creative core of the content creation pipeline.

**Agent**: Content Creator  
**FR**: FR-2 (Content Generation)  
**Timeout**: 45s | **P95 Target**: 25s

---

## Input Schema

```json
{
  "trend": {
    "id": "uuid4",
    "platform": "twitter|news|market|reddit|tiktok",
    "content": "string",
    "engagement_score": 15000,
    "created_at": "2026-02-06T10:30:00Z",
    "metadata": {}
  },
  "persona": {
    "agent_id": "uuid4",
    "voice_tone": "humorous|formal|inspirational|casual",
    "target_audience": "Gen Z|Millennials|Professionals",
    "expertise_areas": ["technology", "finance"],
    "vocabulary": {
      "forbidden_words": ["slur1", "slur2"],
      "preferred_terms": {"tech": "technology", "crypto": "digital assets"}
    },
    "content_guidelines": {
      "max_length": 280,
      "include_hashtags": true,
      "include_emojis": true,
      "call_to_action": "follow|like|share|comment"
    }
  },
  "platform": "twitter",
  "content_type": "video_script|caption|post|hashtag_set"
}
```

**Validation Rules**:
- ✅ `trend` must be valid TrendData
- ✅ `persona` must match Agent Persona schema (2-design.md)
- ✅ `voice_tone` must be one of 4 enum values
- ✅ `platform` must match trend platform
- ✅ `content_type` must be enum: video_script|caption|post|hashtag_set
- ✅ `vocabulary.forbidden_words` must not contain empty strings
- ✅ `content_guidelines.max_length` > 0

---

## Output Schema

```json
{
  "content_id": "uuid4",
  "content_type": "video_script|caption|post|hashtag_set",
  "platform": "twitter",
  "script": "string",
  "confidence_score": 0.87,
  "safety_score": 0.95,
  "engagement_prediction": 0.82,
  "metadata": {
    "word_count": 45,
    "has_hashtags": true,
    "has_call_to_action": true,
    "tone_detected": "humorous",
    "length_compliant": true
  },
  "generated_at": "2026-02-06T10:35:00Z",
  "persona_alignment": {
    "voice_tone_match": 0.92,
    "vocabulary_compliance": 1.0,
    "guideline_compliance": 0.98
  }
}
```

**Output Requirements**:
- `script`: Generated content (string)
- `confidence_score`: Float 0.0-1.0 (AI confidence in quality)
- `safety_score`: Float 0.0-1.0 (absence of harmful content)
- `engagement_prediction`: Float 0.0-1.0 (predicted audience engagement)
- `metadata`: Platform-specific details (word count, hashtags, etc.)
- `persona_alignment`: How well generated content matches persona constraints

---

## Content Generation Strategy

### By Content Type

| Type | Purpose | Format | Example |
|------|---------|--------|---------|
| `video_script` | TikTok/YouTube short | 15-60 sec narration | "Here's why crypto is..." |
| `caption` | Instagram/TikTok post caption | < 2200 chars | "Just dropped a video on..." |
| `post` | Twitter/Reddit post | Platform-specific max | "🔥 Hot take on tech trends..." |
| `hashtag_set` | Hashtag suggestions | Array of 5-10 tags | ["#TechTrends", "#CryptoNews"] |

### Persona-Based Voice

Map `voice_tone` to LLM instructions:

```python
VOICE_PROMPTS = {
    "humorous": "Use wit, puns, and humor. Make the audience laugh while educating.",
    "formal": "Professional tone. Authoritative. Data-backed. No slang.",
    "inspirational": "Motivational. Empowering. Focus on possibility and growth.",
    "casual": "Friendly, conversational. Like talking to a friend. Relaxed."
}
```

### Constraint Enforcement

**Mandatory Checks** (before returning):

1. **No forbidden words** (vocabulary.forbidden_words)
   - Scan script for exact matches (case-insensitive)
   - Raise `VAL_SCHEMA_INVALID` if found
   
2. **Length compliance** (content_guidelines.max_length)
   - For captions/posts: ≤ max_length
   - For video scripts: Readable in 15-60 sec at 150 wpm
   - Raise `VAL_SCHEMA_INVALID` if exceeded
   
3. **Call-to-action** (if content_guidelines.call_to_action specified)
   - Must include CTA (e.g., "Follow for more", "Like if you agree")
   - Raise `VAL_SCHEMA_INVALID` if missing
   
4. **Safety check** (no slurs, violence, hate speech)
   - Use Gemini moderation API or safety filter
   - Raise `GENERATION_UNSAFE` if unsafe content detected

---

## LLM Integration

Use **Gemini 3 Flash** for generation:

```python
prompt = f"""
You are a content creator with the following persona:

Voice Tone: {persona['voice_tone']}
Target Audience: {persona['target_audience']}
Expertise Areas: {', '.join(persona['expertise_areas'])}

Additional Instructions:
- {VOICE_PROMPTS[persona['voice_tone']]}
- Tone should match {persona['voice_tone']}
- Write for {persona['target_audience']} audience
- Content must be for {platform}
- Type: {content_type}

Content Constraints:
- Maximum length: {persona['content_guidelines']['max_length']} chars
- Must include call-to-action: {persona['content_guidelines'].get('call_to_action', 'N/A')}
- Include hashtags: {persona['content_guidelines']['include_hashtags']}
- Include emojis: {persona['content_guidelines']['include_emojis']}
- FORBIDDEN words (absolutely never use): {', '.join(persona['vocabulary']['forbidden_words'])}
- Use these preferred terms: {json.dumps(persona['vocabulary']['preferred_terms'])}

Trend to base content on:
Topic: {trend['content']}
Platform: {trend['platform']}
Engagement: {trend['engagement_score']} interactions

Generate a {content_type} that:
1. Directly addresses the trend
2. Matches the voice tone perfectly
3. Appeals to {persona['target_audience']}
4. Complies with all constraints above
5. Includes relevant call-to-action

Return ONLY the generated {content_type}, no explanations.
"""

response = gemini_client.generate(
    prompt=prompt,
    temperature=0.7,  # Balanced creativity
    timeout=40  # Leave headroom for validation
)
```

---

## Error Handling

| Error Code | HTTP | Cause | Recovery |
|-----------|------|-------|----------|
| `GENERATION_TIMEOUT` | 504 | LLM timeout | Retry with shorter context |
| `INVALID_PERSONA` | 422 | Persona schema invalid | Don't generate, return error |
| `GENERATION_UNSAFE` | 400 | Generated content unsafe | Regenerate with stricter prompt |
| `VAL_SCHEMA_INVALID` | 422 | Constraint violation (forbidden words, length) | Regenerate or escalate |

**Retry Strategy**:
```python
for attempt in range(3):
    try:
        script = call_llm_to_generate()
        validate_constraints(script, persona)
        return script
    except VAL_SCHEMA_INVALID as e:
        if attempt < 2:
            # Add constraint violation to prompt and retry
            prompt += f"\nConstraint violation: {e}. Fix this."
            continue
        else:
            raise  # Give up after 3 attempts
```

---

## Implementation Checklist

### 1. Input Validation
- [ ] Validate `trend` is complete TrendData
- [ ] Validate `persona` against Agent Persona schema
- [ ] Validate `voice_tone` is enum (humorous|formal|inspirational|casual)
- [ ] Validate `platform` matches trend.platform
- [ ] Validate `content_type` is enum
- [ ] Validate `vocabulary.forbidden_words` non-empty and unique

### 2. Persona Validation
- [ ] Check persona exists (get_agent_profile if needed)
- [ ] Check persona.voice_tone is one of 4 enums
- [ ] Check persona.target_audience is valid
- [ ] Check expertise_areas is non-empty list

### 3. LLM Generation
- [ ] Build prompt with persona + trend + constraints (see above)
- [ ] Call Gemini 3 Flash with temperature=0.7
- [ ] Parse response (handle streaming if needed)
- [ ] Log LLM call: duration, token count, temperature

### 4. Constraint Validation
- [ ] **Forbidden words check**: Scan for exact matches (case-insensitive)
  - [ ] Raise `VAL_SCHEMA_INVALID` if any found
- [ ] **Length check**: Count chars/words
  - [ ] For captions: ≤ max_length
  - [ ] For video scripts: ≤ (duration_seconds * 150/60) words
  - [ ] Raise `VAL_SCHEMA_INVALID` if exceeded
- [ ] **CTA check**: If `call_to_action` specified, ensure present
  - [ ] Look for keywords: "follow", "like", "share", "comment", "subscribe", etc.
  - [ ] Raise `VAL_SCHEMA_INVALID` if missing
- [ ] **Safety check**: Run moderation API
  - [ ] If unsafe content → Regenerate with stricter prompt
  - [ ] If still unsafe after 2 retries → Raise `GENERATION_UNSAFE`

### 5. Scoring & Metadata
- [ ] Calculate `confidence_score` (LLM confidence from response metadata)
- [ ] Calculate `safety_score` (moderation score)
- [ ] Calculate `engagement_prediction` based on content length, sentiment, CTAs
- [ ] Extract metadata:
  - [ ] `word_count`: Length in words
  - [ ] `has_hashtags`: Boolean (if persona requires)
  - [ ] `has_call_to_action`: Boolean
  - [ ] `tone_detected`: Re-analyze with Gemini to verify tone match
  - [ ] `length_compliant`: Boolean (is ≤ max_length)
- [ ] Calculate persona_alignment scores:
  - [ ] `voice_tone_match`: 0.0-1.0 (does tone match persona?)
  - [ ] `vocabulary_compliance`: 1.0 if no forbidden words, else 0.0
  - [ ] `guideline_compliance`: Avg of all constraint checks

### 6. Response Formatting
- [ ] Generate unique `content_id` as UUID4
- [ ] Return full output schema
- [ ] Set `generated_at` to current ISO8601 timestamp

### 7. Logging & Metrics
- [ ] Log at START: `generate_content_start` with {platform, content_type, voice_tone}
- [ ] Log at SUCCESS: `generate_content_success` with {content_id, confidence, safety, duration_ms}
- [ ] Log each constraint check (for audit)
- [ ] Track metric: `generate_content_duration_ms` (should be < 25000 for P95)
- [ ] Track metric: `generate_content_safety_score` (monitor for unsafe content)
- [ ] Track metric: `generate_content_constraint_violations` (monitor regeneration rate)

---

## Example Implementation Pattern

```python
from typing import TypedDict
import re

class GenerateContentInput(TypedDict):
    trend: dict
    persona: dict
    platform: str
    content_type: str

class GenerateContentOutput(TypedDict):
    content_id: str
    script: str
    confidence_score: float
    safety_score: float
    engagement_prediction: float
    metadata: dict
    persona_alignment: dict

def generate_content(
    trend: dict,
    persona: dict,
    platform: str,
    content_type: str = "post"
) -> GenerateContentOutput:
    """
    Generate content based on trend and persona.
    
    Implements: skill_generate_content from 4-skills-api.md
    FR: FR-2 (Content Generation)
    Timeout: 45s | P95 Target: 25s
    
    Args:
        trend: TrendData object
        persona: Agent Persona configuration
        platform: Target platform (twitter, tiktok, etc.)
        content_type: Type of content to generate
    
    Returns:
        ContentPackage with script and metadata
    """
    start_time = time.time()
    content_id = str(uuid4())
    
    # 1. Validate inputs
    validate_input(trend, persona, platform, content_type)
    
    # 2. Build LLM prompt
    voice_prompt = VOICE_PROMPTS[persona['voice_tone']]
    max_length = persona['content_guidelines']['max_length']
    forbidden_words = persona['vocabulary']['forbidden_words']
    
    prompt = f"""
    You are a {persona['voice_tone']} content creator.
    Target audience: {persona['target_audience']}
    Expertise: {', '.join(persona['expertise_areas'])}
    
    {voice_prompt}
    
    Generate a {content_type} about: {trend['content']}
    Platform: {platform}
    Max length: {max_length} chars
    Include CTA: {persona['content_guidelines'].get('call_to_action', 'none')}
    
    NEVER use these words: {', '.join(forbidden_words)}
    
    Return ONLY the {content_type}, no explanations.
    """
    
    # 3. Generate with retries
    for attempt in range(3):
        try:
            with timeout(40):
                script = gemini_client.generate(
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=1000
                )
            break
        except TimeoutError:
            if attempt < 2:
                logger.warning(f"generate_content_retry {attempt+1}/3")
                continue
            else:
                raise SpecError(code="GENERATION_TIMEOUT", http_status=504)
    
    # 4. Validate constraints
    violations = []
    
    # Check forbidden words
    for word in forbidden_words:
        if re.search(rf'\b{re.escape(word)}\b', script, re.IGNORECASE):
            violations.append(f"Forbidden word: {word}")
    
    # Check length
    if len(script) > max_length:
        violations.append(f"Too long: {len(script)} > {max_length}")
    
    # Check CTA
    if persona['content_guidelines'].get('call_to_action'):
        cta_keywords = ['follow', 'like', 'share', 'comment', 'subscribe', 'click']
        if not any(kw in script.lower() for kw in cta_keywords):
            violations.append("Missing call-to-action")
    
    if violations:
        if attempt < 2:
            # Regenerate with stricter constraints
            prompt += f"\nFix these issues: {'; '.join(violations)}"
            attempt += 1
            continue
        else:
            raise SpecError(
                code="VAL_SCHEMA_INVALID",
                message='; '.join(violations),
                http_status=422
            )
    
    # 5. Safety check
    safety_score = moderation_api.check(script)
    if safety_score < 0.8:
        raise SpecError(code="GENERATION_UNSAFE", http_status=400)
    
    # 6. Score content
    confidence_score = 0.85  # From LLM response metadata
    engagement_prediction = predict_engagement(script, persona, platform)
    
    metadata = {
        'word_count': len(script.split()),
        'has_hashtags': '#' in script,
        'has_call_to_action': any(k in script.lower() for k in ['follow', 'like', 'share']),
        'tone_detected': persona['voice_tone'],
        'length_compliant': len(script) <= max_length
    }
    
    persona_alignment = {
        'voice_tone_match': 0.92,
        'vocabulary_compliance': 1.0 if not violations else 0.0,
        'guideline_compliance': 0.98
    }
    
    result = GenerateContentOutput(
        content_id=content_id,
        script=script,
        confidence_score=confidence_score,
        safety_score=safety_score,
        engagement_prediction=engagement_prediction,
        metadata=metadata,
        persona_alignment=persona_alignment,
        generated_at=datetime.utcnow().isoformat()
    )
    
    # 7. Log success
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        'generate_content_success',
        content_id=content_id,
        platform=platform,
        confidence=confidence_score,
        safety=safety_score,
        duration_ms=duration_ms
    )
    metrics.record('generate_content_duration_ms', duration_ms)
    
    return result
```

---

## Testing Requirements

**Unit Tests**:
- [ ] Test all 4 voice_tone enums (humorous, formal, inspirational, casual)
- [ ] Test forbidden word detection (exact match, case-insensitive)
- [ ] Test length validation (under, at, over max_length)
- [ ] Test CTA presence (with/without requirement)
- [ ] Test safety check (safe vs unsafe content)
- [ ] Test all content_types (video_script, caption, post, hashtag_set)
- [ ] Test persona_alignment scoring

**Integration Tests**:
- [ ] Mock Gemini API and verify prompt structure
- [ ] Verify regeneration on constraint violations (max 3 retries)
- [ ] Verify confidence/safety scores reasonable
- [ ] Verify engagement prediction correlates with engagement_score

**Performance Tests**:
- [ ] P95 latency < 25s (spec: 45s timeout)
- [ ] Single generation < 20s on average
- [ ] Batch generation (5 trends) < 100s total

---

## Debugging & Escalation

**If forbidden words appearing in output**:
- Verify forbidden_words list is being parsed correctly
- Check case-insensitive regex working
- Consider synonyms (e.g., "stupid" vs "dumb")

**If safety_score too low**:
- May need stricter safety thresholds
- Consider adding explicit safety instructions to prompt

**If engagement_prediction consistently wrong**:
- Tune prediction model with historical engagement data
- Consider content length, hashtag count, CTA presence

**If P95 > 25s**:
- Profile LLM call vs constraint validation
- Consider caching generated content for similar trends

---

## References

- **API Spec**: [specs/4-skills-api.md#3-generate_content](../specs/4-skills-api.md)
- **Persona Schema**: [specs/2-design.md#agent-persona-schema](../specs/2-design.md)
- **Functional Req**: [specs/1-functional.md#fr-2](../specs/1-functional.md)
- **Error Codes**: [specs/7-error-codes.md](../specs/7-error-codes.md)
- **Verification**: [specs/3-verification.md#fr-2-content-generation](../specs/3-verification.md)
