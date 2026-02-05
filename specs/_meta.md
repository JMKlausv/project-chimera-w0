# Project Chimera - Meta Specification

## Vision
Build the infrastructure for autonomous AI influencer agents that research trends, generate content, and manage social engagement without human intervention.

## Constraints
- Spec-Driven Development: No code without ratified specs
- Human-in-the-Loop: Safety layer for content approval
- MCP-First: All external integrations via Model Context Protocol
- Zero Trust: Agents are potential security vectors

## Architecture Pattern
**Hierarchical Swarm:**
- Orchestrator Agent (Governor)
- Specialized Worker Agents (Trend Analyst, Content Creator, Distributor)
- Judge Agent (Quality Control)

## Tech Stack
- Language: Python 3.11+
- Package Manager: uv
- Containerization: Docker
- Database: NoSQL (MongoDB) + Vector DB (Weaviate/pgvector)
- Testing: pytest
- CI/CD: GitHub Actions

## Success Criteria
Repository is so well-specified that an AI agent swarm can implement features with minimal human conflict.