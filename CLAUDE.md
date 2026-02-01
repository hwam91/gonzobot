# Gonzo Bot - CLAUDE.md

## What This Is

Gonzo is an autonomous content engine for Demeter (demeterdata.ag), an agricultural data company. It generates daily social media content by:

1. Researching agricultural news and priority industry voices
2. Driving browser conversations with Demeter's AI assistant (assistant.demeterdata.ag)
3. Turning those conversations into channel-ready social posts with data visualisations
4. Pushing drafts to a publishing queue for human review

The human (marketing lead) reviews drafts and clicks approve or reject. That's their only job. Gonzo does everything else.

## Why This Exists

Demeter has great agricultural data and a capable AI assistant but near-zero public presence. The founding team needs:
- 1000+ AI assistant interactions per month (proves usage for fundraising)
- Daily content on LinkedIn and Twitter (builds authority)
- Systematic QA of the AI assistant (improves the product)
- A content pipeline that doesn't depend on humans being fast or available

## Architecture

```
gonzo/
├── CLAUDE.md                      # This file
├── config.yaml                    # Volumes, format mix, brand, experiments
├── coverage_manifest.yaml         # What Demeter covers (crops, geos, data types)
├── orchestrator.py                # Main entry point - cron calls this
├── phases/
│   ├── scan.py                    # DEPRECATED - now using Anthropic Web Search
│   ├── interrogate.py             # Phase 2: Playwright browser automation with Demeter AI
│   ├── generate.py                # Phase 3: Claude API - assessment + content generation
│   └── log.py                     # Phase 4: Persistent logging + capability map
├── services/
│   ├── claude_api.py              # Anthropic API wrapper (question gen w/ web search, assessment, content)
│   ├── browser.py                 # Playwright automation for Demeter AI conversations
│   ├── publishing.py              # Typefully/Buffer API client for draft queue
│   └── charts.py                  # Matplotlib chart generation with brand specs
├── prompts/
│   ├── question_generator.txt     # Search web + generate conversation plans (Sonnet w/ web search)
│   ├── response_assessor.txt      # Rate Demeter AI responses, identify gaps (cheap model)
│   ├── content_writer.txt         # Turn transcripts into posts + chart specs (good model)
│   └── weekly_synthesis.txt       # Summarise week's logs (cheap model)
├── logs/
│   ├── runs/                      # One JSON per run: YYYY-MM-DD-HHMM.json
│   ├── capability_map.json        # Persistent crop x geo x question_type ratings
│   └── topics_covered.json        # What's been covered recently (avoid repetition)
├── output/
│   └── charts/                    # Generated chart images, cleaned up after push
├── requirements.txt
└── tests/
```

## Run Cycle

```
cron (e.g. daily 06:00 UTC)
    │
    ▼
orchestrator.py
    │
    ├── 1. Load config.yaml, coverage_manifest.yaml
    ├── 2. Load recent logs, capability_map.json, topics_covered.json
    │
    ├── 3. CLAUDE API CALL #1: Question Generation (with Web Search)
    │      Model: claude-sonnet-4-20250514
    │      Tools: web_search_20250305 (Anthropic Web Search API via Brave)
    │
    │      Claude autonomously:
    │      - Searches for recent agricultural news in coverage areas
    │      - Reads full articles (not just headlines)
    │      - Follows leads with additional searches
    │      - Synthesizes information from multiple sources
    │      - Generates conversation plans based on research
    │
    │      Input: coverage manifest + recent topics + config
    │      Output: 3-5 conversation plans with topic, opening question, follow-ups
    │      Prompt: prompts/question_generator.txt
    │      Cost: ~5-10 searches @ $10/1000 = ~$0.10 per run
    │
    ├── 4. PHASE 2: interrogate.py
    │      For each conversation plan:
    │        - Playwright opens assistant.demeterdata.ag
    │        - Types opening question, waits for response (LONG timeouts - assistant can be slow)
    │        - Types pre-planned follow-ups, captures responses
    │        - Max 8 exchanges per conversation
    │        - Max 5 conversations per run
    │      Output: [{conversation_id, topic, exchanges: [{question, response}]}]
    │      No LLM needed. Pure browser automation.
    │
    ├── 5. CLAUDE API CALL #2: Response Assessment
    │      Model: claude-haiku-4-5-20251001 (cheap, this is classification)
    │      Input: conversation transcripts
    │      Output: quality ratings, strengths, weaknesses, data gaps per conversation
    │      Prompt: prompts/response_assessor.txt
    │
    ├── 5.5 [PHASE 1.5] FAO ENRICHMENT (when available)
    │      For each assessed conversation:
    │        - If global context would strengthen it → formulate FAO query
    │        - If Demeter AI had gaps the FAO might cover → formulate FAO query
    │      Query Vanna.ai HTTP API with formulated questions
    │      Output: FAO context to pass alongside transcripts into content generation
    │      Note: Skipped if Vanna/FAO not configured. Becomes redundant if FAO
    │      data is ingested into Demeter platform directly.
    │
    ├── 6. CLAUDE API CALL #3: Content Generation
    │      Model: claude-sonnet-4-20250514 (needs to write well)
    │      Input: transcripts + assessments + FAO context (if available) + scan context + config
    │      Output: channel-ready posts + chart specifications (JSON for charts.py)
    │      Prompt: prompts/content_writer.txt
    │
    ├── 7. CHART GENERATION: charts.py
    │      For each chart spec from API call #3:
    │        - Matplotlib renders with brand colours (config.yaml)
    │        - Saves to output/charts/
    │      No LLM needed.
    │
    ├── 8. PUBLISH: publishing.py
    │      Push each post + chart image to Typefully (or Buffer) as draft
    │      All drafts. Human approves/kills from Typefully UI.
    │
    └── 9. LOG: log.py
           - Write run log to logs/runs/
           - Update capability_map.json with new ratings
           - Update topics_covered.json
           - If Friday: CLAUDE API CALL #4 (weekly synthesis, cheap model)
```

## Key Design Decisions

### Browser automation for Demeter AI (not MCP/API)
The Demeter AI assistant is web-based at assistant.demeterdata.ag. It has an MCP endpoint but that sits behind the system prompt, so you don't get the rich conversational interaction needed. Playwright drives a real browser session: navigate, type, wait, extract response text.

IMPORTANT: The assistant can be slow. Use generous timeouts (60-120 seconds per response). Build in retry logic for timeouts.

### Pre-planned follow-ups (Phase 1, upgrade later)
Conversation plans include pre-written follow-up questions generated before the browser session starts. This is simpler and cheaper than making adaptive API calls mid-conversation. The tradeoff is less natural conversations. Upgrade path: after each Demeter AI response, make a small Claude API call to decide the next question based on what was actually said.

### Three separate API calls (not one mega-call)
Question generation, response assessment, and content writing are separate calls because:
- Assessment runs on a cheap model (Haiku) - it's classification, not creative
- Content writing runs on a better model (Sonnet) - it needs to write well
- Separation makes debugging easier
- Each call has focused context rather than one massive prompt

### Persistent logging across runs
Gonzo needs memory between runs to:
- Avoid covering the same topic three days running
- Follow up on flagged items from previous runs
- Track capability map evolution over time
- Generate meaningful weekly syntheses

JSON files on disk are fine for v1. No database needed.

### Anthropic Web Search for news research
**Current implementation (Phase 1):** Uses Anthropic's native web search capability (`web_search_20250305` tool) during question generation. Claude autonomously researches agricultural news, reads full articles, follows leads, and synthesizes information before generating conversation plans.

**Benefits over DuckDuckGo scan approach:**
- Claude reads full articles, not just headlines/snippets
- Agentic behavior: Claude decides what to search and follows leads
- No separate scan phase needed - simpler architecture
- No rate limiting issues
- Better question quality from fuller context
- Cost: ~$0.10 per run (~5-10 searches @ $10/1000)

**Future upgrade for Phase 3+:** Priority account monitoring (LinkedIn/Twitter) could be added as a separate scan phase to surface posts from key industry voices (FAO, USDA, Almond Board, etc.). This would complement Claude's autonomous news research.

## Roadmap

### Phase 0: Skeleton (build this first)
Get the loop working end-to-end with minimal functionality:
- orchestrator.py loads config, calls phases in sequence
- scan.py is a STUB that returns empty results
- interrogate.py drives ONE conversation with Demeter AI (Playwright)
- generate.py makes ONE Claude API call to turn transcript into ONE LinkedIn post with chart spec
- charts.py renders the chart with brand colours (matplotlib, full brand specs from config)
- publishing.py prints output to console and saves post + chart image to output/ (no Typefully yet)
- log.py writes a JSON file

Chart generation is included in the MVP because it's the highest-leverage automation: charts are extremely time-consuming for humans and instant for computers. Every data-driven post should ship with a visual from day one.

Success = you can run `python orchestrator.py` and get a LinkedIn post draft + branded chart image saved to output/, based on a real conversation with the Demeter AI.

### Phase 1: Core Loop ✅ COMPLETE
- Question generation uses Anthropic Web Search to autonomously research news
- interrogate.py handles multiple conversations with proper error handling and timeouts
- Response assessment filters out low-quality conversations before content generation
- generate.py produces posts for Twitter AND LinkedIn with chart specifications
- Multiple chart types supported (horizontal bar, line, table)
- log.py maintains capability_map.json and topics_covered.json across runs
- Charts render with full brand specifications

Success = daily cron produces 2 Twitter drafts + 1 LinkedIn draft with charts, saved to output/ directory.

### Phase 1.5: FAO Enrichment
Add a second data source via Vanna.ai querying FAO's FAOSTAT database. This serves two purposes:

**A) Adding macro context to Demeter's granular data**
Demeter AI returns regional/crop-level detail. FAO provides the global picture. Content that combines both is stronger: "California almond yields dropped 4% while global production hit a record 1.6M tonnes" tells a story that neither source tells alone.

**B) Filling gaps where Demeter can't answer**
When Demeter AI gives a weak or empty response, the FAO may have relevant data at a higher level - particularly for global production volumes, trade flows, and producer prices (a domain Demeter doesn't currently cover well).

Architecture: After Phase 2 (Demeter AI conversations), a new step runs:
1. For each conversation transcript, a cheap Claude API call determines:
   - Would global/macro context strengthen this? If yes, formulate a FAO query.
   - Did Demeter AI fail to answer something the FAO might cover? If yes, formulate a FAO query.
2. Query Vanna.ai (HTTP API) with the formulated questions
3. FAO results are passed alongside Demeter transcripts into the content generation API call

FAO datasets to prioritise:
- Production / Crops and livestock products (global volumes by country/year)
- Trade / Crops and livestock products (import/export flows)
- Prices / Producer Prices (farm gate prices globally)
- Food Balances (supply/demand)

Setup: Download FAOSTAT bulk CSVs, load into SQLite or Postgres, point Vanna.ai at it. ~15 minutes for basic setup.

Note: If the Demeter team ingests FAO data into the main platform, this separate Vanna interface becomes redundant and this phase simplifies to Gonzo just asking Demeter AI better questions that draw on the now-ingested FAO data.

Success = content posts that combine Demeter's granular regional data with FAO's global context, or that recover useful content from conversations where Demeter AI alone came up short.

### Phase 2: Publishing Pipeline
- Integrate Typefully (or Buffer) API
- Drafts land directly in publishing queue with images attached
- Human reviewer sees ready-to-publish posts

Success = marketing lead opens Typefully each morning and sees a queue of drafts to approve.

### Phase 3: Intelligence
- News scanning considers priority accounts
- Coverage rotation is informed by topics_covered.json
- Weekly synthesis runs on Fridays
- Performance feedback loop (marketing lead notes what worked in a file, Gonzo reads it)

### Phase 4: Upgrades (future)
- Adaptive follow-ups (Claude API call mid-conversation based on actual responses)
- Social monitoring API integration (LinkedIn/Twitter/newsletter aggregation)
- Blog post generation (longer form, multiple charts)
- Richer chart types (maps, multi-series)
- Notion integration for logging/dashboard

## Config Reference (config.yaml)

```yaml
# Output targets
output:
  daily_minimum:
    twitter: 2
    linkedin: 1
  weekly:
    blog_posts: 1

# Format mix (percentages, sum to 100)
# data_snippet: single data point + factual context, NO editorial opinion
# ranking_league_table: ordered comparison, chart REQUIRED
# deep_dive: extended analysis, ~weekly
# news_reactive: responds to news with Demeter data
# question_to_audience: data point that raises a question
format_mix:
  data_snippet: 40
  ranking_league_table: 30
  deep_dive: 10
  news_reactive: 10
  question_to_audience: 10

# Override format mix for experiments
active_experiment: null
# Example:
# active_experiment:
#   name: "Rankings Sprint"
#   start_date: 2025-02-01
#   end_date: 2025-02-14
#   format_mix_override:
#     ranking_league_table: 50
#     data_snippet: 25
#     deep_dive: 10
#     news_reactive: 10
#     question_to_audience: 5

# Interaction limits per run
interaction_limits:
  max_exchanges_per_conversation: 8
  max_conversations_per_run: 5

# Channel specs
channels:
  twitter:
    max_characters: 280
    max_thread_tweets: 4
  linkedin:
    max_characters: 3000
  blog:
    target_words: 800-1500

# Brand
brand:
  colours:
    primary_gold: "#E8C07D"
    primary_dark_brown: "#47403F"
    secondary_linen: "#F7EFE4"
    secondary_light_blue: "#CADAE8"
    white: "#FFFFFF"
    text: "#1A1A1A"
  font: "Roboto"
  image_sizes:
    twitter: [1200, 675]
    linkedin: [1200, 1200]

# Priority accounts to monitor (Gonzo web-searches for recent activity)
priority_accounts:
  linkedin:
    - "FAO"
    - "Rabobank Food & Agribusiness"
    - "AgFunder"
  twitter:
    - "@FAO"
    - "@USDAForeignAg"

# Demeter AI
demeter_ai:
  url: "https://assistant.demeterdata.ag"
  response_timeout_seconds: 120
  access_method: "playwright"

# Publishing queue
publishing:
  service: "typefully"
  api_key: ""
  auto_schedule: false
  default_status: "draft"

# Logging
logging:
  runs_dir: "logs/runs"
  capability_map: "logs/capability_map.json"
  topics_covered: "logs/topics_covered.json"
  weekly_synthesis_day: "Friday"

# Performance feedback (updated manually by marketing lead)
performance_feedback:
  location: "logs/performance_notes.txt"
```

## Coverage Manifest (coverage_manifest.yaml)

This defines what Demeter actually covers. Gonzo uses this to:
- Filter news (only react to topics within coverage)
- Generate relevant questions
- Assess whether Demeter AI should have been able to answer

```yaml
# Update this as Demeter's coverage expands
crops:
  - almonds
  - olives
  - pistachios
  - walnuts
  - citrus
  - avocados
  - table_grapes
  - wine_grapes

geographies:
  - California
  - Spain
  - Portugal
  - Italy
  - Australia
  - Chile
  - Turkey
  - Tunisia

data_types:
  - production_volume
  - acreage_and_plantings
  - yield_per_acre
  - water_availability_and_allocation
  - cost_of_production
  - price_trends
  - trade_flows
  - processing_infrastructure
  - weather_and_growing_conditions
  - investment_activity

# Strongest coverage (prioritise for content)
strengths:
  - "California almonds: comprehensive acreage, yield, water, pricing"
  - "DASI index: daily California almond conditions"
  - "Spanish olives: production, pricing, export data"
  - "Australian almonds: production and trade flows"

# Known gaps (avoid or flag when encountered)
known_gaps:
  - "Turkish hazelnuts: limited data"
  - "South American wine: partial coverage"
  - "Processing cost breakdowns: sparse"
```

## Brand Voice (for content generation prompts)

### Do
- Lead with data, always
- State things plainly: "yields fell 12%" not "yields experienced a significant decline"
- Use comparisons: "roughly the output of the entire Australian almond industry"
- Acknowledge limits: "the data shows X, though we don't have visibility into Y"
- Credit sources including Demeter
- Treat agriculture as serious global infrastructure

### Don't
- Editorialise in data posts. No "finally", "surprisingly", "worryingly". Present the data.
- Corporate language: "excited to share", "leverage", "synergy"
- Emojis (none, ever)
- Hashtags (none, ever)
- Press release voice: "Demeter, the leading agricultural data provider"
- Pretend certainty where there is none
- Name competitors
- "Disrupting" or "revolutionising"
- "Genuinely", "honestly", "frankly"

### By channel
- Twitter: Concise, direct. Visual does the work. Threads only when genuinely needed.
- LinkedIn: Professional, analytical. Hook first, no preamble.
- Blog: Authoritative. Show your working. Build a picture.

### Data snippet example (the primary format)
GOOD: "California's almond-bearing acreage dropped 4% YoY in 2024 - the first decline in a decade. Five years ago it was growing at 8% annually. Source: Demeter."
BAD: "California's almond-bearing acreage dropped 4% YoY - water costs are finally showing up in planting decisions." (Editorial. You don't know that from the data point alone.)

### Ranking example
"Top 10 almond-producing regions globally, ranked by yield per hectare. The gap between first and tenth is 3.2x. [chart] Source: Demeter platform data, 2024 season."

### Question to audience example
"Australian almond exports to India grew 40% last year while every other destination was flat or down. Structural shift or one-off price arbitrage?"
NOT: "Australian almond exports to India grew 40% last year. Genuinely curious what traders are seeing." (Performative.)

## Chart Generation Specs

Brand colours for matplotlib:
```python
BRAND = {
    "primary_gold": "#E8C07D",
    "primary_dark_brown": "#47403F",
    "secondary_linen": "#F7EFE4",
    "secondary_light_blue": "#CADAE8",
    "white": "#FFFFFF",
    "text": "#1A1A1A",
    "chart_palette": [
        "#47403F", "#E8C07D", "#CADAE8",
        "#8B7D6B", "#A3B8C8", "#D4C4A8"
    ]
}
```

Rules:
- Title states the INSIGHT: "Spain produces 45% of EU olive oil" not "EU Olive Oil Production"
- Y-axis from zero unless justified
- No 3D, no pie charts (use horizontal bar instead)
- Source attribution at bottom of every chart
- Clean, minimal, no chartjunk
- Font: Roboto (install via matplotlib font manager)
- Twitter: 1200x675px
- LinkedIn: 1200x1200px
- Background: white (#FFFFFF) or linen (#F7EFE4)

### Chart Spec Schema

The content generation API call (Claude API call #3) returns structured JSON. Each post may include a `chart` field. The `chart` field must conform to this schema so `charts.py` can render it reliably.

`charts.py` receives the chart spec + brand config from config.yaml, renders with matplotlib, saves the PNG, and returns the file path. `generate.py` orchestrates this: it parses the API response, finds any posts with a `chart` field, calls `charts.py` for each, and attaches the resulting image path to the post.

```json
{
  "posts": [
    {
      "channel": "linkedin | twitter | blog",
      "copy": "The post text, fully formatted for the channel.",
      "format_type": "data_snippet | ranking_league_table | deep_dive | news_reactive | question_to_audience",
      "trigger": "news | systematic | priority_voice",
      "chart": {
        "type": "horizontal_bar | vertical_bar | line | table",
        "title": "Insight-led title, e.g. Spain produces 45% of EU olive oil",
        "subtitle": "Optional subtitle for additional context",
        "data": {
          "labels": ["Label 1", "Label 2", "Label 3"],
          "values": [45.0, 23.0, 12.0],
          "series_name": "Optional - used for axis label or legend"
        },
        "source": "Demeter | Demeter platform data | USDA NASS | etc.",
        "size": [1200, 1200],
        "highlight_index": null
      }
    }
  ]
}
```

#### Chart type details

**horizontal_bar** (primary chart type - use for rankings, comparisons)
```json
{
  "type": "horizontal_bar",
  "title": "Top 10 Almond-Producing Regions by Yield per Hectare",
  "data": {
    "labels": ["Region A", "Region B", "Region C"],
    "values": [3.2, 2.8, 2.1],
    "series_name": "Yield (tonnes/ha)"
  },
  "source": "Demeter platform data, 2024 season",
  "size": [1200, 1200],
  "highlight_index": 0
}
```
- `labels`: Category names, ordered as they should appear (top to bottom)
- `values`: Corresponding numeric values
- `highlight_index`: Optional int - index of bar to highlight in primary_gold, rest in primary_dark_brown

**vertical_bar** (use for comparing a small number of categories or time periods)
```json
{
  "type": "vertical_bar",
  "title": "California Almond Acreage Change by Year",
  "data": {
    "labels": ["2020", "2021", "2022", "2023", "2024"],
    "values": [8.1, 6.3, 3.2, 0.5, -4.0],
    "series_name": "YoY Change (%)"
  },
  "source": "Demeter",
  "size": [1200, 675],
  "highlight_index": 4
}
```
- Same structure as horizontal_bar
- Negative values should render below axis in a distinct shade
- `highlight_index`: Optional, highlights one bar

**line** (use for trends over time with many data points)
```json
{
  "type": "line",
  "title": "DASI Index: California Almond Conditions, 2024 Season",
  "data": {
    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    "values": [72, 68, 71, 65, 58, 62],
    "series_name": "DASI Index"
  },
  "source": "Demeter DASI",
  "size": [1200, 675],
  "highlight_index": null
}
```
- Line in primary_gold, markers at each data point
- Optional: if `comparison_values` is present, render a second line (e.g. prior year)
```json
{
  "data": {
    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    "values": [72, 68, 71, 65, 58, 62],
    "comparison_values": [70, 72, 74, 71, 69, 67],
    "series_name": "2024",
    "comparison_series_name": "2023"
  }
}
```
- Primary series in primary_gold, comparison in secondary_light_blue

**table** (use for multi-dimensional data or league tables with several columns)
```json
{
  "type": "table",
  "title": "Almond Production: Key Regions Compared",
  "data": {
    "columns": ["Region", "Acreage (ha)", "Yield (t/ha)", "Production (kt)"],
    "rows": [
      ["California", "640,000", "2.8", "1,792"],
      ["Australia", "55,000", "3.1", "170"],
      ["Spain", "750,000", "0.3", "225"]
    ]
  },
  "source": "Demeter platform data",
  "size": [1200, 1200],
  "highlight_index": 0
}
```
- Render as a clean styled table image (not HTML)
- Header row in primary_dark_brown with white text
- Alternating row shading: white and secondary_linen
- `highlight_index`: Optional int - index of row to highlight

#### charts.py rendering rules

1. Parse the chart spec JSON
2. Read brand colours and font from config.yaml
3. Set figure size from `spec["size"]` (pixels, convert to inches at 150 DPI)
4. Render chart type per spec
5. Apply:
   - Title: Roboto Bold, primary_dark_brown, top-aligned
   - Subtitle (if present): Roboto Regular, smaller, lighter
   - Source: Roboto Regular, small, bottom-right, grey
   - Grid: Light, horizontal only, behind data
   - Spines: Remove top and right. Left and bottom in light grey.
   - Background: white or secondary_linen
6. Save as PNG to output/charts/{run_id}_{post_index}.png
7. Return file path

#### Content generation prompt must specify

The prompt in `prompts/content_writer.txt` must instruct the model to:
- Return valid JSON conforming to the schema above
- Always include a `chart` field for data_snippet and ranking_league_table posts
- Use `horizontal_bar` as the default chart type for rankings
- Use `line` for time series data
- Use `table` when there are 3+ dimensions to show
- Make chart titles insight-led, never just descriptive
- Include source attribution in every chart spec
- Set `size` to match the target channel's image dimensions from config
- Set `highlight_index` when one data point is the focus of the post

## Environment Setup

```bash
# Python dependencies
pip install anthropic playwright matplotlib pyyaml duckduckgo-search requests

# Playwright browser
playwright install chromium

# Font (for charts)
# Download Roboto from Google Fonts, install to system or matplotlib font dir
```

## Running

```bash
# Manual run
python orchestrator.py

# Cron (daily at 06:00 UTC)
0 6 * * * cd /path/to/gonzo && python orchestrator.py >> logs/cron.log 2>&1
```

## Implementation Notes

### Playwright and Demeter AI
The Demeter AI assistant at assistant.demeterdata.ag is a web-based chat interface. Playwright needs to:
1. Navigate to the URL
2. Find the chat input field
3. Type a question
4. Wait for the response to complete (watch for loading indicators or response text to stop changing)
5. Extract the response text
6. Repeat for follow-ups
7. Start a new conversation for the next topic

The assistant can be SLOW. Use timeouts of 120+ seconds. Build retry logic. If a conversation fails mid-way, log what you got and move on.

The exact DOM selectors will need to be determined by inspecting assistant.demeterdata.ag. This is the most brittle part of the system. If the UI changes, selectors break. Keep selector definitions in one place (browser.py) for easy updates.

### Anthropic Web Search integration
**Enabled in Phase 1.** The question generation API call includes `tools=[{"type": "web_search_20250305"}]`, which gives Claude access to Brave Search via Anthropic's web search tool.

**How it works:**
1. `prompts/question_generator.txt` instructs Claude to search for recent agricultural news before generating conversation plans
2. Claude autonomously decides what to search for, reads full articles, and follows leads
3. Web search results inform conversation plan generation
4. Each search costs ~$0.01 (part of $10/1000 searches pricing)

**No separate news scan phase needed.** The deprecated `phases/scan.py` (DuckDuckGo implementation) is retained in codebase for reference but not used.

### Typefully API
Typefully has a REST API for creating drafts. Verify:
- Can create drafts with text + image attachment
- Can tag/label drafts (for format type tracking)
- Supports both Twitter and LinkedIn

If Typefully API is insufficient, Buffer is the fallback. Both support programmatic draft creation.

### Model selection
- Question generation: claude-sonnet-4-20250514 (needs strategic thinking)
- Response assessment: claude-haiku-4-5-20251001 (classification task, keep cheap)
- Content writing: claude-sonnet-4-20250514 (needs to write well within brand voice)
- Weekly synthesis: claude-haiku-4-5-20251001 (summarisation, keep cheap)

### Cost estimation
Per daily run (Phase 1):
- 1 Sonnet call for question generation (~2K input, ~1K output): ~$0.01
- Web search (5-10 searches @ $10/1000): ~$0.10
- 1 Haiku call for assessment (~3K input, ~500 output): ~$0.005
- 1 Sonnet call for content generation (~4K input, ~2K output): ~$0.02
- **Total: ~$0.13-0.15 per run, ~$4-5 per month**
- Plus occasional Haiku calls for weekly synthesis: ~$0.005 each

The web search adds ~$3/month vs the old DuckDuckGo approach, but delivers significantly better output quality through:
- Full article context instead of headline snippets
- Agentic research behavior (Claude follows leads)
- No rate limiting issues
- Simpler architecture (one less phase)

This cost is negligible for the value delivered.
