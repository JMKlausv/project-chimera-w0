# Verification Specification

This document defines how we verify that the system meets the functional requirements defined in [1-functional.md](1-functional.md). Each **FR (Functional Requirement)** from that specification maps to acceptance criteria and test cases implemented in `tests/`.

**Reference:** See [1-functional.md](1-functional.md) for the complete list of user stories and functional requirements.

## Verification Strategy

### Three-Layer Testing

1. **Unit Tests** (`tests/unit/`)
   - Test individual agent skills in isolation
   - Verify data transformations (trend → content → post)
   - Mock external MCP servers

2. **Integration Tests** (`tests/integration/`)
   - Test agent-to-agent communication
   - Verify full pipelines (trend discovery → content creation → approval → distribution)
   - Test with real MCP server contracts

3. **System Tests** (`tests/system/`)
   - End-to-end agent workflows
   - Human-in-the-Loop verification
   - OpenClaw network interactions

---

## Mapping: Functional Requirements to Verification

Each FR from [1-functional.md](1-functional.md) maps to verification criteria below:

| Functional Requirement | Definition | Verification Section | Test Layers | Owner |
|---|---|---|---|---|
| [FR-1: Trend Discovery](1-functional.md#fr-1-trend-discovery) | Fetch from ≥2 platforms, >10k engagement, JSON schema | [FR-1](#fr-1-trend-discovery) | Unit + Integration + System | Engineering |
| [FR-2: Content Generation](1-functional.md#fr-2-content-generation) | Match persona, safety checks, packaging | [FR-2](#fr-2-content-generation) | Unit + Integration | Engineering |
| [FR-3: Human Approval Gate](1-functional.md#fr-3-human-approval-gate) | HITL layer, approval token, review interface | [FR-3](#fr-3-human-approval-gate) | Unit + Integration | Engineering + HITL |
| [FR-4: OpenClaw Integration](1-functional.md#fr-4-openclaw-integration) | Status publishing, capability queries, ARP protocol | [FR-4](#fr-4-openclaw-integration) | Integration + System | Engineering |
| **Orchestrator Coordination** | Coordinate workers, validate specs, escalate on low confidence | [Orchestrator Coordination](#orchestrator-coordination) | Unit + Integration + System | Engineering |
| **Cross-cutting:** Security | Zero Trust, logging, sandboxing | [Security Verification](#security-verification) | Unit + Integration + System | Security |
| **Cross-cutting:** Resilience | Idempotency, edge cases, partial failure recovery | [Resilience & Idempotency](#resilience--idempotency) | Integration + System | Engineering |
| **Cross-cutting:** Performance | Latency, throughput, concurrency | [Performance Benchmarks](#performance-benchmarks) | System | Performance |

---

## Orchestrator Coordination

**User Story (from [1-functional.md](1-functional.md#as-an-orchestrator-agent)):**
- Coordinate multiple worker agents to complete influencer tasks
- Check all worker outputs against the specs before proceeding
- Escalate to human review when confidence is below threshold

### Acceptance Criteria

| Criterion | Definition | Test File |
|-----------|-----------|-----------|
| **Worker lifecycle** | Orchestrator starts, monitors, and stops workers cleanly | `tests/integration/orchestrator/test_worker_lifecycle.py` |
| **Output validation** | All worker outputs validated against [2-design.md](2-design.md) schemas before proceeding | `tests/unit/orchestrator/test_output_validation.py` |
| **Confidence thresholding** | Content with confidence <0.8 automatically escalates to HITL without agent publishing | `tests/unit/orchestrator/test_confidence_thresholding.py` |
| **Orchestration pipeline** | Trend → Content → Approval → Distribution workflow completes in order | `tests/integration/orchestrator/test_pipeline_order.py` |
| **Conflict resolution** | Multiple workers producing different outputs handled gracefully | `tests/integration/orchestrator/test_conflict_resolution.py` |
| **Worker failure isolation** | One worker failure doesn't cascade to others | `tests/integration/orchestrator/test_failure_isolation.py` |

### Test Implementation Roadmap

```python
# tests/unit/orchestrator/test_output_validation.py
def test_trend_output_validated_against_schema():
    """Verify Trend Analyst output matches schema before proceeding"""
    
def test_content_output_validated_against_schema():
    """Verify Content Creator output matches schema before proceeding"""
    
def test_invalid_output_rejected():
    """Verify orchestrator rejects malformed outputs"""

# tests/unit/orchestrator/test_confidence_thresholding.py
def test_low_confidence_escalates_to_hitl():
    """Verify content with confidence <0.8 escalates automatically"""
    
def test_high_confidence_bypasses_escalation():
    """Verify content with confidence ≥0.8 proceeds without escalation"""

# tests/integration/orchestrator/test_pipeline_order.py
def test_trend_discovery_before_content_generation():
    """Verify trends fetched before content generation starts"""
    
def test_approval_before_distribution():
    """Verify approval token received before distribution starts"""

# tests/integration/orchestrator/test_failure_isolation.py
def test_trend_analyst_failure_doesnt_block_other_workers():
    """Verify one worker failure isolated from others"""
    
def test_worker_timeout_handling():
    """Verify orchestrator handles slow/hung workers with timeout"""
```

---

## FR-1: Trend Discovery

**Functional Requirement (from [1-functional.md](1-functional.md#fr-1-trend-discovery)):**
- Agent MUST fetch data from minimum 2 social platforms
- Agent MUST identify trending topics with >10k engagement
- Output format: JSON with standardized schema

### Acceptance Criteria

| Criterion | Definition | Test File |
|-----------|-----------|-----------|
| **Multi-platform fetch** | Trend Analyst retrieves data from ≥2 platforms within 30s timeout | `tests/unit/agents/test_trend_analyst.py` |
| **Engagement threshold** | Returned trends have `engagement_score ≥ 10000` | `tests/unit/agents/test_trend_analyst.py` |
| **Schema compliance** | Output matches Trend Data Schema (trend_id, topic, platform, engagement_score, sentiment, timestamp, metadata) | `tests/unit/schemas/test_trend_schema.py` |
| **Error handling** | If platform unavailable, fetch from fallback platform without crashing | `tests/integration/agents/test_trend_resilience.py` |
| **Performance** | Fetch completes in <30s for 100+ trends | `tests/system/performance/test_trend_throughput.py` |

### Edge Cases & Error Scenarios

| Edge Case | Definition | Test File |
|-----------|-----------|-----------|
| **No high-engagement trends** | Platform returns trends but none exceed >10k threshold; agent returns empty list gracefully | `tests/integration/agents/test_trend_no_results.py` |
| **Duplicate trends** | Same trend appears on multiple platforms; agent deduplicates before returning | `tests/unit/agents/test_trend_deduplication.py` |
| **Data freshness** | Trends older than 24h are excluded; verifies recency filter | `tests/unit/agents/test_trend_freshness.py` |
| **Rate limiting** | Platform enforces rate limits; agent implements exponential backoff retry | `tests/integration/agents/test_rate_limiting.py` |
| **Partial platform failure** | One platform times out; agent fetches from others without blocking | `tests/integration/agents/test_partial_failure.py` |
| **Invalid platform response** | Platform returns malformed/unexpected JSON; agent validates and rejects gracefully | `tests/unit/agents/test_invalid_response_handling.py` |
| **All platforms unavailable** | No platforms accessible; agent escalates error to orchestrator | `tests/integration/agents/test_all_platforms_down.py` |

### Test Implementation Roadmap

```python
# tests/unit/agents/test_trend_analyst.py
def test_fetch_multiple_platforms():
    """Verify TrendAnalyst fetches from ≥2 platforms"""
    
def test_engagement_threshold():
    """Verify only trends with engagement ≥10k are returned"""
    
def test_trend_data_schema():
    """Verify output matches Trend Data Schema"""

# tests/unit/agents/test_trend_deduplication.py
def test_duplicate_trends_deduplicated():
    """Verify same trend from multiple platforms appears once"""

# tests/unit/agents/test_trend_freshness.py
def test_stale_trends_filtered():
    """Verify trends >24h old are excluded"""

# tests/integration/agents/test_trend_resilience.py
def test_fallback_on_platform_error():
    """Verify agent fetches from fallback if primary platform fails"""

# tests/integration/agents/test_rate_limiting.py
def test_rate_limit_backoff():
    """Verify exponential backoff on platform rate limiting"""

# tests/system/performance/test_trend_throughput.py
def test_trend_fetch_performance():
    """Verify <30s latency for large trend batches"""
```

---

## FR-2: Content Generation

**Functional Requirement (from [1-functional.md](1-functional.md#fr-2-content-generation)):**
- Agent MUST generate content matching persona voice
- Agent MUST include safety checks (no offensive content)
- Output MUST be packaged for human review

### Acceptance Criteria

| Criterion | Definition | Test File |
|-----------|-----------|-----------|
| **Persona matching** | Generated script reflects agent persona guidelines (tone, vocabulary, style) | `tests/unit/agents/test_content_creator.py` |
| **Safety filtering** | Content MUST NOT contain: (1) offensive language, (2) hate speech, (3) misinformation | `tests/unit/safety/test_content_safety.py` |
| **Package format** | Output matches Content Package Schema (content_id, script, media_urls, captions, hashtags, confidence_score, requires_review) | `tests/unit/schemas/test_content_schema.py` |
| **Confidence scoring** | confidence_score correlates with review requirement (score <0.8 → requires_review=true) | `tests/unit/agents/test_content_confidence.py` |
| **Determinism** | Same input trend + persona produces consistent output structure (not exact text) | `tests/unit/agents/test_content_determinism.py` |

### Edge Cases & Error Scenarios

| Edge Case | Definition | Test File |
|-----------|-----------|-----------|
| **Invalid/missing persona** | Persona guidelines absent or malformed; agent uses default persona gracefully | `tests/unit/agents/test_missing_persona.py` |
| **Generation timeout** | Content generation exceeds time limit; agent returns partial content with low confidence | `tests/unit/agents/test_generation_timeout.py` |
| **Concurrent generation** | Multiple content generation requests for same trend; no race conditions, consistent outputs | `tests/integration/agents/test_concurrent_generation.py` |
| **Media URL validation** | Generated media URLs are tested for accessibility; unreachable URLs flagged | `tests/unit/agents/test_media_url_validation.py` |
| **Content length constraints** | Scripts, captions exceed platform limits; agent truncates with warning | `tests/unit/agents/test_content_length_validation.py` |
| **Multilingual/special characters** | Non-ASCII content (emoji, accents) handled correctly in all fields | `tests/unit/agents/test_unicode_handling.py` |
| **Plagiarism detection** | Generated content compared against trend sources; high similarity flags content | `tests/integration/agents/test_plagiarism_detection.py` |

### Test Implementation Roadmap

```python
# tests/unit/agents/test_content_creator.py
def test_persona_tone_matching():
    """Verify generated script matches persona tone/vocabulary"""
    
def test_content_package_structure():
    """Verify output matches Content Package Schema"""

# tests/unit/safety/test_content_safety.py
def test_offensive_language_filter():
    """Verify offensive content is rejected/sanitized"""
    
def test_hate_speech_detection():
    """Verify hate speech content is rejected"""
    
def test_misinformation_filter():
    """Verify false claims are flagged"""

# tests/unit/agents/test_content_confidence.py
def test_low_confidence_triggers_review():
    """Verify content with score <0.8 sets requires_review=true"""

# tests/unit/agents/test_missing_persona.py
def test_default_persona_fallback():
    """Verify agent uses default persona if input is missing/invalid"""

# tests/integration/agents/test_concurrent_generation.py
def test_concurrent_requests_no_race_condition():
    """Verify concurrent generation requests don't interfere"""
```

---

## FR-3: Human Approval Gate

**Functional Requirement (from [1-functional.md](1-functional.md#fr-3-human-approval-gate)):**
- All content MUST pass through HITL layer before publication
- Agent MUST NOT publish without approval token
- Review interface MUST show content + justification

### Acceptance Criteria

| Criterion | Definition | Test File |
|-----------|-----------|-----------|
| **Review blocking** | Distribution agent MUST reject publish requests without valid approval_token | `tests/unit/agents/test_distribution_gate.py` |
| **Token validation** | approval_token is cryptographically signed and non-forgeable | `tests/unit/security/test_approval_tokens.py` |
| **Review SLA** | Human reviewer must approve/reject within 2 minutes; after SLA timeout, escalate | `tests/integration/hitl/test_review_sla.py` |
| **Audit trail** | Every approval action logged with: reviewer_id, timestamp, content_id, decision | `tests/integration/logging/test_approval_audit_trail.py` |
| **Feedback loop** | Rejection feedback is stored and used to improve agent confidence scores | `tests/integration/learning/test_feedback_improvement.py` |

### Edge Cases & Error Scenarios

| Edge Case | Definition | Test File |
|-----------|-----------|-----------|
| **Token expiration** | Approval token expires after TTL; agent cannot publish with expired token | `tests/unit/security/test_token_expiration.py` |
| **Parallel reviews** | Same content submitted to multiple reviewers; only first approval counts | `tests/integration/hitl/test_parallel_review_idempotency.py` |
| **Reviewer offline** | Reviewer unavailable during SLA window; escalate to backup reviewer | `tests/integration/hitl/test_reviewer_offline_fallback.py` |
| **Review timeout** | No reviewer decision after 2 minutes; content automatically escalated/queued | `tests/integration/hitl/test_review_timeout_escalation.py` |
| **Re-rejection handling** | Content rejected multiple times; agent confidence decreases with each rejection | `tests/integration/learning/test_rejection_learning.py` |
| **Reviewer conflict** | Two reviewers approve/reject same content; conflict resolution rules applied | `tests/integration/hitl/test_reviewer_conflict_resolution.py` |
| **Audit tampering** | Audit trail cannot be modified after logged; verified via checksums | `tests/security/test_audit_immutability.py` |

### Test Implementation Roadmap

```python
# tests/unit/agents/test_distribution_gate.py
def test_publish_requires_approval_token():
    """Verify distribution agent rejects publish without valid token"""
    
def test_invalid_token_rejected():
    """Verify forged/expired tokens are rejected"""

# tests/unit/security/test_approval_tokens.py
def test_token_signature_verification():
    """Verify tokens are cryptographically signed"""

# tests/unit/security/test_token_expiration.py
def test_expired_token_rejected():
    """Verify tokens expire after TTL"""

# tests/integration/hitl/test_review_sla.py
def test_review_completes_within_sla():
    """Verify review completed within 2 minutes"""
    
def test_sla_timeout_escalation():
    """Verify escalation triggers after 2 min timeout"""

# tests/integration/hitl/test_parallel_review_idempotency.py
def test_multiple_approvals_idempotent():
    """Verify only first approval counts in parallel reviews"""

# tests/integration/logging/test_approval_audit_trail.py
def test_approval_audit_logged():
    """Verify all approval actions are logged"""
```

---

## FR-4: OpenClaw Integration

**Functional Requirement (from [1-functional.md](1-functional.md#fr-4-openclaw-integration)):**
- Agent MUST publish availability status to OpenClaw network
- Agent MUST respond to capability queries from other agents
- Protocol: Agent Relay Protocol (ARP)

### Acceptance Criteria

| Criterion | Definition | Test File |
|-----------|-----------|-----------|
| **Profile registration** | Agent profile exists in OpenClaw directory with: agent_id, type, capabilities, availability, pricing, reputation_score | `tests/integration/openclaw/test_profile_registration.py` |
| **Heartbeat mechanism** | Agent fetches OpenClaw heartbeat every 4 hours ± 5 min, executes instructions, reports status | `tests/system/openclaw/test_heartbeat_mechanism.py` |
| **ARP capability queries** | Agent responds to ARP queries with accurate capabilities within 5s | `tests/integration/openclaw/test_arp_queries.py` |
| **Commercial workflow** | RFP → quote → acceptance → execution → payment completes end-to-end without human intervention | `tests/system/openclaw/test_commercial_workflow.py` |
| **Network isolation** | OpenClaw heartbeat instructions cannot access privileged agent functions or shell | `tests/security/test_openclaw_sandboxing.py` |

### Edge Cases & Error Scenarios

| Edge Case | Definition | Test File |
|-----------|-----------|-----------|
| **Agent offline detection** | Agent offline >24h; profile marked inactive in OpenClaw, cleaned up | `tests/integration/openclaw/test_offline_detection.py` |
| **OpenClaw downtime** | OpenClaw network unavailable; agent retries heartbeat with exponential backoff | `tests/integration/openclaw/test_network_downtime.py` |
| **Unsupported capability RFP** | RFP requests capability agent doesn't have; agent rejects with clear reason | `tests/integration/openclaw/test_unsupported_capability.py` |
| **Payment failure/retry** | Payment transaction fails; agent retries with escalation to human if necessary | `tests/integration/openclaw/test_payment_retry.py` |
| **Identity impersonation** | Malicious agent tries to register with same agent_id; OpenClaw verifies signature | `tests/security/test_identity_verification.py` |
| **Reputation score tampering** | Reputation score cannot be manually set; only updates via verified completion | `tests/security/test_reputation_immutability.py` |
| **ARP query abuse** | Excessive ARP queries from single source; agent implements rate limiting | `tests/security/test_arp_rate_limiting.py` |
| **API compatibility** | OpenClaw API version change; agent has fallback/upgrade mechanism | `tests/integration/openclaw/test_api_compatibility.py` |

### Test Implementation Roadmap

```python
# tests/integration/openclaw/test_profile_registration.py
def test_agent_profile_registration():
    """Verify agent profile is registered in OpenClaw"""
    
def test_profile_schema_compliance():
    """Verify profile includes all required fields"""

# tests/system/openclaw/test_heartbeat_mechanism.py
def test_heartbeat_frequency():
    """Verify heartbeat fetched every 4 hours ± 5 min"""
    
def test_heartbeat_instruction_execution():
    """Verify instructions from heartbeat are executed"""

# tests/integration/openclaw/test_arp_queries.py
def test_arp_query_response_time():
    """Verify capability queries answered within 5s"""

# tests/system/openclaw/test_commercial_workflow.py
def test_end_to_end_rfp_workflow():
    """Verify RFP → quote → acceptance → execution → payment flow"""

# tests/integration/openclaw/test_offline_detection.py
def test_agent_marked_inactive_after_24h_offline():
    """Verify agent profile updated when offline >24h"""

# tests/security/test_openclaw_sandboxing.py
def test_heartbeat_cannot_access_privileged_functions():
    """Verify heartbeat instructions are sandboxed"""
```

---

## Resilience & Idempotency

### Idempotency Testing

All operations MUST be safe to retry without side effects:

```python
# tests/resilience/idempotency/
def test_trend_fetch_idempotent():
    """Fetching same trends twice produces identical results"""
    
def test_content_generation_idempotent():
    """Regenerating content from same trend produces consistent structure"""
    
def test_approval_idempotent():
    """Approving already-approved content doesn't double-publish"""
    
def test_publication_idempotent():
    """Publishing already-published content doesn't create duplicates"""
    
def test_payment_idempotent():
    """Processing same payment twice doesn't duplicate charge"""
```

### Partial Failure Recovery

System handles multi-step failures gracefully:

```python
# tests/resilience/partial_failure/
def test_trend_fetch_succeeds_partial_platform_failure():
    """Trend fetch succeeds even if one platform fails"""
    
def test_approval_succeeds_after_distribution_rejection():
    """Can re-approve content that failed initial distribution"""
    
def test_publication_retry_after_network_failure():
    """Publication can be retried after transient network error"""
    
def test_workflow_resumption_after_worker_crash():
    """Workflow resumes from checkpoint after worker dies unexpectedly"""
    
def test_database_rollback_on_partial_write():
    """If write fails halfway, entire transaction rolled back"""
```

### Data Consistency Under Concurrency

```python
# tests/resilience/concurrency/
def test_concurrent_approval_decisions():
    """Multiple approvers don't create race conditions"""
    
def test_concurrent_trend_fetches():
    """Fetching trends concurrently doesn't lose data"""
    
def test_concurrent_wallet_transactions():
    """Parallel payment transactions maintain consistent balance"""
```

### Network Partition Handling

```python
# tests/resilience/network/
def test_database_offline_graceful_degradation():
    """Agent handles DB offline by queuing operations locally"""
    
def test_mcp_server_unavailable_fallback():
    """Missing MCP server triggers fallback or explicit error"""
    
def test_network_partition_detection():
    """Agent detects network partition and pauses external operations"""
```

---

## Cross-Cutting Concerns

### Security Verification

All tests MUST verify the Zero Trust model:

```python
# tests/security/
def test_no_direct_shell_access():
    """Verify agents cannot execute arbitrary shell commands"""
    
def test_external_content_sanitization():
    """Verify all external data is sanitized before use"""
    
def test_action_logging_via_mcp_sense():
    """Verify every agent action is logged for audit"""
    
def test_cryptographic_signing():
    """Verify published content is cryptographically signed"""
    
def test_agent_isolation():
    """Verify one agent's actions don't affect others"""
    
def test_human_review_cannot_bypass():
    """Verify agents cannot override human review decisions"""
```

### Performance Benchmarks

```python
# tests/system/performance/
def test_trend_to_content_latency():
    """P95 latency: trend → content generation ≤ 10s"""
    
def test_approval_to_publication_latency():
    """P95 latency: approval → published ≤ 5s"""
    
def test_concurrent_agents():
    """System handles ≥4 concurrent agents without degradation"""
    
def test_heartbeat_processing_latency():
    """P95 latency: heartbeat fetch → instruction execute ≤ 30s"""
    
def test_vector_db_query_performance():
    """Vector similarity search completes in <500ms for 1M trends"""
```

### Data Integrity

```python
# tests/data/
def test_schema_validation():
    """All data written to MongoDB validates against schema"""
    
def test_vector_db_consistency():
    """Weaviate vector embeddings match source trends"""
    
def test_foreign_key_integrity():
    """All content_id references point to valid content documents"""
    
def test_audit_trail_consistency():
    """Audit logs contain complete chronological record without gaps"""
    
def test_backup_restore_correctness():
    """Data restored from backup matches original state"""
```

---

## Definition of Done

A functional requirement is "done" when:
1. ✅ All unit tests pass (code-level verification)
2. ✅ All integration tests pass (contract-level verification)
3. ✅ All system tests pass (end-to-end verification)
4. ✅ Security tests pass (Zero Trust validation)
5. ✅ Edge case tests pass (error scenarios covered)
6. ✅ Resilience tests pass (idempotency, partial failure, concurrency)
7. ✅ Performance benchmarks met (latency/throughput)
8. ✅ Coverage ≥80% for unit, ≥60% for integration
9. ✅ Code review approved
10. ✅ Spec changes documented (if any)

---

## Test Execution & CI/CD

### Local Development
```bash
# Run all tests
pytest tests/ -v

# Run by layer
pytest tests/unit/ -v           # Fast (~10s)
pytest tests/integration/ -v    # Medium (~60s)
pytest tests/system/ -v         # Slow (~300s)

# Run by requirement
pytest tests/ -k "FR_1" -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### GitHub Actions (CI/CD)
- Unit tests: Run on every commit (must pass)
- Integration tests: Run on PR (must pass)
- System tests: Run on merge to main (nightly + pre-release)

### Coverage Requirements
- Unit tests: ≥80% code coverage
- Integration tests: ≥60% coverage
- All critical paths covered by system tests
