---
name: nw-signal-detection
description: Buying intent signal categories, scoring framework, data sources per signal type, and detection methods for identifying business changes and opportunities.
disable-model-invocation: true
---

# Signal Detection

## Signal Categories

Detect these signals during research and score each for actionability.

### Leadership Changes

| Signal | Indicates | Detection Method |
|--------|----------|-----------------|
| New C-level hire | Budget authority change, new strategic direction | WebSearch: `"{company}" new CTO OR CEO OR CFO OR CIO 2026` |
| Key departure | Instability, potential project restart | WebSearch: `"{company}" former OR leaves OR departs OR resignation` |
| New VP/Director | Specific initiative funding | WebSearch: `"{company}" VP OR "vice president" OR director hired OR joins` |
| Board change | Strategic shift, investor influence | SEC DEF 14A proxy statements, OpenCorporates officer changes |

### Financial Signals

| Signal | Indicates | Detection Method |
|--------|----------|-----------------|
| Funding round | Expansion budget, buying opportunity | WebSearch: `"{company}" funding OR raises OR series OR seed 2025 2026` |
| Acquisition (acquirer) | Integration needs, technology decisions | WebSearch: `"{company}" acquires OR acquisition` |
| Acquisition (target) | Potential disruption, new decision-makers | Same search from target perspective |
| IPO filing | Transparency, compliance needs | SEC EDGAR S-1 filings |
| Earnings beat/miss | Financial health indicator | SEC 10-Q, financial news |

### Growth Signals

| Signal | Indicates | Detection Method |
|--------|----------|-----------------|
| Hiring surge (>30% increase) | Growth, new initiative | WebSearch: `site:linkedin.com/jobs "{company}"` + compare over time |
| New job titles (first-ever) | Organizational restructuring | Watch for novel roles ("Head of AI", "VP Platform") |
| Office expansion (new cities) | Geographic growth | Job postings in new locations |
| New product launch | Technology decisions, budget allocation | News search, company blog |

### Technology Signals

| Signal | Indicates | Detection Method |
|--------|----------|-----------------|
| Tech stack change | Modernization budget, integration needs | WebSearch: `"{company}" migrating OR adopts OR switches to` |
| Engineering blog posts | Technical direction, hiring signals | WebFetch: `{domain}/blog` or `/engineering` |
| Open source activity | Technology investment, developer hiring | GitHub org activity |
| Patent filing | R&D direction, innovation area | USPTO/EPO search by assignee |

### Market Signals

| Signal | Indicates | Detection Method |
|--------|----------|-----------------|
| Competitor funding | Competitive pressure, may trigger spending | Crunchbase competitor monitoring |
| Regulatory change | Compliance needs, new requirements | Industry news, government sites |
| Partnership announcement | Strategic direction, ecosystem choices | News search, press releases |

## Signal Scoring Framework

Score each detected signal on three dimensions:

**Timing Score (0-1)**: How recent?
- Last 7 days: 1.0
- Last 30 days: 0.8
- Last 90 days: 0.5
- Last 180 days: 0.3
- Older than 180 days: 0.1
- Apply exponential decay with ~30-day half-life for precision

**Relevance Score (0-1)**: How relevant to our offering?
- Directly related to our product/service domain: 1.0
- Adjacent domain (related technology/industry): 0.6
- General business signal (funding, leadership): 0.4
- Tangentially related: 0.2

**Magnitude Score (0-1)**: How significant?
- Funding: >$50M = 1.0, $10-50M = 0.7, $1-10M = 0.5, <$1M = 0.3
- Executive: C-level = 1.0, VP = 0.7, Director = 0.5
- Hiring: >50 roles = 1.0, 20-50 = 0.7, 5-20 = 0.5, <5 = 0.3
- Tech change: Core platform = 1.0, Major tool = 0.7, Minor tool = 0.3

**Composite Score**: `(timing * 0.3) + (relevance * 0.4) + (magnitude * 0.3)`
- Score >= 0.7: High priority -- highlight in executive summary
- Score 0.4-0.7: Medium priority -- include in signals section
- Score < 0.4: Low priority -- mention briefly or omit

## Signal Output Format

```json
{
  "type": "funding_round",
  "description": "Series C: $45M led by Sequoia Capital",
  "detected_date": "2026-03-05",
  "signal_date": "2026-02-28",
  "timing_score": 0.8,
  "relevance_score": 0.6,
  "magnitude_score": 0.7,
  "composite_score": 0.69,
  "priority": "medium",
  "source": "crunchbase.com",
  "rating": "B2",
  "implication": "Company has fresh capital for technology investments. Good timing for outreach."
}
```

## Practical Detection Workflow

During Phase 3 (Execute Research), weave signal detection into the research flow:

1. During company research: note any news from last 90 days as potential signals
2. During person research: note job changes, new publications, speaking engagements
3. During relationship mapping: note investor activity, board changes
4. After all research: review collected signals, apply scoring framework
5. Rank by composite score, include top signals in executive summary
