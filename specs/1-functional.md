# Functional Specification

## User Stories

### As an Orchestrator Agent
- I need to coordinate multiple worker agents to complete influencer tasks
- I need to check all worker outputs against the specs before proceeding
- I need to escalate to human review when confidence is below threshold

### As a Trend Analyst Agent
- I need to fetch trending topics from social platforms via MCP
- I need to analyze sentiment and engagement metrics
- I need to output structured trend data: {topic, engagement_score, sentiment, timestamp}

### As a Content Creator Agent
- I need to receive trend data and persona guidelines
- I need to generate video scripts, captions, and hashtags
- I need to output a content package: {script, media_urls, metadata}

### As a Distribution Agent
- I need to receive approved content packages
- I need to publish to target platforms via MCP
- I need to monitor engagement and report metrics

### As a Human Reviewer (HITL)
- I need to see flagged content with context
- I need to approve/reject/edit within 2 minutes
- I need to provide feedback that improves agent confidence

## Functional Requirements

### FR-1: Trend Discovery & Perception System

#### FR-1.0: Active Resource Monitoring (SRS 4.2, FR 2.0)
- Agent MUST fetch data exclusively via MCP Resources (not direct API calls)
- Agent MUST support ≥2 concurrent resource streams (e.g., twitter://mentions/recent, news://ethiopia/fashion/trends)
- Agent MUST poll resources at configurable intervals (default: 30 minutes)
- Agent MUST handle resource unavailability gracefully with fallback streams

#### FR-1.1: Semantic Filtering & Relevance Scoring (SRS 4.2, FR 2.1)
- ALL ingested content MUST pass through Semantic Filter using lightweight LLM (Gemini 3 Flash)
- Filter MUST score relevance to agent's active campaign goals on 0.0-1.0 scale
- Only content exceeding configurable Relevance Threshold (e.g., 0.75) SHALL trigger task creation
- Scoring MUST consider: topic alignment, sentiment match, engagement potential, goal fit
- Agent MUST NOT automatically respond to content below threshold

#### FR-1.2: Trend Detection via Trend Spotter (SRS 4.2, FR 2.2)
- System MUST implement "Trend Spotter" background worker analyzing aggregated data over time windows (default: 4 hours)
- Trend Spotter MUST detect topic clusters (related topics emerging together)
- When cluster detected, Trend Spotter MUST generate "Trend Alert" and feed to Planner context
- Trend Alert MUST include: cluster_topics, emergence_timestamp, confidence_score, campaign_relevance
- Trend Spotter MUST run continuously independent of primary task queue

#### FR-1.3: High-Engagement Thresholding
- Within accepted trends, Agent MUST filter for topics with engagement_score ≥ 10,000
- Engagement scoring MUST incorporate: likes, comments, shares, impressions
- Agent MUST track engagement metrics per platform with normalized scoring

#### FR-1.4: Standardized Trend Data Output
- ALL trend data MUST conform to Trend Data Schema
- Output format: JSON with standardized schema (see Design Specification)

### FR-2: Content Generation
- Agent MUST generate content matching persona voice
- Agent MUST include safety checks (no offensive content)
- Output MUST be packaged for human review

### FR-3: Human Approval Gate
- All content MUST pass through HITL layer before publication
- Agent MUST NOT publish without approval token
- Review interface MUST show content + justification

### FR-4: OpenClaw Integration
- Agent MUST publish availability status to OpenClaw network
- Agent MUST respond to capability queries from other agents
- Protocol: Agent Relay Protocol (ARP)