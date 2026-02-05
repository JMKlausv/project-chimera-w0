# Chimera Project Setup Notes

## Project Overview

**Chimera** is a spec-driven Python project for building autonomous AI influencer agents that research trends, generate content, and manage social engagement.

**Core Principle:** Specs drive everything → Code implements specs → Tests verify specs are met.

---

## Directory Structure & Purposes

### `specs/` - Specification Documents
Single source of truth. All implementation decisions derive from here.

| File | Purpose |
|------|---------|
| `0-meta.md` | Project vision, constraints, tech stack, architecture pattern |
| `1-functional.md` | User stories & 4 functional requirements (FR-1 through FR-4) |
| `2-design.md` | Technical architecture, API schemas, database design, integrations |
| `3-verification.md` | Test strategy, acceptance criteria, verification for each requirement |

### `src/chimera/` - Production Code
Implementation of agents and core system.

```
src/chimera/
├── orchestrator/      # Coordinates workers, validates outputs, escalates
├── agents/            # Worker agents (Trend Analyst, Content Creator, etc.)
├── mcp/               # MCP integrations (social media, vector DB, wallet, OpenClaw)
├── schemas/           # Data validation (Trend Data Schema, Content Package, etc.)
├── security/          # Zero Trust: signing, sanitization, logging
└── utils/             # Shared utilities
```

### `tests/` - Test Suite
Automated verification mapped to `3-verification.md`.

```
tests/
├── unit/              # Individual agent/component testing
├── integration/       # Agent-to-agent communication
├── system/            # End-to-end workflows
├── security/          # Zero Trust validation
├── resilience/        # Idempotency, partial failures, concurrency
└── data/              # Schema/data integrity
```

### `skills/` - Agent Capabilities
Reusable, modular skill library that agents invoke.

Examples:
- `skill_fetch_trends.py` - Fetch trending data from platforms
- `skill_generate_content.py` - Generate content from trends
- `skill_publish_content.py` - Publish to platforms
- `skill_analyze_sentiment.py` - Analyze sentiment

**Purpose:** Composable, independently testable agent capabilities.

### `research/` - Exploration & Reference
Non-spec documentation, experiments, learning materials.

Examples:
- Market research on social platforms
- AI model comparisons
- OpenClaw protocol deep dives
- Persona templates
- Platform API documentation

**Purpose:** Supporting context. Specs should stay focused on implementation requirements.

### `.github/` - GitHub Configuration
- `workflows/` - CI/CD pipelines (test automation)
- `ISSUE_TEMPLATE/` - Issue templates
- `copilot-instructions.md` - AI-assisted development guidelines

### Root Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point for local development/debugging |
| `pyproject.toml` | Project metadata, dependencies (managed by uv) |
| `README.md` | Quick start, project overview, architecture |
| `.gitignore` | Git exclusion rules (populated with Python + uv standards) |
| `uv.lock` | Lock file for reproducible dependency versions (commit this) |

---

## Dependency Flow

```
specs/
  ↓
src/chimera/ (implements specs)
  ↓
tests/ (verifies against specs)
  ↓
skills/ (used by agents in src/)
  ↓
.github/ (runs tests in CI/CD)
```

---

## Functional Requirements (from `1-functional.md`)

| FR | Requirement | Coverage |
|----|-------------|----------|
| **FR-1** | Trend Discovery: Fetch from ≥2 platforms, >10k engagement, JSON schema | ✅ Specified |
| **FR-2** | Content Generation: Match persona, safety checks, package for review | ✅ Specified |
| **FR-3** | Human Approval Gate: HITL layer, approval tokens, review interface | ✅ Specified |
| **FR-4** | OpenClaw Integration: Status publishing, capability queries, ARP protocol | ✅ Specified |

---

## Tech Stack (from `0-meta.md`)

- **Language:** Python 3.11+
- **Package Manager:** uv
- **Database:** MongoDB (state) + Weaviate/pgvector (embeddings) + Redis (task queue)
- **Testing:** pytest
- **Containerization:** Docker
- **CI/CD:** GitHub Actions

---

## Current Project Status

### ✅ Completed
- [x] Spec documentation (specs/ directory complete)
- [x] Comprehensive verification plan (`3-verification.md`)
- [x] Project structure established
- [x] `.gitignore` configured for Python + uv
- [x] Directory purposes documented

### ⏳ In Progress / TODO

**High Priority:**
1. [ ] Populate `README.md` with project overview, quick start, architecture diagram
2. [ ] Implement `src/chimera/` - Agent infrastructure & base classes
3. [ ] Implement `skills/` - Modular skill library
4. [ ] Implement `tests/` - Test suite aligned with `3-verification.md`

**Medium Priority:**
5. [ ] Set up `.github/workflows/` - CI/CD pipelines
6. [ ] Configure `pyproject.toml` with dependencies (anthropic, fastapi, pymongo, weaviate, etc.)
7. [ ] Set up local dev environment (PostgreSQL, MongoDB, Weaviate)

**Lower Priority:**
8. [ ] Populate `research/` with supporting documentation
9. [ ] Create issue templates & development guidelines
10. [ ] Set up pre-commit hooks for code quality

---

## Development Workflow

1. **Understand the spec** → Read relevant file in `specs/`
2. **Write tests first** → Create tests in `tests/` aligned with `3-verification.md`
3. **Implement code** → Add implementation in `src/chimera/` or `skills/`
4. **Verify tests pass** → Run test suite locally
5. **Update specs if needed** → Only if implementation reveals spec gaps
6. **Commit & push** → GitHub Actions runs test suite automatically

---

## Key Principles

### Spec-Driven Development
- **No code without specs** - Every feature must be specified first in `specs/`
- **Specs are the contract** - Implementation must satisfy spec requirements
- **Tests verify specs** - If tests pass, specs are met

### Zero Trust Model
- Agents are potential security vectors
- Every action logged and auditable
- No direct shell access
- All external content sanitized
- Human-in-the-loop for safety-critical decisions

### Hierarchical Swarm Architecture
- **Orchestrator Agent (Governor)** - Coordinates workflow
- **Worker Agents** - Specialized (Analyst, Creator, Distributor, Judge)
- **Judge Agent** - Quality control & escalation
- **Human Reviewer** - Final approval gate for low-confidence content

---

## Getting Started Checklist

- [ ] Review `specs/0-meta.md` for project vision
- [ ] Review `specs/1-functional.md` for requirements
- [ ] Review `specs/2-design.md` for architecture
- [ ] Review `specs/3-verification.md` for testing strategy
- [ ] Set up Python 3.11+ environment with uv
- [ ] Install project dependencies: `uv pip install -e .`
- [ ] Run tests: `pytest tests/ -v`
- [ ] Start implementing agents in `src/chimera/`

---

## References

- **Specs:** See `/specs/` directory for complete specification
- **Architecture:** [2-design.md](specs/2-design.md) - System design, schemas, integration points
- **Testing:** [3-verification.md](specs/3-verification.md) - Test strategy, acceptance criteria
- **Tech:** See `pyproject.toml` for dependencies and `0-meta.md` for tech stack overview
