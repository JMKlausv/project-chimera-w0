# Design Specification

## System Architecture

### Components

1. **Orchestrator Service**
   - Manages worker lifecycle
   - Maintains global state (GlobalState)
   - Routes tasks to appropriate workers
   - Implements Optimistic Concurrency Control (OCC) for state consistency
   - Hosts centralized Dashboard for Network Operators

2. **Perception System** (Implements FR-1)
   - **Resource Monitor**: Polls MCP Resources continuously
   - **Semantic Filter**: LLM-based relevance scoring (Gemini 3 Flash)
   - **Trend Spotter**: Background worker detecting topic clusters over configurable windows
   - **Relevance Threshold Gate**: Configurable (default 0.75) to decide task creation

3. **FastRender Swarm Architecture**
   - **Planner Agent**: Decomposes goals into task DAG, monitors GlobalState, dynamic re-planning
   - **Worker Pool**: Stateless agents executing atomic tasks from TaskQueue
   - **Judge Agent**: Quality control, confidence-based escalation, output validation
   - **CFO Judge**: Specialized Judge for budget governance (Coinbase AgentKit)

4. **Worker Agents**
   - Trend Analyst (consumes Perception System)
   - Content Creator
   - Distribution Manager
   - Judge (Quality Control)

5. **MCP Servers** (External Integrations)
   - **mcp-server-twitter**: Resources (mentions, feed); Tools (post_tweet, reply)
   - **mcp-server-news**: Resources (trends, category feeds) for multi-region trend data
   - **mcp-server-weaviate**: Vector database for RAG memory retrieval
   - **mcp-server-coinbase**: AgentKit wallet, transactions, balance queries
   - **mcp-server-openclaw**: OpenClaw heartbeat, ARP queries, profile registration
   - **mcp-server-ideogram**: Image generation tools
   - **mcp-server-runwayml**: Video generation tools
   - Custom MCP Servers: Analytics, webhooks, proprietary data sources

6. **Storage Layer**
   - MongoDB: Agent state, memories, content drafts, campaign configs
   - Weaviate: Vector embeddings for semantic memory retrieval (RAG)
   - PostgreSQL: User data, audit logs, transactional records
   - Redis: TaskQueue, ReviewQueue, rate limiting, episode caching
   - Blockchain (Base/Ethereum): Immutable ledger for financial transactions

## Perception System Architecture

### MCP Resources for Trend Detection
```
twitter://mentions/recent          -> Recent mentions of the agent
twitter://feed/{user_id}           -> User timeline with trending posts
news://global/trends               -> Global trending topics
news://region/{region}/trends      -> Region-specific trends (e.g., ethiopia)
news://category/{category}/trends  -> Category trends (fashion, tech, crypto)
market://crypto/{asset}/trending   -> Cryptocurrency trending topics
```

### Semantic Filter Pipeline
**Process:**
1. Ingest content from MCP Resource
2. Pass through Semantic Filter (Gemini 3 Flash LLM)
3. Score relevance to active campaign goals (0.0-1.0 scale)
4. If score ≥ Relevance Threshold (default 0.75): Create Task for Planner
5. If score < threshold: Discard (do not trigger automatic response)

**Scoring Criteria:**
- Topic alignment with campaign goals
- Sentiment match (positive/neutral/negative relevance)
- Engagement potential (likes, comments, shares trending upward)
- Recency (prefer fresh data within 24 hours)
- Uniqueness (avoid duplicate topics)

### Trend Spotter Algorithm
**Execution:**
1. Aggregate content from all resources over configurable window (default: 4 hours)
2. Vectorize topics using semantic embeddings (Weaviate)
3. Cluster similar topics (cosine_similarity > 0.8)
4. For each cluster:
   - Calculate cluster_confidence = avg(topic_engagement, cluster_cohesion)
   - Filter clusters with aggregate engagement_score ≥ 5,000
   - Generate Trend Alert
5. Feed Trend Alert to Planner as campaign opportunity
6. Continue running as background Worker independent of TaskQueue

### Trend Alert Schema
```json
{
  "alert_id": {
    "type": "string",
    "format": "uuid",
    "required": true,
    "description": "Unique identifier for this trend alert"
  },
  "cluster_topics": {
    "type": "array",
    "items": { "type": "string", "minLength": 1, "maxLength": 500 },
    "required": true,
    "minItems": 2,
    "maxItems": 20,
    "description": "Related topics that emerged together in cluster"
  },
  "emergence_timestamp": {
    "type": "string",
    "format": "ISO8601",
    "required": true,
    "description": "When the trend cluster was first detected"
  },
  "emergence_window": {
    "type": "string",
    "pattern": "^[0-9]+(h|m)$",
    "required": true,
    "description": "Time window for aggregation (e.g., '4h', '30m')"
  },
  "confidence_score": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "required": true,
    "description": "Cluster confidence: avg(topic_engagement_norm, cluster_cohesion). Use for filtering."
  },
  "engagement_aggregate": {
    "type": "integer",
    "minimum": 5000,
    "required": true,
    "description": "Sum of engagement_scores across all cluster topics. Threshold: ≥5000 to trigger alert."
  },
  "platforms": {
    "type": "array",
    "items": { "type": "string", "enum": ["twitter", "news", "market", "reddit", "tiktok"] },
    "required": true,
    "minItems": 1,
    "description": "Platforms where trend was detected"
  },
  "campaign_relevance": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "required": true,
    "description": "Relevance score vs active campaign goals. High (>0.75) signals actionable opportunity."
  },
  "recommended_action": {
    "type": "string",
    "minLength": 10,
    "maxLength": 1000,
    "required": true,
    "description": "LLM-generated action suggestion for Planner Agent"
  },
  "decay_score": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "required": true,
    "description": "Trend freshness (1.0 = just detected, 0.0 = stale). Decays hourly."
  },
  "cluster_cohesion": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "required": true,
    "description": "Semantic similarity of cluster topics (cosine_similarity > 0.8 indicates coherent cluster)"
  }
}
```

## API Contracts

### Trend Data Schema
```json
{
  "trend_id": {
    "type": "string",
    "format": "uuid",
    "required": true,
    "description": "Unique identifier for this trend detection instance"
  },
  "topic": {
    "type": "string",
    "required": true,
    "minLength": 1,
    "maxLength": 500,
    "description": "The primary topic, keyword, or hashtag"
  },
  "platform": {
    "type": "string",
    "enum": ["twitter", "news", "market", "reddit", "tiktok"],
    "required": true,
    "description": "Source platform where trend originated"
  },
  "sentiment": {
    "type": "string",
    "enum": ["positive", "neutral", "negative"],
    "required": true,
    "description": "Aggregated sentiment of trend discussion"
  },
  "timestamp": {
    "type": "string",
    "format": "ISO8601",
    "required": true,
    "description": "When trend was first detected/published"
  },
  "engagement": {
    "type": "object",
    "required": true,
    "properties": {
      "likes": {
        "type": "integer",
        "minimum": 0,
        "required": true,
        "description": "Total likes/reactions"
      },
      "comments": {
        "type": "integer",
        "minimum": 0,
        "required": true,
        "description": "Total comments/replies"
      },
      "shares": {
        "type": "integer",
        "minimum": 0,
        "required": true,
        "description": "Total shares/retweets"
      },
      "impressions": {
        "type": "integer",
        "minimum": 0,
        "required": true,
        "description": "Total views/impressions"
      },
      "engagement_score": {
        "type": "number",
        "minimum": 0,
        "maximum": 1000000,
        "required": true,
        "description": "Normalized engagement metric: (likes + comments*2 + shares*3)"
      }
    }
  },
  "trend_velocity": {
    "type": "number",
    "minimum": 0,
    "required": true,
    "description": "Growth rate in past 24h (engagement_score_24h / engagement_score_7d)"
  },
  "decay_score": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "required": true,
    "description": "Relevance decay (1.0 = fresh, 0.0 = stale). Decays hourly after detection."
  },
  "geographic_origin": {
    "type": "string",
    "required": false,
    "enum": ["global", "US", "EU", "LATAM", "APAC", "AFRICA", "MENA"],
    "description": "Geographic region where trend originated or is strongest"
  },
  "metadata": {
    "type": "object",
    "required": false,
    "properties": {
      "hashtags": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 50,
        "description": "Associated hashtags"
      },
      "mentions": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 50,
        "description": "Mentioned accounts/entities"
      },
      "source_urls": {
        "type": "array",
        "items": { "type": "string", "format": "uri" },
        "maxItems": 10,
        "description": "URLs referenced in trend"
      },
      "category": {
        "type": "string",
        "enum": ["technology", "fashion", "finance", "entertainment", "news", "crypto", "other"],
        "description": "Categorized topic domain"
      }
    },
    "additionalProperties": false
  }
}
```

### Content Package Schema
```json
{
  "content_id": {
    "type": "string",
    "format": "uuid",
    "required": true,
    "description": "Unique identifier for this content package"
  },
  "task_id": {
    "type": "string",
    "format": "uuid",
    "required": true,
    "description": "Reference to parent task (PostgreSQL foreign key)"
  },
  "trend_ref": {
    "type": "string",
    "format": "uuid",
    "required": true,
    "description": "Reference to TrendData document in MongoDB"
  },
  "script": {
    "type": "string",
    "minLength": 50,
    "maxLength": 5000,
    "required": true,
    "description": "Video/content script matching agent persona. Min 50 chars (sanity check), max 5000."
  },
  "media_urls": {
    "type": "array",
    "items": { "type": "string", "format": "uri" },
    "required": true,
    "minItems": 1,
    "maxItems": 10,
    "description": "URLs to generated media (images from Ideogram, videos from RunwayML). ≥1 required."
  },
  "media_metadata": {
    "type": "array",
    "required": false,
    "items": {
      "type": "object",
      "properties": {
        "url": { "type": "string", "format": "uri" },
        "type": { "type": "string", "enum": ["image", "video"] },
        "duration_sec": { "type": "number", "minimum": 0, "maximum": 600 },
        "size_bytes": { "type": "integer", "minimum": 0 },
        "generated_by": { "type": "string", "enum": ["ideogram", "runwayml"] }
      }
    },
    "description": "Metadata for each media file (duration, size, generator)"
  },
  "captions": {
    "type": "string",
    "minLength": 20,
    "maxLength": 2000,
    "required": true,
    "description": "Platform-specific captions (multi-platform format handled separately)"
  },
  "hashtags": {
    "type": "array",
    "items": { "type": "string", "pattern": "^#[a-zA-Z0-9_]{1,30}$" },
    "required": true,
    "minItems": 3,
    "maxItems": 30,
    "description": "Hashtags matching trend topics and campaign goals. Min 3, max 30."
  },
  "confidence_score": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "required": true,
    "description": "Agent confidence in output quality. <0.8 triggers human review, ≥0.8 may auto-publish."
  },
  "requires_review": {
    "type": "boolean",
    "required": true,
    "description": "Always true if confidence_score < 0.8. Determined by Judge Agent."
  },
  "generation_metadata": {
    "type": "object",
    "required": false,
    "properties": {
      "generator_agent": { "type": "string", "description": "Which agent generated this content" },
      "model": { "type": "string", "description": "LLM model used (e.g., 'gemini-3-flash')" },
      "persona_applied": { "type": "string", "enum": ["strict", "flexible", "experimental"] },
      "safety_checks_passed": { "type": "boolean" },
      "generation_time_ms": { "type": "integer", "minimum": 0 }
    },
    "additionalProperties": false
  },
  "platform_variants": {
    "type": "object",
    "required": false,
    "description": "Platform-specific adaptations",
    "properties": {
      "twitter": {
        "type": "object",
        "properties": {
          "text": { "type": "string", "maxLength": 280 },
          "media_ids": { "type": "array", "items": { "type": "string" } }
        }
      },
      "tiktok": {
        "type": "object",
        "properties": {
          "video_url": { "type": "string", "format": "uri" },
          "description": { "type": "string", "maxLength": 2200 },
          "sound_id": { "type": "string" }
        }
      },
      "instagram": {
        "type": "object",
        "properties": {
          "carousel_items": { "type": "array", "maxItems": 10 },
          "caption": { "type": "string", "maxLength": 2200 }
        }
      }
    },
    "additionalProperties": false
  }
}
```

## Campaign Configuration Schema

A campaign is a strategic initiative with defined goals, audience, budget, and content guidelines. The Planner Agent uses campaigns to filter trends, route tasks, and evaluate content.

```json
{
  "campaign_id": {
    "type": "string",
    "format": "uuid",
    "required": true,
    "description": "Unique campaign identifier"
  },
  "agent_id": {
    "type": "string",
    "format": "uuid",
    "required": true,
    "description": "Owner agent (foreign key to agents table)"
  },
  "name": {
    "type": "string",
    "minLength": 3,
    "maxLength": 200,
    "required": true,
    "description": "Campaign display name"
  },
  "goal": {
    "type": "string",
    "minLength": 10,
    "maxLength": 1000,
    "required": true,
    "description": "Primary campaign objective (e.g., 'Build luxury fashion brand awareness in Ethiopia')"
  },
  "status": {
    "type": "string",
    "enum": ["active", "paused", "completed", "archived"],
    "default": "active",
    "required": true
  },
  "start_date": {
    "type": "string",
    "format": "ISO8601",
    "required": true
  },
  "end_date": {
    "type": "string",
    "format": "ISO8601",
    "required": false,
    "description": "Optional end date; null = ongoing"
  },
  "budget": {
    "type": "object",
    "required": true,
    "properties": {
      "total_amount": {
        "type": "number",
        "minimum": 0,
        "required": true,
        "description": "Total budget in USDC"
      },
      "spent_amount": {
        "type": "number",
        "minimum": 0,
        "required": true,
        "description": "Amount already spent (read-only, calculated)"
      },
      "cost_per_post": {
        "type": "number",
        "minimum": 0,
        "required": false,
        "description": "Target cost per published post"
      },
      "currency": {
        "type": "string",
        "enum": ["USDC", "ETH", "BASE"],
        "default": "USDC"
      }
    }
  },
  "trend_filters": {
    "type": "object",
    "required": true,
    "description": "Criteria for trend selection",
    "properties": {
      "engagement_min": {
        "type": "integer",
        "minimum": 0,
        "default": 10000,
        "description": "Minimum engagement_score threshold"
      },
      "engagement_max": {
        "type": "integer",
        "minimum": 10000,
        "required": false,
        "description": "Optional max to avoid oversaturated trends"
      },
      "sentiment": {
        "type": "array",
        "items": { "type": "string", "enum": ["positive", "neutral", "negative", "mixed"] },
        "minItems": 1,
        "default": ["positive", "neutral"],
        "description": "Allowed sentiment values"
      },
      "decay_score_min": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "default": 0.5,
        "description": "Minimum freshness (1.0 = brand new, 0.0 = stale)"
      },
      "trend_velocity_min": {
        "type": "number",
        "minimum": 0,
        "required": false,
        "description": "Minimum growth rate (optional)"
      },
      "topics": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 50,
        "required": false,
        "description": "Whitelisted topics (e.g., ['fashion', 'luxury'])"
      },
      "excluded_topics": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 50,
        "required": false,
        "description": "Blacklisted topics"
      },
      "platforms": {
        "type": "array",
        "items": { "type": "string", "enum": ["twitter", "news", "market", "reddit", "tiktok"] },
        "minItems": 1,
        "description": "Source platforms to monitor"
      },
      "regions": {
        "type": "array",
        "items": { "type": "string", "enum": ["global", "US", "EU", "LATAM", "APAC", "AFRICA", "MENA"] },
        "minItems": 1,
        "default": ["global"],
        "description": "Geographic focus"
      },
      "categories": {
        "type": "array",
        "items": { "type": "string", "enum": ["technology", "fashion", "finance", "entertainment", "news", "crypto", "sports", "health", "other"] },
        "required": false,
        "description": "Content categories to target"
      }
    }
  },
  "content_guidelines": {
    "type": "object",
    "required": true,
    "description": "Content generation constraints",
    "properties": {
      "persona_id": {
        "type": "string",
        "format": "uuid",
        "required": true,
        "description": "Reference to Agent Persona to use"
      },
      "content_types": {
        "type": "array",
        "items": { "type": "string", "enum": ["video_script", "carousel", "single_post", "thread"] },
        "minItems": 1,
        "required": true
      },
      "required_hashtags": {
        "type": "array",
        "items": { "type": "string", "pattern": "^#[a-zA-Z0-9_]{1,30}$" },
        "maxItems": 10,
        "required": false,
        "description": "Hashtags to always include"
      },
      "required_mentions": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 10,
        "required": false,
        "description": "Accounts to mention (sponsors, partners)"
      },
      "brand_safety_level": {
        "type": "string",
        "enum": ["strict", "moderate", "flexible"],
        "default": "moderate",
        "description": "How restrictive safety filters should be"
      },
      "approval_required": {
        "type": "boolean",
        "default": true,
        "description": "All content requires human approval before publishing"
      },
      "auto_publish_threshold": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "default": 0.95,
        "description": "Confidence score above which auto-publish (if approval_required=false)"
      }
    }
  },
  "performance_targets": {
    "type": "object",
    "required": false,
    "properties": {
      "target_engagement_rate": {
        "type": "number",
        "minimum": 0,
        "maximum": 100,
        "description": "Expected engagement % per post"
      },
      "target_reach_per_post": {
        "type": "integer",
        "minimum": 100,
        "description": "Expected impressions per post"
      },
      "target_conversion_rate": {
        "type": "number",
        "minimum": 0,
        "maximum": 100,
        "required": false,
        "description": "Expected conversion % (if commerce goal)"
      },
      "target_posts_per_week": {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "description": "Posting frequency target"
      }
    }
  },
  "external_references": {
    "type": "object",
    "required": false,
    "properties": {
      "brand_id": {
        "type": "string",
        "required": false,
        "description": "Link to external brand/client system"
      },
      "utm_source": {
        "type": "string",
        "required": false,
        "description": "UTM parameter for tracking"
      },
      "analytics_dashboard": {
        "type": "string",
        "format": "uri",
        "required": false,
        "description": "Link to external analytics"
      }
    }
  },
  "created_at": {
    "type": "string",
    "format": "ISO8601",
    "required": true
  },
  "updated_at": {
    "type": "string",
    "format": "ISO8601",
    "required": true
  }
}
```

### Campaign Usage in Task Routing

**Planner Agent** uses campaign filters to decide:
1. Which trends are relevant
2. What persona to apply
3. Whether to approve auto-publish or require review
4. Cost limits for the task

**Example: Fashion Campaign**
```json
{
  "campaign_id": "fashion-2025-q1",
  "name": "Luxury Fashion Ethiopia Launch",
  "goal": "Build brand awareness for sustainable fashion in Ethiopia",
  "trend_filters": {
    "topics": ["fashion", "luxury", "sustainability"],
    "regions": ["AFRICA", "global"],
    "platforms": ["twitter", "tiktok", "instagram"],
    "engagement_min": 15000,
    "sentiment": ["positive"]
  },
  "content_guidelines": {
    "persona_id": "luna-styles-persona",
    "content_types": ["video_script", "carousel"],
    "required_hashtags": ["#SustainableFashion", "#EthiopiaStyle"],
    "approval_required": true
  }
}
```

## Agent Persona Schema

Each agent has a distinct persona that governs content generation, engagement style, and decision-making. The persona schema ensures consistent voice across all outputs.

```json
{
  "agent_id": {
    "type": "string",
    "format": "uuid",
    "required": true,
    "description": "Reference to agent (immutable)"
  },
  "name": {
    "type": "string",
    "minLength": 3,
    "maxLength": 100,
    "required": true,
    "description": "Agent's public display name"
  },
  "bio": {
    "type": "string",
    "minLength": 10,
    "maxLength": 500,
    "required": true,
    "description": "Short bio/mission statement"
  },
  "voice_tone": {
    "type": "string",
    "enum": ["formal", "casual", "humorous", "technical", "inspirational", "edgy"],
    "required": true,
    "description": "Overall communication style"
  },
  "target_audience": {
    "type": "object",
    "required": true,
    "properties": {
      "age_range": {
        "type": "string",
        "enum": ["13-17", "18-24", "25-34", "35-44", "45-54", "55+", "all"],
        "required": true
      },
      "demographics": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 10,
        "examples": ["students", "professionals", "entrepreneurs", "parents"],
        "required": false
      },
      "interests": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 20,
        "examples": ["fashion", "technology", "sustainability", "crypto"],
        "required": true
      },
      "regions": {
        "type": "array",
        "items": { "type": "string", "enum": ["global", "US", "EU", "LATAM", "APAC", "AFRICA", "MENA"] },
        "required": true,
        "minItems": 1
      }
    }
  },
  "vocabulary": {
    "type": "object",
    "required": true,
    "properties": {
      "preferred_words": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 100,
        "examples": ["rad", "vibe", "slay", "fire"],
        "description": "Vocabulary to prioritize in content"
      },
      "forbidden_words": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 100,
        "description": "Words/phrases to never use"
      },
      "jargon_level": {
        "type": "string",
        "enum": ["beginner", "intermediate", "advanced", "expert"],
        "description": "Technical complexity of language"
      }
    }
  },
  "content_style": {
    "type": "object",
    "required": true,
    "properties": {
      "post_length_preference": {
        "type": "string",
        "enum": ["concise", "medium", "detailed"],
        "description": "Script/caption length tendency"
      },
      "emoji_usage": {
        "type": "string",
        "enum": ["none", "minimal", "moderate", "heavy"],
        "default": "moderate"
      },
      "hashtag_strategy": {
        "type": "string",
        "enum": ["none", "trending_only", "mix_popular_niche", "comprehensive"],
        "default": "mix_popular_niche"
      },
      "media_preference": {
        "type": "string",
        "enum": ["text_only", "text_images", "videos", "mixed"],
        "description": "Preferred media types"
      },
      "storytelling_style": {
        "type": "string",
        "enum": ["narrative", "listicle", "question_answer", "data_driven", "inspirational"],
        "description": "How to structure content"
      }
    }
  },
  "engagement_strategy": {
    "type": "object",
    "required": true,
    "properties": {
      "goal": {
        "type": "string",
        "enum": ["viral", "authentic", "educational", "commerce", "community_building"],
        "description": "Primary engagement objective"
      },
      "call_to_action": {
        "type": "string",
        "enum": ["none", "like_comment_share", "link_click", "purchase", "follow"],
        "description": "What action to encourage"
      },
      "controversy_level": {
        "type": "string",
        "enum": ["safe", "moderate", "edgy"],
        "default": "moderate",
        "description": "How much risk-taking acceptable"
      },
      "authenticity_weight": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "default": 0.7,
        "description": "Balance between authentic vs promotional (1.0 = fully authentic, 0.0 = fully promotional)"
      }
    }
  },
  "platform_preferences": {
    "type": "object",
    "required": true,
    "properties": {
      "twitter": { "type": "number", "minimum": 0, "maximum": 1, "description": "Activity score (0 = never, 1 = always)" },
      "tiktok": { "type": "number", "minimum": 0, "maximum": 1 },
      "instagram": { "type": "number", "minimum": 0, "maximum": 1 },
      "youtube": { "type": "number", "minimum": 0, "maximum": 1 },
      "linkedin": { "type": "number", "minimum": 0, "maximum": 1 }
    },
    "description": "Relative activity distribution across platforms"
  },
  "brand_guidelines": {
    "type": "object",
    "required": false,
    "properties": {
      "colors": {
        "type": "array",
        "items": { "type": "string", "pattern": "^#[0-9A-F]{6}$" },
        "maxItems": 5,
        "description": "Brand color palette (hex codes)"
      },
      "forbidden_associations": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 50,
        "description": "Topics/brands to avoid (e.g., 'competitor-x', 'controversial-topic')"
      },
      "required_disclaimers": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 5,
        "description": "Legal disclaimers to include (e.g., '#ad', '#notfinancialadvice')"
      }
    }
  },
  "values": {
    "type": "object",
    "required": true,
    "properties": {
      "core_values": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 5,
        "examples": ["sustainability", "inclusivity", "innovation", "authenticity"],
        "required": true,
        "description": "Core beliefs guiding content"
      },
      "causes_supported": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 10,
        "examples": ["environmental_protection", "education", "social_justice"],
        "required": false
      }
    }
  },
  "content_performance_targets": {
    "type": "object",
    "required": false,
    "properties": {
      "target_engagement_rate": {
        "type": "number",
        "minimum": 0,
        "maximum": 100,
        "description": "Expected engagement % (likes+comments+shares / impressions)"
      },
      "target_reach_per_post": {
        "type": "integer",
        "minimum": 100,
        "description": "Expected impressions per post"
      }
    }
  },
  "created_at": {
    "type": "string",
    "format": "ISO8601",
    "required": true
  },
  "updated_at": {
    "type": "string",
    "format": "ISO8601",
    "required": true
  },
  "version": {
    "type": "integer",
    "minimum": 1,
    "required": true,
    "description": "Persona version (increments on updates)"
  }
}
```

### Persona Validation Rules

1. **Voice consistency**: All generated content MUST match voice_tone
2. **Vocabulary enforcement**: Content MUST use preferred_words; MUST NOT use forbidden_words
3. **Platform compliance**: Post distribution matches platform_preferences weights
4. **Audience alignment**: Topics and language match target_audience
5. **Brand safety**: Never mention forbidden_associations; always include required_disclaimers if present

### Example: Fashion Influencer Persona

```json
{
  "agent_id": "fashion-influencer-001",
  "name": "Luna Styles",
  "bio": "Fashion curator discovering sustainable luxury for Gen Z",
  "voice_tone": "casual",
  "target_audience": {
    "age_range": "18-24",
    "demographics": ["students", "fashion_enthusiasts"],
    "interests": ["fashion", "sustainability", "luxury_brands"],
    "regions": ["global", "EU", "US"]
  },
  "vocabulary": {
    "preferred_words": ["slay", "serve", "aesthetic", "vibe", "iconic", "drip"],
    "forbidden_words": ["cheap", "old-fashioned", "outdated"],
    "jargon_level": "beginner"
  },
  "content_style": {
    "post_length_preference": "medium",
    "emoji_usage": "heavy",
    "hashtag_strategy": "mix_popular_niche",
    "media_preference": "videos",
    "storytelling_style": "narrative"
  },
  "engagement_strategy": {
    "goal": "viral",
    "call_to_action": "like_comment_share",
    "controversy_level": "moderate",
    "authenticity_weight": 0.8
  },
  "platform_preferences": {
    "twitter": 0.2,
    "tiktok": 0.8,
    "instagram": 0.7,
    "youtube": 0.4,
    "linkedin": 0.0
  },
  "brand_guidelines": {
    "colors": ["#FF6B9D", "#FFD700", "#FFFFFF"],
    "forbidden_associations": ["fast-fashion-brands", "environmental-offenders"],
    "required_disclaimers": ["#partner", "#ad"]
  },
  "values": {
    "core_values": ["sustainability", "inclusivity", "authenticity"],
    "causes_supported": ["environmental_protection", "fair_trade"]
  }
}
```

## State Machine & Workflow

Content flows through the following state machine:

### State Definitions

```
TREND_DETECTED
  └─> SEMANTIC_FILTER_PENDING
       ├─> REJECTED (relevance score < threshold)
       └─> ACCEPTED (relevance score ≥ threshold)
            └─> TASK_QUEUED
                 └─> CONTENT_GENERATION_PENDING
                      ├─> GENERATION_FAILED
                      └─> CONTENT_GENERATED
                           └─> VALIDATION_PENDING
                                ├─> VALIDATION_FAILED
                                └─> VALIDATION_PASSED
                                     └─> REVIEW_PENDING (if confidence < 0.8)
                                     └─> READY_TO_PUBLISH (if confidence ≥ 0.8)
                                          └─> APPROVAL_PENDING
                                               ├─> APPROVAL_REJECTED
                                               └─> APPROVAL_APPROVED
                                                    └─> PUBLISHING
                                                         ├─> PUBLISH_FAILED
                                                         └─> PUBLISHED
                                                              └─> DISTRIBUTION_TRACKING
```

### State Transition Rules

| From State | To State | Condition | Actor |
|-----------|----------|-----------|-------|
| TREND_DETECTED | SEMANTIC_FILTER_PENDING | Automatically triggered | System |
| SEMANTIC_FILTER_PENDING | REJECTED | relevance_score < threshold | Semantic Filter |
| SEMANTIC_FILTER_PENDING | ACCEPTED | relevance_score ≥ threshold | Semantic Filter |
| ACCEPTED | TASK_QUEUED | High-engagement trend (≥10k) | Planner |
| TASK_QUEUED | CONTENT_GENERATION_PENDING | Task assigned to Content Creator | Orchestrator |
| CONTENT_GENERATION_PENDING | GENERATION_FAILED | Timeout or LLM error | Content Creator |
| CONTENT_GENERATION_PENDING | CONTENT_GENERATED | Script + media generated | Content Creator |
| CONTENT_GENERATED | VALIDATION_PENDING | Automatically triggered | Judge |
| VALIDATION_PENDING | VALIDATION_FAILED | Safety check failed | Judge |
| VALIDATION_PENDING | VALIDATION_PASSED | All safety checks pass | Judge |
| VALIDATION_PASSED | REVIEW_PENDING | confidence_score < 0.8 | Judge |
| VALIDATION_PASSED | READY_TO_PUBLISH | confidence_score ≥ 0.8 | Judge |
| REVIEW_PENDING | APPROVAL_PENDING | Human reviewer sees flagged content | HITL |
| READY_TO_PUBLISH | APPROVAL_PENDING | Automatically queued for review | Judge |
| APPROVAL_PENDING | APPROVAL_REJECTED | Reviewer rejects content | Human |
| APPROVAL_PENDING | APPROVAL_APPROVED | Reviewer approves + signs token | Human |
| APPROVAL_REJECTED | CONTENT_GENERATION_PENDING | Retry with feedback | Orchestrator |
| APPROVAL_APPROVED | PUBLISHING | approval_token received | Distribution |
| PUBLISHING | PUBLISH_FAILED | Network error or platform rejected | Distribution |
| PUBLISH_FAILED | PUBLISHING | Retry with exponential backoff (max 3x) | Distribution |
| PUBLISHING | PUBLISHED | Post live on platform | Distribution |
| PUBLISHED | DISTRIBUTION_TRACKING | Monitor engagement metrics | Analytics |

### Valid Paths (Happy & Error Cases)

**Happy Path**:
```
TREND_DETECTED → ACCEPTED → TASK_QUEUED → CONTENT_GENERATED → VALIDATION_PASSED 
  → READY_TO_PUBLISH → APPROVAL_APPROVED → PUBLISHED → DISTRIBUTION_TRACKING
```

**Low-Confidence Path** (requires human approval):
```
TREND_DETECTED → ACCEPTED → TASK_QUEUED → CONTENT_GENERATED → VALIDATION_PASSED 
  → REVIEW_PENDING → APPROVAL_PENDING → APPROVAL_APPROVED → PUBLISHED
```

**Rejection Path** (with retry):
```
APPROVAL_PENDING → APPROVAL_REJECTED → CONTENT_GENERATION_PENDING (retry with feedback)
  → CONTENT_GENERATED → ... (loop back to validation)
```

**Failure Path** (early exit):
```
TREND_DETECTED → SEMANTIC_FILTER_PENDING → REJECTED (stop)
```

or

```
TASK_QUEUED → CONTENT_GENERATION_PENDING → GENERATION_FAILED → escalate to human
```

### Invalid Transitions (Prevented by Orchestrator)

- Cannot skip HITL review if confidence < 0.8
- Cannot publish without approval_token
- Cannot re-approve already-rejected content without regeneration
- Cannot transition from PUBLISHED back to earlier states

### SLA for Each State

| State | Max Duration | Action on Timeout |
|-------|--------------|------------------|
| SEMANTIC_FILTER_PENDING | 10s | Retry, then skip trend |
| CONTENT_GENERATION_PENDING | 45s | Fail and escalate |
| VALIDATION_PENDING | 5s | Assume requires_review=true |
| REVIEW_PENDING | 120s (2min) | Auto-escalate to supervisor |
| APPROVAL_PENDING | 120s (2min) | Auto-escalate to supervisor |
| PUBLISHING | 15s | Retry up to 3x, then queue for retry |

## API Contract Edge Cases & Validation Rules

### Data Quality Invariants

**Invariant 1: Engagement Score Calculation**
- Formula: `engagement_score = likes + (comments * 2) + (shares * 3)`
- Validation: Calculate independently and compare. Reject if difference > 0.01 (float tolerance).
- If negative: Clamp to 0 and log warning (data corruption detected).
- If zero: Accept; check decay_score to distinguish between "new post" vs "spam with no engagement".

**Invariant 2: Impressions Bounds**
- Formula: `impressions ≥ (likes + comments + shares)` must always hold.
- If violated: Log warning but accept data (impressions may be underreported by platform).
- Never reject on this; impressions can lag behind engagement counts.

**Invariant 3: Decay Score Monotonicity**
- Decay score only decreases or stays the same; never increases.
- If same trend detected twice, create NEW TrendData document with fresh decay_score = 1.0.
- Do not reuse old TrendData and reset decay—violates monotonic property.

### Handling Uncertain/Invalid Values

| Field | Invalid Case | Handling | Impact |
|-------|--------------|----------|--------|
| **sentiment** | Unknown to LLM | Use `"unknown"` (not in original enum) | Filter from high-confidence campaigns; escalate to human review |
| **sentiment** | Mixed opinions | Use `"mixed"` (new enum value) | Caution flag; may indicate controversial topic |
| **engagement_score** | Negative from platform | Clamp to 0; log data quality issue | Proceed with validation |
| **engagement_score** | Zero | Accept; normal for new posts | Distinguish from spam using decay_score |
| **timestamp** | In future | Reject; log clock skew (return HTTP 400) | Fail fast—timezone/system issue |
| **timestamp** | >30 days old | Accept; but mark as historical data | May not be actionable for real-time trends |
| **timestamp** | Naive (no timezone) | Reject; require explicit timezone | ISO8601 format mandatory (e.g., `...Z` or `...+02:00`) |
| **metadata.category** | Unclassifiable | Default to `"other"` | Non-fatal; grouping may be less precise |
| **metadata.hashtags** | Empty array | Accept; valid for news articles/corporate posts | Not all content has hashtags |
| **platform** | Unknown/typo | Reject (enum violation) | Fail fast—invalid platform |
| **decay_score** | Increased vs previous | Reject; monotonic property violation | Log and skip document |
| **trend_velocity** | Negative | Clamp to 0 (stale trend with declining engagement) | Treat as low-priority opportunity |

### Updated Sentiment Enum

Extend sentiment to handle real-world uncertainty:
```json
"sentiment": {
  "type": "string",
  "enum": ["positive", "neutral", "negative", "mixed", "unknown"],
  "required": true,
  "description": "Aggregated sentiment. 'unknown' = LLM confidence <0.7. 'mixed' = cluster has conflicting sentiments."
}
```

**Semantic Meanings**:
- `positive`: Majority sentiment favorable
- `neutral`: Informational or balanced tone
- `negative`: Majority sentiment unfavorable
- `mixed`: Cluster contains both positive/negative reactions (e.g., controversial announcement)
- `unknown`: LLM couldn't classify with sufficient confidence (>0.7)

### Validation Checklist for AI Implementation

When storing TrendData, verify:

- [ ] `engagement_score ≥ 0` (clamp to 0 if platform returns negative)
- [ ] `engagement_score = likes + (comments*2) + (shares*3)` (tolerance: 0.01)
- [ ] `impressions ≥ (likes + comments + shares)` (warn if violated, accept anyway)
- [ ] `timestamp` not in future (allow ±5 min for clock tolerance)
- [ ] `timestamp` not older than 30 days (warn for historical data)
- [ ] `timestamp` includes timezone (reject naive timestamps)
- [ ] `sentiment` is one of `[positive, neutral, negative, mixed, unknown]`
- [ ] `platform` is one of `[twitter, news, market, reddit, tiktok]`
- [ ] `decay_score ≥ previous_decay_score` for same trend (monotonic check)
- [ ] If `decay_score = 0` and `engagement_score = 0`, mark as expired (delete candidate)
- [ ] `geographic_origin` matches defined enum
- [ ] `metadata.hashtags` follows platform conventions (Twitter = `#tag`, others flexible)
- [ ] `metadata.category` defaults to `"other"` if unclassifiable

### Cross-Schema Validation

**TrendData → Task Creation**:
- If `confidence_score < 0.75` in Semantic Filter: Do NOT create Task (drop before ingestion).
- If `decay_score < 0.2`: Planner may de-prioritize (stale opportunity).
- If `engagement_score < engagement_threshold` (campaign-specific): Filter out.

**TrendData → Content Package**:
- Content Generator MUST reference valid `trend_id` from MongoDB.
- Content confidence_score should be influenced by input TrendData confidence.
- If TrendData sentiment = `"unknown"` or `"mixed"`: Content confidence_score ≤ 0.75 (triggers review).

## Database Architecture

### Design Decision: MongoDB + PostgreSQL Polyglot Pattern

**Core Principle**: Use the right tool for each data characteristic.

#### MongoDB: High-Velocity Temporal Data
Chimera uses MongoDB for trend data because:
- **Write Throughput**: Handles 10k+ inserts/sec without tuning (TrendData flows continuously from Perception System)
- **Schema Flexibility**: Trend documents vary by platform (Twitter mentions ≠ news articles); MongoDB accommodates structural variation
- **Time-Series Patterns**: TTL indexes auto-expire stale trends (7-day retention)
- **Stateless Queries**: Trends are write-once, read-once for task creation; minimal mutations
- **Horizontal Scaling**: Sharding by `platform` or `timestamp` distributes write load across nodes

#### PostgreSQL: Agent State & Business Logic
Chimera uses PostgreSQL for agent state because:
- **Consistency Guarantees**: ACID transactions prevent race conditions (e.g., double-spending wallet balance)
- **Relational Integrity**: Foreign keys enforce referential consistency (task → campaign → agent)
- **Complex Queries**: SQL handles multi-table joins (agent + campaigns + content drafts + reviews) efficiently
- **Mutable State**: Agent status transitions and content approval workflows require strong consistency
- **Audit Trail**: Native transaction logging for compliance and debugging

### Data Flow by System

```
PERCEPTION → INGESTION PATH (Write-Heavy, Sequential)
  MCP Resource (twitter://mentions/recent)
    ↓
  Semantic Filter (Gemini 3 Flash)
    ↓
  TrendData → MongoDB [trends collection] ✓ FAST WRITE
    ↓
  Redis Queue [TaskQueue]
    ↓
  Planner Agent reads MongoDB
    ↓
  Creates Task → PostgreSQL [tasks table] ✓ ACID

EXECUTION PATH (State-Heavy, Transactional)
  Planner → PostgreSQL [tasks, agent_state]
    ↓
  Worker executes task
    ↓
  Updates PostgreSQL [campaign_progress, content_drafts]
    ↓
  Human review gate
    ↓
  Publishes → PostgreSQL [audit_log] + MongoDB [execution_history]
```

### MongoDB Schema

**Collections**:

**trends**
```javascript
{
  trend_id: UUID,                    // Primary key
  data: TrendData,                   // Matches API contract schema
  analyzed_at: ISOString,            // Index for TTL
  used_in_content: [UUID],           // References to content_drafts (denormalized)
  source_resource: string,           // Which MCP resource created this
  platform: string,                  // Index: fast query by platform
  decay_score: number                // Index: filter fresh trends
}
```

**Indexes**:
```javascript
db.trends.createIndex({ "analyzed_at": 1 }, { expireAfterSeconds: 604800 })  // Auto-delete after 7 days
db.trends.createIndex({ "platform": 1, "decay_score": 1, "engagement.engagement_score": 1 })
db.trends.createIndex({ "metadata.category": 1 })
db.trends.createIndex({ "timestamp": 1 })  // For time-range queries
```

**execution_history**
```javascript
{
  execution_id: UUID,
  task_id: UUID,                     // FK reference to PostgreSQL
  agent_id: UUID,
  inputs: Object,
  outputs: Object,
  duration_ms: number,
  completed_at: ISOString,
  error: string (nullable)           // NULL if successful
}
```

### PostgreSQL Schema

**Core Tables**:

```sql
-- Agents and their operational state
CREATE TABLE agents (
  agent_id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  persona JSONB NOT NULL,
  status VARCHAR(20) CHECK (status IN ('active', 'paused', 'error')),
  wallet_address VARCHAR(255),
  version INT DEFAULT 1,             -- Optimistic locking for state conflicts
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Agent state (mutable, requires ACID)
CREATE TABLE agent_state (
  agent_id UUID PRIMARY KEY REFERENCES agents(agent_id) ON DELETE CASCADE,
  status VARCHAR(20) CHECK (status IN ('active', 'paused', 'error')),
  wallet_balance NUMERIC(18,8) NOT NULL DEFAULT 0,
  pending_tasks INT DEFAULT 0,
  last_execution TIMESTAMP,
  version INT DEFAULT 1,             -- Optimistic locking
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Campaigns
CREATE TABLE campaigns (
  campaign_id UUID PRIMARY KEY,
  agent_id UUID NOT NULL REFERENCES agents(agent_id),
  goal TEXT NOT NULL,
  budget NUMERIC(18,8) NOT NULL,
  status VARCHAR(20) DEFAULT 'active',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Tasks created from TrendData
CREATE TABLE tasks (
  task_id UUID PRIMARY KEY,
  campaign_id UUID NOT NULL REFERENCES campaigns(campaign_id),
  trend_id UUID NOT NULL,            -- Reference to MongoDB trend (denormalized for performance)
  status VARCHAR(20) DEFAULT 'pending',
  assigned_worker UUID REFERENCES agents(agent_id),
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);

-- Content drafts
CREATE TABLE content_drafts (
  content_id UUID PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES tasks(task_id),
  agent_id UUID NOT NULL REFERENCES agents(agent_id),
  data JSONB NOT NULL,              -- Matches Content Package Schema
  confidence_score NUMERIC(3,2),
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'published')),
  requires_review BOOLEAN DEFAULT TRUE,
  reviewed_by UUID REFERENCES agents(agent_id),
  reviewed_at TIMESTAMP,
  published_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Audit trail
CREATE TABLE audit_log (
  log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID REFERENCES agents(agent_id),
  action VARCHAR(100) NOT NULL,     -- e.g., 'content_published', 'wallet_debit'
  resource_type VARCHAR(50),        -- e.g., 'content_draft', 'transaction'
  resource_id UUID,
  details JSONB,
  timestamp TIMESTAMP DEFAULT NOW()
);

-- Indexes for query performance
CREATE INDEX idx_agent_status ON agent_state(status) WHERE status = 'active';
CREATE INDEX idx_campaign_agent ON campaigns(agent_id);
CREATE INDEX idx_task_campaign ON tasks(campaign_id);
CREATE INDEX idx_task_status ON tasks(status);
CREATE INDEX idx_content_status ON content_drafts(status);
CREATE INDEX idx_content_agent ON content_drafts(agent_id);
CREATE INDEX idx_audit_agent ON audit_log(agent_id, timestamp DESC);
```

### Critical Patterns

**Optimistic Locking** (prevent race conditions):
```sql
-- Agent attempts to update state
UPDATE agent_state 
SET wallet_balance = wallet_balance - 10,
    version = version + 1,
    updated_at = NOW()
WHERE agent_id = $1 AND version = $2
RETURNING version;

-- If no rows updated, conflict detected; retry with fresh version
```

**Denormalization for Performance**:
- `tasks.trend_id` references MongoDB (denormalized)
- Prevents expensive MongoDB-PostgreSQL joins on hot paths
- Risk: eventual consistency if MongoDB trend is deleted; mitigated by 7-day TTL + archival

**Foreign Key Constraints**:
```sql
-- All content must reference a valid task
ALTER TABLE content_drafts 
ADD CONSTRAINT fk_content_task 
FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE;
```

## Concurrency & Locking Specification

### Optimistic Locking Strategy

All mutable resources use **version-based optimistic locking** to prevent lost updates:

```sql
-- Agent state has version column
ALTER TABLE agent_state ADD COLUMN version INT DEFAULT 1;

-- Update requires version check
UPDATE agent_state 
SET status = $1, version = version + 1, updated_at = NOW()
WHERE agent_id = $2 AND version = $3
RETURNING version;

-- If no rows updated, conflict detected (version mismatch)
```

**When to use optimistic locking**:
- Low contention (few agents competing for same resource)
- Read-heavy workloads (version check cheap vs pessimistic lock)
- Distributed agents (can't hold locks across network)

**Conflict resolution**:
1. Client detects conflict (update returns 0 rows)
2. Client re-fetches resource with new version
3. Client retries operation with fresh version
4. Max 5 retries; if still failing, escalate to human

### Concurrency Rules by Resource

| Resource | Lock Type | Conflict Resolution | Max Retries |
|----------|-----------|-------------------|------------|
| **agent_state** | Optimistic (version) | Client re-fetch + retry | 5 |
| **content_drafts** | Optimistic (version) | Client re-fetch + retry | 5 |
| **tasks** | Row-level (status only) | Only status field locked | 3 |
| **campaigns** | Optimistic (version) | Client re-fetch + retry | 3 |
| **agent_state.wallet_balance** | Optimistic + transaction | ACID serializable isolation | 10 |

### Wallet Balance Updates (Critical Path)

Wallet operations require **SERIALIZABLE** isolation to prevent double-spending:

```sql
-- Start transaction with serializable isolation
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- Agent 1 and Agent 2 both try to debit from shared wallet
SELECT balance FROM agent_state WHERE agent_id = $1 FOR UPDATE;
-- This locks the row; other transactions wait

IF balance >= amount:
  UPDATE agent_state SET balance = balance - amount WHERE agent_id = $1;
  COMMIT;
ELSE:
  ROLLBACK;
  -- Return FIN_INSUFFICIENT_BALANCE error
```

### Concurrent Content Approval Idempotency

Multiple humans might approve same content simultaneously:

```sql
-- Approval is idempotent: first approval wins
UPDATE content_drafts
SET status = 'approved', 
    approved_by = $1, 
    approved_at = NOW(),
    version = version + 1
WHERE content_id = $2 
  AND status IN ('pending', 'review_pending')
  AND version = $3
RETURNING content_id, approved_by, approved_at;

-- If another approval already happened:
-- - Different approved_by recorded
-- - Status unchanged (already 'approved')
-- - Return error: PLAT_DUPLICATE_CONTENT (idempotent success)
```

### Rate Limiting & Backpressure

When concurrent requests exceed capacity:

```sql
-- Circuit breaker: track recent requests
CREATE TABLE request_rate_limit (
  agent_id UUID,
  window_start TIMESTAMP,
  request_count INT,
  PRIMARY KEY (agent_id, window_start)
);

-- Check rate before processing
SELECT request_count FROM request_rate_limit
WHERE agent_id = $1 AND window_start = CURRENT_HOUR;

IF request_count >= 100 THEN:
  RETURN HTTP 429 (Too Many Requests)
  RETURN json { retry_after: 60 }
ELSE:
  INCREMENT request_count
  PROCESS request
```

---

## SLA & Performance Targets

### Latency Targets (P50/P95/P99)

| Operation | P50 | P95 | P99 | Timeout |
|-----------|-----|-----|-----|---------|
| **Fetch trends** | 2s | 8s | 15s | 30s |
| **Semantic filter** | 500ms | 5s | 8s | 10s |
| **Generate content** | 8s | 25s | 40s | 45s |
| **Validate content** | 300ms | 2s | 4s | 5s |
| **Publish content** | 3s | 10s | 12s | 15s |
| **Get agent profile** | 100ms | 500ms | 1s | 2s |
| **Update agent state** | 200ms | 1s | 2s | 5s |
| **Debit wallet** | 2s | 8s | 10s | 10s |
| **OpenClaw heartbeat** | 5s | 15s | 25s | 30s |

### Throughput Targets

| Metric | Target | Status |
|--------|--------|--------|
| **Trends ingestion** | ≥10,000 trends/hour | Per MongoDB |
| **Content generation** | ≥50 posts/hour | Per Content Creator agent |
| **Publication rate** | ≥100 posts/hour | Per Distribution Manager |
| **Concurrent agents** | ≥10 agents without degradation | Load test required |
| **Vector search** | ≥1000 queries/min | Per Weaviate instance |
| **Wallet transactions** | ≥100 txs/min | Per blockchain |

### State SLAs

| State | Max Duration | Action on Timeout |
|-------|--------------|------------------|
| **SEMANTIC_FILTER_PENDING** | 10s | Retry; skip trend if persistent |
| **CONTENT_GENERATION_PENDING** | 45s | Fail; escalate to human |
| **VALIDATION_PENDING** | 5s | Assume requires_review=true |
| **REVIEW_PENDING** | 120s (2 min) | Auto-escalate to supervisor |
| **APPROVAL_PENDING** | 120s (2 min) | Auto-escalate to supervisor |
| **PUBLISHING** | 15s | Retry up to 3x |

### Database Performance Targets

| Query | Target Latency | Index Required |
|-------|---------------|--------------------|
| Get agent by agent_id | <100ms | PRIMARY KEY |
| List active agents | <500ms | INDEX (status) |
| Get recent trends (platform + decay) | <2s | COMPOSITE INDEX (platform, decay_score, timestamp) |
| Query content by status | <1s | INDEX (status) |
| Vector similarity search (1M vectors) | <500ms | Weaviate HNSW index |

### Availability Targets

- **Overall system uptime**: 99.5% (4.38 hours downtime/month)
- **API endpoints**: 99.9% uptime
- **MCP servers**: 99% uptime (brief outages acceptable with fallbacks)
- **Data persistence**: 99.99% durability (use multi-region replication)

### Capacity Planning

| Resource | Capacity | Growth Plan |
|----------|----------|------------|
| **MongoDB trends collection** | 50M documents (7 days * 10k/hr) | Auto-scale; oldest data archived |
| **PostgreSQL agents table** | 100k agents | Increase per year-over-year growth |
| **Weaviate vector DB** | 1M trend embeddings | Purge old embeddings monthly |
| **Redis (TaskQueue)** | 100k pending tasks | Auto-scale queue depth |
| **Agent state memory** | <1KB per agent | Negligible |

### Cost Targets

| Service | Monthly Cost Target | Constraint |
|---------|-------------------|-----------|
| **MongoDB** | $500 | 10k inserts/sec, 50M docs |
| **PostgreSQL** | $300 | 100k agents, ACID transactions |
| **Weaviate** | $200 | 1M vectors |
| **Redis** | $50 | Task queues + caching |
| **MCP servers (Twitter, News)** | $1000 | API calls + rate limits |
| **Coinbase AgentKit** | $200 | Wallet operations |
| **LLM (Gemini Flash)** | $2000 | Content generation + filtering |
| **Total** | ~$4,250/month | Scales with agent count |

### Monitoring & Alerting

Key metrics to monitor:

```
# Latency (histogram percentiles)
chimera_skill_duration_ms{skill, percentile}
  alert if P95 > 2x baseline

# Error rates
chimera_error_rate_5m{service, error_code}
  alert if > 5% for non-transient errors

# Concurrency
chimera_concurrent_requests{service}
  alert if approaching capacity limit

# Queue depth
chimera_task_queue_depth
  alert if > 10k tasks (processing slow)

# Database health
chimera_database_connection_pool{pool_type}
  alert if utilization > 80%

# Wallet balance anomalies
chimera_wallet_balance{agent_id}
  alert if rapid depletion (possible fraud)
```

---

## Integration Points

### MCP Servers Required

1. **social-media-mcp** - Fetch trends, publish content
2. **vector-db-mcp** - Store/query trend embeddings
3. **wallet-mcp** - Blockchain transactions (Coinbase AgentKit)

### Skills Required

1. **skill_fetch_trends** - Input: platform, limit. Output: Trend Data JSON
2. **skill_generate_content** - Input: Trend Data, Persona. Output: Content Package
3. **skill_publish_content** - Input: Content Package, approval_token. Output: post_id

## OpenClaw Integration

### Overview
Chimera agents will publish their availability and capabilities to the OpenClaw network, enabling discovery by other autonomous agents.

### Agent Profile Registration
Each Chimera agent maintains a profile in the OpenClaw directory:
```json
{
  "agent_id": {
    "type": "string",
    "format": "uuid",
    "required": true,
    "description": "Unique identifier matching PostgreSQL agents.agent_id"
  },
  "name": {
    "type": "string",
    "minLength": 3,
    "maxLength": 100,
    "required": true,
    "description": "Human-readable agent name"
  },
  "type": {
    "type": "string",
    "enum": ["content_creator", "trend_analyst", "distribution_manager", "judge", "orchestrator"],
    "required": true,
    "description": "Agent role in Chimera system"
  },
  "capabilities": {
    "type": "array",
    "items": {
      "type": "string",
      "enum": ["trend_analysis", "video_generation", "image_generation", "content_writing", "social_engagement", "budget_management", "quality_control"]
    },
    "required": true,
    "minItems": 1,
    "maxItems": 10,
    "description": "Declared capabilities for discoverability"
  },
  "availability": {
    "type": "string",
    "enum": ["active", "busy", "unavailable", "maintenance"],
    "required": true,
    "description": "Current operational status"
  },
  "pending_tasks": {
    "type": "integer",
    "minimum": 0,
    "required": true,
    "description": "Current task queue depth (for load-aware routing)"
  },
  "max_concurrent_tasks": {
    "type": "integer",
    "minimum": 1,
    "maximum": 100,
    "required": false,
    "default": 5,
    "description": "Maximum parallelism this agent supports"
  },
  "pricing": {
    "type": "object",
    "required": false,
    "properties": {
      "currency": {
        "type": "string",
        "enum": ["USDC", "ETH", "BASE"],
        "required": true
      },
      "rate_per_task": {
        "type": "number",
        "minimum": 0,
        "required": true,
        "description": "Cost per task execution in specified currency"
      },
      "rate_per_hour": {
        "type": "number",
        "minimum": 0,
        "required": false,
        "description": "Alternative hourly rate for long-running tasks"
      }
    }
  },
  "reputation_score": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "required": true,
    "description": "Agent quality metric (task_success_rate / total_tasks). Updated after each completion."
  },
  "uptime_24h": {
    "type": "number",
    "minimum": 0,
    "maximum": 100,
    "required": true,
    "description": "Percentage of last 24h the agent was operational"
  },
  "last_heartbeat": {
    "type": "string",
    "format": "ISO8601",
    "required": true,
    "description": "Last network heartbeat timestamp. Agents offline >4h are marked unavailable."
  },
  "supported_platforms": {
    "type": "array",
    "items": { "type": "string", "enum": ["twitter", "tiktok", "instagram", "youtube", "news"] },
    "required": false,
    "description": "Platforms this agent can operate on"
  }
}
```

### Agent Relay Protocol (ARP)
Chimera implements ARP to:
- Discover other content creators for collaboration
- Receive engagement requests from brand agents
- Share trend insights with research agents

### Heartbeat Mechanism
Every 4 hours, agent:
1. Fetches OpenClaw heartbeat file (markdown)
2. Executes instructions (post updates, respond to queries)
3. Reports status back to network

### Commercial Integration
When another agent requests services:
1. Chimera receives RFP via ARP
2. Orchestrator evaluates against current workload
3. Returns quote + availability
4. Executes work if accepted
5. Receives payment via wallet_mcp

## Security Considerations

### Zero Trust Model
- Every agent action is logged via MCP Sense
- No agent has direct shell access
- All external content is sanitized before processing

### Human Safety Layer
- Content with confidence < 0.8 requires human review
- Review must happen within SLA (2 minutes)
- All published content is cryptographically signed

### OpenClaw Security
- Heartbeat files are potential attack vectors
- Implement checksum verification
- Sandbox all executed instructions
- Rate limit network queries
