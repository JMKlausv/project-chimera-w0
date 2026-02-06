# Skill: validate_content

## Overview
Validate generated content against safety, compliance, and quality standards. This is the final safety gate before human review.

**Agent**: Judge Agent  
**FR**: Part of FR-3 (Human Approval Gate)  
**Timeout**: 5s | **P95 Target**: 2s

---

## Input Schema

```json
{
  "content_id": "uuid4",
  "content_type": "video_script|caption|post|hashtag_set",
  "script": "string",
  "platform": "twitter|tiktok|instagram|reddit",
  "confidence_score": 0.87,
  "safety_score": 0.95,
  "metadata": {
    "word_count": 45,
    "has_call_to_action": true
  }
}
```

**Validation Rules**:
- ✅ `content_id` must be valid UUID4
- ✅ `content_type` must be enum
- ✅ `script` must be non-empty string
- ✅ `platform` must match content platform
- ✅ `confidence_score` must be 0.0-1.0

---

## Output Schema

```json
{
  "content_id": "uuid4",
  "is_valid": true,
  "validation_score": 0.94,
  "issues": [],
  "warnings": [],
  "validation_result": {
    "safety_check": "PASS",
    "compliance_check": "PASS",
    "quality_check": "PASS",
    "length_check": "PASS"
  },
  "recommendation": "APPROVE|REVIEW|REJECT",
  "validated_at": "2026-02-06T10:35:00Z"
}
```

**Output Requirements**:
- `is_valid`: Boolean (all critical checks pass)
- `issues`: Array of blocking problems (prevent approval)
- `warnings`: Array of non-blocking concerns
- `recommendation`: 
  - `APPROVE` if `is_valid=true` and no concerns
  - `REVIEW` if `is_valid=true` but has warnings
  - `REJECT` if `is_valid=false`

---

## Validation Checks

### 1. Safety Check (Critical)

**Criteria**:
- No hate speech, slurs, or discriminatory language
- No violence or gore
- No misinformation or false claims
- No personally identifiable information (PII)
- `safety_score ≥ 0.8` from generation

**Failure**: Issue raised → `recommendation=REJECT`

**Detection**:
```python
safety_issues = []

# Check moderation API score
if safety_score < 0.8:
    safety_issues.append("Safety score too low")

# Check for PII patterns
pii_patterns = [
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
    r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',  # Email
]
for pattern in pii_patterns:
    if re.search(pattern, script, re.IGNORECASE):
        safety_issues.append("PII detected")
        break
```

### 2. Compliance Check (Critical)

**Criteria**:
- Platform-specific content policies respected
- No prohibited content for platform
- Length/format constraints met
- Mandatory disclosures present (if applicable)

**Platform Rules**:

| Platform | Rule | Violation |
|----------|------|-----------|
| twitter | Max 280 chars | Length check |
| tiktok | No external links | Link detection |
| instagram | No contact info in caption | PII check |
| reddit | No excessive self-promotion | Link/hashtag count |

**Failure**: Issue raised → `recommendation=REJECT`

### 3. Quality Check (Non-Critical)

**Criteria**:
- Minimum length (5+ chars for any content)
- No excessive repetition (same word >3x)
- No spam-like patterns (excessive hashtags/emojis)
- Spelling/grammar acceptable

**Non-Blocking Issues** → warnings, not issues

### 4. Length Check (Critical)

**Criteria**:
- Matches platform limits
- Readable/watchable length

**Failure**: Issue raised → `recommendation=REJECT`

---

## Validation Algorithm

```python
def validate_content(content: dict) -> dict:
    """
    Validate content against safety, compliance, quality.
    
    Flow:
    1. Safety check → CRITICAL (any failure = reject)
    2. Compliance check → CRITICAL (any failure = reject)
    3. Quality check → WARNING (non-blocking)
    4. Length check → CRITICAL (failure = reject)
    5. Aggregate scores
    """
    issues = []
    warnings = []
    
    # 1. Safety check
    safety_ok, safety_issues = check_safety(content)
    if not safety_ok:
        issues.extend(safety_issues)
    
    # 2. Compliance check
    compliance_ok, compliance_issues = check_compliance(content)
    if not compliance_ok:
        issues.extend(compliance_issues)
    
    # 3. Quality check
    quality_ok, quality_warnings = check_quality(content)
    if not quality_ok:
        warnings.extend(quality_warnings)
    
    # 4. Length check
    length_ok, length_issues = check_length(content)
    if not length_ok:
        issues.extend(length_issues)
    
    # Aggregate
    is_valid = len(issues) == 0
    
    recommendation = (
        "APPROVE" if (is_valid and len(warnings) == 0) else
        "REVIEW" if (is_valid and len(warnings) > 0) else
        "REJECT"
    )
    
    validation_score = (
        1.0 - (len(issues) * 0.1 + len(warnings) * 0.02)
    )
    
    return {
        'content_id': content['content_id'],
        'is_valid': is_valid,
        'issues': issues,
        'warnings': warnings,
        'recommendation': recommendation,
        'validation_score': max(0.0, validation_score),
        'validated_at': datetime.utcnow().isoformat()
    }
```

---

## Error Handling

| Error Code | HTTP | Cause | Recovery |
|-----------|------|-------|----------|
| `VALIDATION_ERROR` | 422 | Schema validation failed | Return `is_valid=false` |
| `INVALID_INPUT` | 400 | Content_id not UUID4 | Don't validate, return error |

No retries for validation (deterministic).

---

## Implementation Checklist

### 1. Input Validation
- [ ] Validate `content_id` is UUID4
- [ ] Validate `content_type` is enum
- [ ] Validate `script` is non-empty string (min 5 chars)
- [ ] Validate `platform` is enum
- [ ] Validate `safety_score` is 0.0-1.0

### 2. Safety Check
- [ ] Call moderation API on script
  - [ ] Raise issue if safety_score < 0.8
- [ ] Scan for PII (SSN, CC, email patterns)
  - [ ] Raise issue if PII found
- [ ] Check for hate speech/slurs
  - [ ] Use content filter or LLM quick check
  - [ ] Raise issue if detected
- [ ] Check for violence/gore keywords
  - [ ] Raise issue if found

### 3. Compliance Check
- [ ] Platform-specific rules (twitter=280 chars, etc.)
  - [ ] Raise issue if violated
- [ ] Check for prohibited links/content per platform
- [ ] Verify mandatory disclosures present (if applicable)

### 4. Quality Check
- [ ] Minimum length (5+ chars)
  - [ ] Warning if too short
- [ ] Excessive repetition (same word >3x)
  - [ ] Warning if found
- [ ] Spam patterns (>10 hashtags or >20 emojis)
  - [ ] Warning if found
- [ ] Spell/grammar check (basic)
  - [ ] Warning if many errors

### 5. Length Check
- [ ] Platform-specific max length
  - [ ] twitter: 280 chars
  - [ ] instagram: 2200 chars
  - [ ] tiktok: No limit (but reasonable < 1000)
- [ ] Raise issue if exceeded

### 6. Scoring
- [ ] `validation_score = 1.0 - (len(issues)*0.1 + len(warnings)*0.02)`
- [ ] Cap at 0.0 (min) and 1.0 (max)
- [ ] `is_valid = len(issues) == 0` (warnings don't block)

### 7. Recommendation Logic
- [ ] `APPROVE`: is_valid=true AND len(warnings)=0
- [ ] `REVIEW`: is_valid=true AND len(warnings)>0
- [ ] `REJECT`: is_valid=false (any issues)

### 8. Logging & Metrics
- [ ] Log at START: `validate_content_start` with {content_id, platform}
- [ ] Log at SUCCESS: `validate_content_success` with {is_valid, recommendation, duration_ms}
- [ ] Log each issue/warning (for audit)
- [ ] Track metric: `validate_content_duration_ms` (should be < 2000 for P95)
- [ ] Track metric: `validate_content_approval_rate` (monitor content quality)

---

## Example Implementation Pattern

```python
from typing import TypedDict
import re

class ValidateContentOutput(TypedDict):
    content_id: str
    is_valid: bool
    validation_score: float
    issues: list[str]
    warnings: list[str]
    recommendation: str

def validate_content(content: dict) -> ValidateContentOutput:
    """
    Validate content against safety and compliance.
    
    Implements: skill_validate_content from 4-skills-api.md
    FR: FR-3 (Human Approval Gate)
    Timeout: 5s | P95 Target: 2s
    """
    start_time = time.time()
    
    # 1. Validate input
    validate_input(content)
    
    issues = []
    warnings = []
    
    # 2. Safety check
    if content.get('safety_score', 0) < 0.8:
        issues.append("Safety score too low")
    
    # Check for PII
    pii_patterns = {
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'email': r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
    }
    for pii_type, pattern in pii_patterns.items():
        if re.search(pattern, content['script'], re.IGNORECASE):
            issues.append(f"PII detected: {pii_type}")
            break
    
    # 3. Compliance check
    platform = content['platform']
    script = content['script']
    
    # Platform-specific length checks
    platform_limits = {
        'twitter': 280,
        'instagram': 2200,
        'tiktok': 1000,
        'reddit': 40000
    }
    
    max_length = platform_limits.get(platform, 1000)
    if len(script) > max_length:
        issues.append(f"{platform} length limit: {len(script)} > {max_length}")
    
    # 4. Quality check
    if len(script) < 5:
        warnings.append("Content too short (< 5 chars)")
    
    # Check for excessive repetition
    words = script.split()
    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    if any(count > 3 for count in word_counts.values()):
        warnings.append("Excessive repetition detected")
    
    # Check for spam patterns
    hashtag_count = script.count('#')
    emoji_count = len([c for c in script if ord(c) > 127])
    
    if hashtag_count > 10:
        warnings.append(f"Too many hashtags: {hashtag_count}")
    if emoji_count > 20:
        warnings.append(f"Too many emojis: {emoji_count}")
    
    # 5. Aggregate results
    is_valid = len(issues) == 0
    validation_score = max(0.0, 1.0 - (len(issues)*0.1 + len(warnings)*0.02))
    
    recommendation = (
        "APPROVE" if (is_valid and len(warnings) == 0) else
        "REVIEW" if (is_valid and len(warnings) > 0) else
        "REJECT"
    )
    
    result = ValidateContentOutput(
        content_id=content['content_id'],
        is_valid=is_valid,
        validation_score=validation_score,
        issues=issues,
        warnings=warnings,
        recommendation=recommendation,
        validated_at=datetime.utcnow().isoformat()
    )
    
    # 6. Log
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        'validate_content_success',
        content_id=content['content_id'],
        is_valid=is_valid,
        recommendation=recommendation,
        duration_ms=duration_ms
    )
    metrics.record('validate_content_duration_ms', duration_ms)
    
    return result
```

---

## Testing Requirements

**Unit Tests**:
- [ ] Valid content → `APPROVE` recommendation
- [ ] Content with warnings → `REVIEW` recommendation
- [ ] Content with issues → `REJECT` recommendation
- [ ] PII detection (SSN, CC, email)
- [ ] Length validation (twitter=280, instagram=2200)
- [ ] Hashtag/emoji spam detection
- [ ] Repetition detection
- [ ] Safety score < 0.8 → issue

**Integration Tests**:
- [ ] Validation score correlates with human judgment
- [ ] All issue types caught before human review
- [ ] No false positives (legitimate content rejected)

**Performance Tests**:
- [ ] P95 latency < 2s (spec: 5s timeout)
- [ ] Can validate 100 content items in < 200ms

---

## Debugging & Escalation

**If too many REJECT recommendations**:
- Content generation may be poor; check generate_content outputs
- Safety thresholds may be too strict; review policy

**If false positives** (valid content rejected):
- Review safety_score thresholds
- Check PII regex patterns (may be too broad)

**If spam detection not working**:
- Hashtag count threshold may be too high
- Add more sophisticated spam patterns

---

## References

- **API Spec**: [specs/4-skills-api.md#4-validate_content](../specs/4-skills-api.md)
- **Functional Req**: [specs/1-functional.md#fr-3](../specs/1-functional.md)
- **Error Codes**: [specs/7-error-codes.md](../specs/7-error-codes.md)
- **Verification**: [specs/3-verification.md#fr-3-hitl](../specs/3-verification.md)
