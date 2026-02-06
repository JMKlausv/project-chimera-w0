# Project Chimera

**Autonomous AI Influencer Infrastructure** -- A spec-driven platform for autonomous AI agents that research trends, generate content, and manage social engagement.

## Vision

Build the infrastructure for autonomous AI influencer agents that operate as a hierarchical swarm: an Orchestrator (Governor) coordinates specialized Worker Agents (Trend Analyst, Content Creator, Distribution Manager) while a Judge Agent enforces quality control. All content passes through a Human-in-the-Loop approval gate before publication.

## Architecture

```
                    ┌─────────────────┐
                    │   Orchestrator   │
                    │   (Governor)     │
                    └────────┬────────┘
               ┌─────────────┼─────────────┐
               v             v             v
     ┌─────────────┐ ┌─────────────┐ ┌──────────────┐
     │ Trend        │ │ Content     │ │ Distribution │
     │ Analyst      │ │ Creator     │ │ Manager      │
     └──────┬──────┘ └──────┬──────┘ └──────┬───────┘
            │               │               │
            v               v               v
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │ MCP Resources│ │ LLM (Gemini)│ │ MCP Publish │
     └─────────────┘ └─────────────┘ └─────────────┘
                            │
                    ┌───────v───────┐
                    │  Judge Agent  │
                    │ (Quality Ctrl)│
                    └───────┬───────┘
                            v
                    ┌───────────────┐
                    │  HITL Review  │
                    │  (Human Gate) │
                    └───────────────┘
```

### 4-Phase Content Pipeline

| Phase | Skill | Agent | P95 Target |
|-------|-------|-------|------------|
| 1. Trend Discovery | `fetch_trends` | Trend Analyst | 8s |
| 1. Semantic Filtering | `semantic_filter` | Orchestrator | 3s |
| 2. Content Creation | `generate_content` | Content Creator | 25s |
| 3. Quality Assurance | `validate_content` | Judge Agent | 2s |
| 4. Distribution | `publish_content` | Distribution Manager | 10s |

**End-to-end P95: ~48s** (within 60s SLA)

## Core Design Principles

- **Spec-Driven Development** -- No code without ratified specs
- **MCP-First** -- All external integrations via Model Context Protocol, never direct API calls
- **Human-in-the-Loop** -- Safety layer for content approval before any publication
- **Zero Trust** -- Agents are treated as potential security vectors

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| Package Manager | [uv](https://github.com/astral-sh/uv) |
| Build System | hatchling |
| Testing | pytest |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Database | MongoDB + Vector DB (Weaviate/pgvector) |
| LLM | Gemini 3 Flash (primary), GPT-4o-mini (fallback) |
| Code Review | CodeRabbit AI |

## Project Structure

```
chymera-w0/
├── specs/                          # Ratified specifications (source of truth)
│   ├── _meta.md                    # Vision, constraints, architecture
│   ├── 1-functional.md             # Functional requirements (FR-1 to FR-4)
│   ├── 2-design.md                 # Data schemas, SLAs, state machine
│   ├── 3-verification.md           # Test strategy, CI/CD requirements
│   ├── 4-skills-api.md             # Skill interface contracts
│   ├── 5-mcp-resources.md          # MCP endpoints, rate limits
│   └── 7-error-codes.md            # 37 error codes, recovery strategies
│
├── skills/                         # Skill documentation & contracts
│   ├── README.md                   # Skills index & dependency graph
│   ├── fetch_trends.md             # Trend fetching skill spec
│   ├── semantic_filter.md          # Semantic filtering skill spec
│   ├── generate_content.md         # Content generation skill spec
│   ├── validate_content.md         # Content validation skill spec
│   └── publish_content.md          # Content publishing skill spec
│
├── src/chimera/                    # Source code (implementation)
│   └── __init__.py
│
├── tests/                          # Test suite
│   └── unit/
│       ├── models/
│       │   ├── test_trend_data_schema.py       # TrendData schema tests
│       │   ├── test_content_package_schema.py  # ContentPackage schema tests
│       │   └── test_error_codes.py             # Error catalog & SpecError tests
│       └── skills/
│           ├── test_fetch_trends.py            # fetch_trends contract tests
│           └── test_semantic_filter.py         # semantic_filter contract tests
│
├── .github/
│   ├── workflows/ci.yml            # CI pipeline (unit, integration, docker)
│   └── copilot-instructions.md     # AI coding guidelines
│
├── .coderabbit.yaml                # CodeRabbit AI review config
├── dockerfile                      # Container image definition
├── Makefile                        # Dev commands (test, lint, docker)
├── pyproject.toml                  # Project metadata & dependencies
└── main.py                         # Application entry point
```

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/<org>/chymera-w0.git
cd chymera-w0

# Install dependencies
make install
# or directly:
uv sync
```

### Running Tests

```bash
# Run all unit tests (default)
make test

# Run specific test suites
make test-models    # Schema/model tests only
make test-skills    # Skill contract tests only
make test-all       # All tests with verbose output

# Run directly with pytest
uv run pytest tests/unit/ -v
```

### Code Quality

```bash
# Lint with ruff
make lint

# Auto-format
make format
```

### Docker

```bash
# Build the image
make docker-build

# Run tests in container
make docker-test

# Run the application
make docker-run
```

## Specifications

All development follows the **Spec-Driven Development** approach. Specs are the source of truth:

| Spec | Description |
|------|-------------|
| [_meta.md](specs/_meta.md) | Project vision, constraints, architecture pattern |
| [1-functional.md](specs/1-functional.md) | Functional requirements FR-1 through FR-4 |
| [2-design.md](specs/2-design.md) | Data schemas (TrendData, ContentPackage, AgentProfile), SLAs, state machine |
| [3-verification.md](specs/3-verification.md) | Test strategy, coverage targets, CI/CD requirements |
| [4-skills-api.md](specs/4-skills-api.md) | Complete skill interface contracts with I/O schemas |
| [5-mcp-resources.md](specs/5-mcp-resources.md) | MCP endpoints, rate limits, fallback chains |
| [7-error-codes.md](specs/7-error-codes.md) | 37 error codes across 8 categories, recovery strategies |

## Skills

The system defines 11 skills across 4 agent types. See [skills/README.md](skills/README.md) for the full index.

### Implementation Status

| Skill | Spec | Implementation |
|-------|------|----------------|
| `fetch_trends` | Complete | Pending |
| `semantic_filter` | Complete | Pending |
| `generate_content` | Complete | Pending |
| `validate_content` | Complete | Pending |
| `publish_content` | Complete | Pending |
| `get_agent_profile` | Planned | Pending |
| `update_agent_state` | Planned | Pending |
| `fetch_wallet_balance` | Planned | Pending |
| `debit_wallet` | Planned | Pending |
| `register_openclaw_profile` | Planned | Pending |
| `respond_to_arp_query` | Planned | Pending |

## Data Schemas

Three core schemas defined in [specs/2-design.md](specs/2-design.md):

- **TrendData** -- Standardized trend output (topic, engagement_score, sentiment, platform metadata)
- **ContentPackage** -- Generated content bundle (script, media_urls, captions, hashtags, confidence_score)
- **AgentProfile** -- Agent configuration and state (persona, capabilities, active campaigns)

## Error Handling

37 error codes organized into 8 categories with structured recovery strategies:

| Category | Prefix | Examples |
|----------|--------|---------|
| External | `EXT_` | Platform unavailable, rate limited, auth expired |
| Validation | `VAL_` | Schema invalid, content too long, forbidden words |
| Resource | `RES_` | Database unavailable, cache miss, storage full |
| State | `STATE_` | Invalid transition, version conflict, agent suspended |
| Security | `SEC_` | Token invalid, permission denied, rate abuse |
| Platform | `PLAT_` | API changed, feature unavailable, region blocked |
| Financial | `FIN_` | Insufficient balance, transaction failed |
| Network | `NET_` | Timeout, connection refused, DNS failure |

All errors use the `SpecError` class with code, message, HTTP status, timestamp, request ID, and recovery details. See [specs/7-error-codes.md](specs/7-error-codes.md).

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`):

- **Unit tests** -- Run on every push and PR
- **Integration tests** -- Run on PRs only (after unit tests pass)
- **Docker build** -- Verify image builds cleanly (after unit tests pass)

Coverage targets per [specs/3-verification.md](specs/3-verification.md): >=80% unit, >=60% integration.

## AI Code Review

CodeRabbit is configured (`.coderabbit.yaml`) with assertive review profile and path-specific instructions:

- `src/**/*.py` -- Verified against spec schemas, error codes, skill contracts, MCP-first policy
- `tests/**/*.py` -- Checked against verification spec, coverage targets, flaky patterns
- `specs/**/*.md` -- Reviewed for breaking changes, missing error codes, inconsistencies
- `dockerfile` -- Validated for pinned versions, no secrets, Python version match
- `.github/**/*.yml` -- Verified against CI requirements from verification spec

## License

See repository for license details.
