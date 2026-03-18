---
name: nw-dossier-templates
description: JSON schemas for Person and Company dossiers, Admiralty Code source rating framework, output format specifications, and executive summary generation guidelines.
disable-model-invocation: true
---

# Dossier Templates

## Admiralty Code Rating System

Rate every data point on two dimensions:

**Source Reliability** (who provided it):
- A = Completely reliable (official government registry, SEC filing, company's own website)
- B = Usually reliable (established news outlet, Crunchbase, official API)
- C = Fairly reliable (industry blog, review site, community database)
- D = Not usually reliable (unverified social media, anonymous source)
- E = Unreliable (known-inaccurate source)
- F = Cannot be judged (new/unknown source)

**Information Credibility** (how trustworthy is the specific claim):
- 1 = Confirmed (corroborated by 3+ independent sources)
- 2 = Probably true (corroborated by 2 independent sources)
- 3 = Possibly true (single credible source, consistent with other data)
- 4 = Doubtful (single source, not corroborated, some inconsistency)
- 5 = Improbable (contradicted by other evidence)
- 6 = Cannot be judged (insufficient basis for assessment)

Example ratings: A1 = government filing confirmed by multiple sources | B2 = Crunchbase data corroborated by news | C3 = single blog post, seems plausible | D4 = unverified LinkedIn claim

## Person Dossier Schema (JSON)

```json
{
  "meta": {
    "schema_version": "1.0",
    "generated_at": "ISO-8601 datetime",
    "generated_by": "nw-business-osint",
    "target_type": "person",
    "overall_confidence": "high|medium|low",
    "data_sources_count": 0,
    "knowledge_gaps_count": 0
  },
  "subject": {
    "name": "string",
    "current_role": "string",
    "current_company": "string",
    "location": "string|null",
    "email": "string|null",
    "rating": "A1-F6"
  },
  "career_timeline": [
    {
      "company": "string",
      "role": "string",
      "start": "YYYY-MM|null",
      "end": "YYYY-MM|null|current",
      "source": "string",
      "rating": "A1-F6"
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string|null",
      "field": "string|null",
      "year": "YYYY|null",
      "source": "string",
      "rating": "A1-F6"
    }
  ],
  "publications": [
    {
      "title": "string",
      "venue": "string",
      "year": "YYYY",
      "co_authors": ["string"],
      "doi": "string|null",
      "source": "string",
      "rating": "A1-F6"
    }
  ],
  "patents": [
    {
      "title": "string",
      "patent_number": "string",
      "filing_date": "YYYY-MM-DD",
      "co_inventors": ["string"],
      "source": "string",
      "rating": "A1-F6"
    }
  ],
  "speaking_engagements": [
    {
      "event": "string",
      "title": "string|null",
      "date": "YYYY-MM|null",
      "url": "string|null",
      "source": "string",
      "rating": "A1-F6"
    }
  ],
  "social_presence": {
    "linkedin_url": "string|null",
    "github": {
      "handle": "string|null",
      "public_repos": 0,
      "top_languages": ["string"],
      "organizations": ["string"],
      "rating": "A1-F6"
    },
    "twitter_handle": "string|null",
    "personal_website": "string|null"
  },
  "key_connections": [
    {
      "name": "string",
      "relationship": "string",
      "context": "string",
      "source": "string",
      "rating": "A1-F6"
    }
  ],
  "signals": [
    {
      "type": "string",
      "description": "string",
      "detected_date": "ISO-8601",
      "relevance_score": 0.0,
      "source": "string",
      "rating": "A1-F6"
    }
  ],
  "knowledge_gaps": [
    {
      "field": "string",
      "sources_tried": ["string"],
      "result": "string",
      "recommendation": "string"
    }
  ],
  "compliance": {
    "eu_data_subject": true,
    "gdpr_lia_applicable": true,
    "data_retention_recommendation": "6 months",
    "collection_date": "ISO-8601"
  }
}
```

## Company Dossier Schema (JSON)

```json
{
  "meta": {
    "schema_version": "1.0",
    "generated_at": "ISO-8601 datetime",
    "generated_by": "nw-business-osint",
    "target_type": "company",
    "overall_confidence": "high|medium|low",
    "data_sources_count": 0,
    "knowledge_gaps_count": 0
  },
  "company": {
    "name": "string",
    "legal_name": "string|null",
    "domain": "string|null",
    "industry": "string",
    "sub_industry": "string|null",
    "founded": "YYYY|null",
    "hq_location": "string",
    "employee_count": "string|null",
    "type": "public|private|startup|nonprofit",
    "rating": "A1-F6"
  },
  "financials": {
    "revenue": "string|null",
    "revenue_source": "string|null",
    "funding_total": "number|null",
    "last_funding_round": {
      "type": "string",
      "amount": "number|null",
      "date": "YYYY-MM|null",
      "lead_investor": "string|null",
      "source": "string",
      "rating": "A1-F6"
    },
    "public_filings": [
      {
        "type": "10-K|10-Q|8-K|DEF14A",
        "date": "YYYY-MM-DD",
        "url": "string",
        "key_findings": "string"
      }
    ]
  },
  "technology_stack": [
    {
      "technology": "string",
      "category": "string",
      "source": "string",
      "rating": "A1-F6"
    }
  ],
  "leadership": [
    {
      "name": "string",
      "role": "string",
      "since": "YYYY|null",
      "source": "string",
      "rating": "A1-F6"
    }
  ],
  "recent_news": [
    {
      "headline": "string",
      "source": "string",
      "date": "YYYY-MM-DD",
      "url": "string",
      "relevance": "string",
      "rating": "A1-F6"
    }
  ],
  "job_postings_analysis": {
    "total_openings_estimate": "number|null",
    "top_departments": ["string"],
    "tech_mentions": ["string"],
    "growth_signals": ["string"],
    "source": "string",
    "rating": "A1-F6"
  },
  "competitive_landscape": [
    {
      "competitor": "string",
      "basis": "string",
      "source": "string"
    }
  ],
  "signals": [],
  "risk_factors": ["string"],
  "opportunity_indicators": ["string"],
  "knowledge_gaps": [],
  "compliance": {
    "eu_company": true,
    "gdpr_applicable": true,
    "data_retention_recommendation": "12 months",
    "collection_date": "ISO-8601"
  }
}
```

## Markdown Dossier Format

```markdown
# {Subject Name} -- Intelligence Dossier

**Generated**: {date} | **Confidence**: {high/medium/low} | **Sources**: {count}

## Executive Summary

- {Key finding 1 -- most important for the upcoming meeting}
- {Key finding 2}
- {Key finding 3}
- {Signal or recent change worth noting}
- {Knowledge gap or caveat}

## {Sections vary by target type -- Person or Company}

### Current Position
...

### Career Timeline
| Period | Company | Role | Source | Rating |
|--------|---------|------|--------|--------|

### Key Connections
...

### Recent Signals
...

## Knowledge Gaps

| Area | Sources Tried | Result | Recommendation |
|------|--------------|--------|----------------|

## Data Sources

| Source | Data Points | Reliability | Last Accessed |
|--------|------------|-------------|---------------|

## Compliance Note

{EU data subject flag, LIA reference, retention recommendation}
```

## Executive Summary Guidelines

The executive summary is the most-read section. Write 3-5 bullets covering:
1. The single most important finding for the meeting context
2. Current role and company status (growth, funding, challenges)
3. Relevant professional background or expertise
4. Recent signals (job change, funding, M&A, hiring surge)
5. Biggest knowledge gap or caveat about the data

Keep each bullet to one sentence. Lead with the most actionable insight.
