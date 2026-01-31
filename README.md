# Gonzo Bot

Autonomous content engine for Demeter (demeterdata.ag).

## What This Does

Gonzo generates daily social media content by:
1. Researching agricultural news and priority industry voices
2. Driving browser conversations with Demeter's AI assistant (assistant.demeterdata.ag)
3. Turning those conversations into channel-ready social posts with data visualizations
4. Pushing drafts to a publishing queue for human review

## Current Status: Phase 0 MVP

The skeleton is complete and working end-to-end:
- ✅ Browser automation with Playwright to query Demeter AI
- ✅ Claude API integration for content generation
- ✅ Matplotlib chart generation with full brand specs
- ✅ JSON logging
- ✅ Stub phases for scan and publish

Phase 1 roadmap: Real web search, multiple conversations per run, Typefully API integration.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"

# Run
python orchestrator.py
```

## Output

- Posts saved to `output/` directory as JSON files
- Charts saved to `output/charts/` as PNG files
- Run logs saved to `logs/runs/` as JSON files

## Architecture

See `CLAUDE.md` for complete architecture, design decisions, and roadmap.

```
orchestrator.py          # Main entry point
├── phases/
│   ├── scan.py         # News scanning (stub for Phase 0)
│   ├── interrogate.py  # Browser automation with Demeter AI
│   ├── generate.py     # Claude API content generation
│   └── log.py          # Persistent logging
└── services/
    ├── browser.py      # Playwright wrapper
    ├── claude_api.py   # Anthropic API wrapper
    ├── charts.py       # Matplotlib chart generation
    └── publishing.py   # Typefully/Buffer integration (stub for Phase 0)
```

## Requirements

- Python 3.9+
- Anthropic API key (set via `ANTHROPIC_API_KEY` environment variable)
- Internet connection (for browser automation and API calls)

## Configuration

Edit `config.yaml` to customize:
- Output targets (daily minimum posts)
- Format mix (data snippets, rankings, deep dives, etc.)
- Brand colors and fonts
- Interaction limits
- Publishing settings

Edit `coverage_manifest.yaml` to define:
- Crops covered by Demeter
- Geographies covered
- Data types available
- Known strengths and gaps

## License

Proprietary - Demeter Data
