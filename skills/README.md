# Chimera Skills Documentation Index

Complete skill specifications for all Chimera agent capabilities. Each skill has detailed implementation instructions aligned with specs.

---

## Core Content Pipeline Skills

### Phase 1: Trend Discovery

**[fetch_trends.md](fetch_trends.md)** - Trend Analyst Agent
- Fetch trending topics from social platforms via MCP resources
- Input: `{platform, limit, timeWindow, minEngagement}`
- Output: `{trends: TrendData[], count, truncated}`
- Timeout: 30s | P95: 8s
- MCP Resources: twitter://mentions/recent, news://global/trends, market://crypto, reddit, tiktok
- Rate Limits: 100/hr (Twitter), 50/hr (News), 200/hr (Market)
- Error Codes: EXT_PLATFORM_UNAVAILABLE, EXT_RATE_LIMITED, VAL_SCHEMA_INVALID

**[semantic_filter.md](semantic_filter.md)** - Orchestrator / Trend Analyst
- Filter trends by relevance to campaign goals using Gemini 3 Flash
- Input: `{trends: TrendData[], campaign_goals}`
- Output: `{filtered_trends, accepted_count, rejected_count, filtering_confidence}`
- Timeout: 10s | P95: 3s
- LLM: Gemini 3 Flash (lightweight, batch scoring)
- Relevance Score: 0.0-1.0 (topic=30%, engagement=25%, audience=20%, sentiment=15%, recency=10%)
- Decision: accept if score ≥ threshold (default 0.75)

### Phase 2: Content Creation

**[generate_content.md](generate_content.md)** - Content Creator Agent
- Generate platform-specific content based on trends and personas
- Input: `{trend, persona, platform, content_type}`
- Output: `{script, confidence_score, safety_score, engagement_prediction, metadata}`
- Timeout: 45s | P95: 25s
- Content Types: video_script, caption, post, hashtag_set
- Voice Tones: humorous, formal, inspirational, casual
- Constraints: forbidden words, max_length, CTA required, safety checks
- LLM: Gemini 3 Flash with persona-based prompts
- Validation: No forbidden words, length compliant, CTA present, safety_score ≥ 0.8

### Phase 3: Quality Assurance

**[validate_content.md](validate_content.md)** - Judge Agent
- Validate generated content against safety, compliance, quality standards
- Input: `{content_id, script, platform, confidence_score, safety_score}`
- Output: `{is_valid, validation_score, issues, warnings, recommendation}`
- Timeout: 5s | P95: 2s
- Checks: Safety (PII, slurs, violence), Compliance (platform rules, length), Quality (spam, repetition)
- Recommendations: APPROVE (no issues/warnings), REVIEW (warnings only), REJECT (has issues)
- Critical: No forbidden words, no PII, platform length limits, no hate speech

### Phase 4: Distribution

**[publish_content.md](publish_content.md)** - Distribution Manager Agent
- Publish approved content to social platforms via MCP resources
- Input: `{content_id, script, platform, approval_token, metadata}`
- Output: `{post_id, post_url, published_at, metrics}`
- Timeout: 15s | P95: 10s
- Security: JWT approval token verification (RS256, 24h expiration, content_id match)
- Platforms: twitter (twitter://post), tiktok (tiktok://upload), instagram (instagram://post), reddit (reddit://submit)
- Rate Limits: Twitter 300/15min, TikTok 10/day, Instagram 200/24h, Reddit 9/10min
- Post-Publish: Fetch initial engagement metrics (likes, views, impressions, comments)

---

## Orchestration Skills

### Agent Lifecycle

**get_agent_profile.md** (TODO) - Orchestrator
- Retrieve agent configuration and current state
- Input: `{agent_id}`
- Output: `{AgentProfile}`
- Timeout: 2s | P95: 0.5s
- Caching: LRU cache, 5 min TTL

**update_agent_state.md** (TODO) - Orchestrator
- Update agent state with optimistic locking
- Input: `{agent_id, state_updates}`
- Output: `{AgentProfile}`
- Timeout: 5s | P95: 1s
- Concurrency: Optimistic locking with version field, retry max 3x with backoff

---

## Financial Skills

**fetch_wallet_balance.md** (TODO) - CFO Judge
- Get current wallet balance for transactions
- Input: `{wallet_address}`
- Output: `{balance, currency}`
- Timeout: 5s | P95: 1s

**debit_wallet.md** (TODO) - CFO Judge
- Execute financial transactions with SERIALIZABLE isolation
- Input: `{wallet_address, amount, tx_description}`
- Output: `{tx_id, success}`
- Timeout: 10s | P95: 3s
- Isolation: PostgreSQL SERIALIZABLE (prevent double-spend)
- Blockchain: Coinbase AgentKit for on-chain settlement

---

## Integration Skills

**register_openclaw_profile.md** (TODO) - Orchestrator
- Publish agent capabilities to OpenClaw network
- Input: `{agent_profile}`
- Output: `{registered: bool, profile_url}`
- Timeout: 10s | P95: 3s
- Protocol: Agent Relay Protocol (ARP)

**respond_to_arp_query.md** (TODO) - Any Agent
- Answer capability queries from other agents
- Input: `{query}`
- Output: `{capabilities, pricing, availability}`
- Timeout: 2s | P95: 0.5s
- Format: JSON response with agent capabilities

---

## Implementation Status

| Skill | Status | File | Location |
|-------|--------|------|----------|
| fetch_trends | ✅ Complete | fetch_trends.md | skills/ |
| semantic_filter | ✅ Complete | semantic_filter.md | skills/ |
| generate_content | ✅ Complete | generate_content.md | skills/ |
| validate_content | ✅ Complete | validate_content.md | skills/ |
| publish_content | ✅ Complete | publish_content.md | skills/ |
| get_agent_profile | ⏳ Planned | get_agent_profile.md | skills/ |
| update_agent_state | ⏳ Planned | update_agent_state.md | skills/ |
| fetch_wallet_balance | ⏳ Planned | fetch_wallet_balance.md | skills/ |
| debit_wallet | ⏳ Planned | debit_wallet.md | skills/ |
| register_openclaw_profile | ⏳ Planned | register_openclaw_profile.md | skills/ |
| respond_to_arp_query | ⏳ Planned | respond_to_arp_query.md | skills/ |

---

## Quick Reference: Skill Dependencies

```
Orchestrator
├─→ semantic_filter (filter trends)
├─→ get_agent_profile (load config)
├─→ update_agent_state (track progress)
└─→ register_openclaw_profile (publish availability)

Trend Analyst
└─→ fetch_trends (from MCP resources)

Content Creator
└─→ generate_content (LLM + persona)

Judge Agent
├─→ validate_content (safety checks)
├─→ fetch_wallet_balance
└─→ debit_wallet (if monetized)

Distribution Manager
└─→ publish_content (to platforms)
    └─→ [MCP platform endpoints]
```

---

## How to Use These Docs

### For Implementation
1. Read the **Overview** section
2. Study **Input/Output Schema** - exact types required
3. Review **Implementation Checklist** - step-by-step
4. Follow **Example Implementation Pattern** - code template
5. Run **Testing Requirements** - verify correctness

### For Architecture
1. Review **Skill Dependencies** graph above
2. Check **Timeout & P95 Targets** for capacity planning
3. Understand **Error Handling** per skill
4. Review **MCP Resources** for integration points
5. Check **Rate Limits** for bottlenecks

### For Debugging
1. Find skill in the index above
2. Go to detailed doc (e.g., fetch_trends.md)
3. Check **Error Handling** section
4. Review **Debugging & Escalation** section
5. Consult relevant spec files for constraints

---

## Cross-References to Specs

All skills implement requirements from:
- **specs/1-functional.md** - Functional requirements (FR-1 through FR-4)
- **specs/2-design.md** - Data schemas, SLAs, state machine, personas
- **specs/3-verification.md** - Test cases and acceptance criteria
- **specs/4-skills-api.md** - Complete skill interface definitions
- **specs/5-mcp-resources.md** - MCP endpoints, rate limits, fallback chains
- **specs/7-error-codes.md** - Error catalog and recovery strategies

---

## Performance Targets Summary

| Skill | P95 Target | Timeout | Retry Policy |
|-------|-----------|---------|--------------|
| fetch_trends | 8s | 30s | Exponential backoff (max 3x) |
| semantic_filter | 3s | 10s | Fallback to accept all |
| generate_content | 25s | 45s | Regenerate on constraint violation (max 3x) |
| validate_content | 2s | 5s | No retry (deterministic) |
| publish_content | 10s | 15s | Exponential backoff + queue (max 10 retries) |

**Overall**: Trend → Filter → Generate → Validate → Publish = ~48s P95 (within 60s SLA)

---

## Common Patterns Across Skills

1. **Input Validation** - All skills validate input schema first
2. **Error Handling** - Use spec error codes (7-error-codes.md)
3. **Logging** - Structured logs with context (agent_id, campaign_id)
4. **Metrics** - Track duration (ms), success rate, resource usage
5. **Retry Logic** - Exponential backoff with jitter (max 30s wait)
6. **Rate Limiting** - Check before external calls, queue if exceeded
7. **Caching** - Check before MCP/LLM calls (per resource TTL)

---

## Next Steps

1. ✅ Complete documentation for 5 core skills (fetch_trends, semantic_filter, generate_content, validate_content, publish_content)
2. 📋 Create docs for 5 orchestration/financial skills (get_agent_profile, update_agent_state, fetch_wallet_balance, debit_wallet, register_openclaw_profile)
3. 🔧 Implement core skills in Python (src/chimera/skills/)
4. 🧪 Write unit + integration tests per specs/3-verification.md
5. 📊 Add observability (metrics, logging, traces)
6. 🚀 Deploy and monitor P95 latencies vs targets

---

## Questions or Issues?

Refer to:
- **Schema questions** → Read 2-design.md Data Schemas section
- **API contract questions** → Read 4-skills-api.md
- **MCP integration questions** → Read 5-mcp-resources.md
- **Error handling** → Read 7-error-codes.md
- **Test requirements** → Read 3-verification.md
- **Functional requirements** → Read 1-functional.md (FR-1 through FR-4)

All skills must follow the **Spec-Driven Development** approach in .github/copilot-instructions.md.
