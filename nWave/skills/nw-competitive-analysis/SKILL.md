---
name: nw-competitive-analysis
description: Porter's 5 Forces and SWOT analysis automation from public data sources, technology adoption analysis methods, and competitive landscape mapping.
disable-model-invocation: true
---

# Competitive Analysis

## When to Apply

Include competitive analysis in company dossiers when the business context is:
- Partnership evaluation (understand their competitive position)
- Sales preparation (understand their market pressures and buying triggers)
- Investment/M&A evaluation (understand market dynamics)

Skip for pure person-focused dossiers unless the person's company context is important.

## Porter's 5 Forces -- Data-Driven

| Force | Data Sources | What to Search |
|-------|-------------|---------------|
| **Threat of New Entrants** | Crunchbase (new startups), patent filings | WebSearch: `"{industry}" startup funding 2025 2026` |
| **Supplier Power** | Job postings (supply chain mentions), SEC 10-K filings | Look for supplier concentration mentions in annual reports |
| **Buyer Power** | G2/Capterra reviews, Glassdoor customer mentions | WebSearch: `site:g2.com "{company}"` or `site:capterra.com "{company}"` |
| **Threat of Substitutes** | Tech stack data, GitHub (open-source alternatives) | WebSearch: `"{company}" alternative OR competitor OR "open source"` |
| **Competitive Rivalry** | News, job postings, tech stack overlap | WebSearch: `"{company}" vs OR competitor OR "market share"` |

For each force, provide:
- Assessment: high/medium/low pressure
- Evidence: specific data points with sources
- Rating: Admiralty Code

## SWOT Analysis from Public Data

**Strengths** (positive internal):
- Technology stack modernity (from tech detection)
- Patent portfolio size and recency
- Funding position (total raised, recent round)
- Key talent (notable hires, team expertise)
- Employee sentiment (Glassdoor rating if available)

**Weaknesses** (negative internal):
- Technology debt signals (legacy tech in stack)
- Key departures (leadership turnover)
- Negative employee reviews (Glassdoor themes)
- Slow hiring in critical areas

**Opportunities** (positive external):
- Market growth trends (news, industry reports)
- Adjacent technology adoption (new capabilities)
- Geographic expansion signals (new office locations)
- Partnership ecosystem growth

**Threats** (negative external):
- Competitor funding rounds (well-funded competition)
- Regulatory changes (compliance requirements)
- Key customer concentration risk (SEC filing disclosures)
- Technology disruption (open-source alternatives gaining traction)

## Technology Adoption Analysis

When tech stack data is available, analyze:

1. **Stack modernity**: recent vs legacy technologies. A company running Node.js 20 + React 18 + Kubernetes is more modern than one on jQuery + Apache + bare metal.
2. **Cloud provider**: AWS, Azure, GCP, or on-prem. Cloud-native suggests different buying patterns.
3. **Development practices**: CI/CD tools (GitHub Actions, Jenkins), monitoring (Datadog, New Relic), security tools.
4. **AI/ML adoption**: presence of AI/ML frameworks, data platforms, LLM integrations.
5. **Migration signals**: mixed old/new tech suggests active modernization (buying trigger).

## Competitive Landscape Mapping

Output a simple competitor map:

```json
{
  "target_company": "TechCorp",
  "industry": "Enterprise SaaS",
  "competitors": [
    {
      "name": "Competitor A",
      "basis": "Direct competitor in same market segment",
      "funding": "$120M Series D",
      "differentiation": "AI-first approach",
      "source": "crunchbase.com",
      "rating": "B2"
    }
  ],
  "market_position": "Mid-market challenger with strong European presence",
  "competitive_pressure": "medium",
  "analysis_confidence": "medium"
}
```

## Output Integration

Competitive analysis appears in the company dossier under:
1. `competitive_landscape` array (competitors with basis and sources)
2. `risk_factors` array (competitive threats)
3. `opportunity_indicators` array (market opportunities)
4. Executive summary bullet (if competitive context is relevant to meeting)

Keep competitive analysis proportional to the dossier scope. For a quick profile, 2-3 competitors with basic positioning is sufficient. For a full dossier, include SWOT and Porter's assessment.
