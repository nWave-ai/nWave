---
name: nw-data-source-catalog
description: Complete catalog of OSINT data sources for business intelligence, organized by pipeline (people, company, relationship, digital footprint) with API details, pricing tiers, rate limits, and recommended query sequence.
disable-model-invocation: true
---

# Data Source Catalog

## Source Selection Principles

1. Free/open sources first, paid only if critical gaps remain
2. Highest data quality sources first within each tier
3. Respect rate limits -- never exceed published thresholds
4. Diversify sources to enable cross-referencing (3+ per major claim)

## Query Sequence by Pipeline

### Person Pipeline (recommended order)

| Priority | Source | Cost | What You Get | How to Query |
|----------|--------|------|-------------|-------------|
| 1 | Web search (name + company) | Free | Current role, recent news, public profiles | WebSearch: `"{name}" "{company}" site:linkedin.com OR site:github.com` |
| 2 | GitHub API | Free (5K req/hr auth) | Tech skills, repos, orgs, activity | WebFetch: `https://api.github.com/users/{handle}` (if handle known) |
| 3 | Semantic Scholar | Free (10 req/sec auth) | Publications, citations, h-index | WebFetch: `https://api.semanticscholar.org/graph/v1/author/search?query={name}` |
| 4 | USPTO PatentsView | Free | Patents, co-inventors | WebFetch: `https://api.patentsview.org/inventors/query?q={"inventor_last_name":"{last}"}` |
| 5 | YouTube Data API | Free (10K units/day) | Conference talks, presentations | WebSearch: `site:youtube.com "{name}" conference OR talk OR keynote` |
| 6 | Apollo.io | Free tier (limited) | Email, phone, enrichment | WebFetch: people enrichment endpoint (requires API key) |
| 7 | Hunter.io | 50 searches/mo free | Email pattern, verification | WebFetch: `https://api.hunter.io/v2/email-finder?domain={domain}&first_name={first}&last_name={last}` |

### Company Pipeline (recommended order)

| Priority | Source | Cost | What You Get | How to Query |
|----------|--------|------|-------------|-------------|
| 1 | Web search (company name) | Free | Overview, news, website | WebSearch: `"{company}" company overview funding technology` |
| 2 | Company website | Free | About, team, products, careers | WebFetch: `https://{domain}/about` and `/careers` or `/jobs` |
| 3 | OpenCorporates | Free (open data) | Registration, officers, filings | WebSearch: `site:opencorporates.com "{company}"` |
| 4 | SEC EDGAR | Free, no auth | 10-K, 10-Q, proxy statements (US public) | WebFetch: `https://efts.sec.gov/LATEST/search-index?q=%22{company}%22&dateRange=custom&startdt=2025-01-01` |
| 5 | Crunchbase | Web free / API paid | Funding, investors, acquisitions | WebSearch: `site:crunchbase.com "{company}"` |
| 6 | UK Companies House | Free API | UK company profiles, officers, filings | WebFetch: `https://api.company-information.service.gov.uk/search/companies?q={company}` |
| 7 | InfoCamere | Paid (Italy) | Italian registry, XBRL balance sheets | WebSearch: `site:registroimprese.it "{company}"` |
| 8 | Web search (tech stack) | Free | Technologies used | WebSearch: `"{company}" technology stack OR "built with" OR engineering blog` |
| 9 | Web search (job postings) | Free | Growth signals, tech needs, org structure | WebSearch: `"{company}" careers OR jobs site:linkedin.com OR site:greenhouse.io` |
| 10 | News search | Free | Recent developments, M&A, partnerships | WebSearch: `"{company}" news OR announcement OR funding 2026` |

### Relationship Pipeline (recommended order)

| Priority | Source | What to Extract |
|----------|--------|----------------|
| 1 | OpenCorporates officer search | Board interlocks -- same person serving on multiple company boards |
| 2 | SEC EDGAR proxy (DEF 14A) | Board composition, compensation, related-party transactions |
| 3 | Crunchbase investor data | Shared investors between companies (warm intro paths) |
| 4 | USPTO co-inventor data | Technical collaboration networks |
| 5 | Semantic Scholar co-author | Research collaboration networks |
| 6 | GitHub org membership | Co-contribution networks in open source |

## Source Details by Category

### People Enrichment

**Apollo.io**: Free tier available | REST API | 275M+ contacts | Email: 1 credit, phone: 5-8 credits | 70-80% email success rate | Bulk enrichment: 10 records/call
**Hunter.io**: 50 searches/mo free | REST API | Domain search (all emails at domain) | Email finder (name+domain) | Email verifier | Single credit pool since 2025
**ZoomInfo**: Enterprise ($15K-30K/yr) | 100M+ profiles | Premium quality but out of scope for Phase 1

### Company Registries

**OpenCorporates**: 200M+ companies globally | REST API v0.4.8 | Free for open data | Bellingcat-endorsed for investigative research
**UK Companies House**: Fully open data | REST + streaming API | Company profiles, officers, PSC (Persons with Significant Control)
**InfoCamere (Italy)**: API available | XBRL balance sheets mandatory since 2010 | Paid per-query or subscription
**SIRENE/INSEE (France)**: Free since 2017 | REST API | 30M+ establishments | SIREN/SIRET numbers
**SEC EDGAR**: Free, no auth | 10 req/sec | XBRL financial data | 30+ year history | Bulk ZIP archives nightly

### Financial Data

**SEC EDGAR**: Gold standard for US public companies | `data.sec.gov` REST + bulk | Company facts, submissions, XBRL
**Financial Modeling Prep**: 250 req/day free | From $14/mo | Global financial data, ratios
**Alpha Vantage**: 25 calls/day free (severely limited) | From $49.99/mo | Fundamentals, technicals

### Tech Stack Detection

**BuiltWith**: From $295/mo | 85K+ technologies | Historical data since 2007
**Wappalyzer**: 50 lookups/mo free | Broad categories | Real-time detection
**DetectZeStack**: From $15/mo | 7,200+ technologies | 60-90x cheaper than BuiltWith at volume
Practical: start with web search (`"{company}" tech stack engineering blog`), use Wappalyzer free tier for validation

### Publications and Patents

**Semantic Scholar**: Free, no key required for basic | 200M+ papers | 1 req/sec (unauth), 10/sec (auth)
**ORCID**: Free | REST API v3.0 | Researcher IDs, affiliations, works
**USPTO PatentsView**: Free | US patents, inventors, co-inventor networks
**EPO Open Patent Services**: Free with registration | European patents | 10 req/sec
**CrossRef**: Free | DOI metadata, journal articles

### News and Signals

**NewsAPI.org**: Free for dev (100 req/day, delayed) | 80K+ sources | Simple query syntax
**NewsData.io**: Free tier (200 credits/day) | 87K+ sources | 206 countries
**GNews**: Free (100 req/day) | Google News aggregation
**RSS feeds**: Free | Direct from outlets | Standard parsing

### Social and Digital Footprint

**GitHub API**: Free 5K req/hr (auth) | Profiles, repos, contributions, orgs | Richest free OSINT source for technical people
**Twitter/X API**: Free tier nearly useless (1,500 tweets/mo) | Basic $100/mo | Not recommended for Phase 1
**YouTube Data API**: Free (10K units/day) | Conference talks, product demos

## Key Limitations

- **LinkedIn**: Official API highly restricted. No open access to profile search. Third-party providers face legal risk (Proxycurl lawsuit Jan 2026). Use web search with `site:linkedin.com` for basic profiles.
- **EU private companies**: Financial data significantly harder than US public. InfoCamere (Italy) and Companies House (UK) are best. Other EU countries vary.
- **Speaking engagements**: No aggregated API exists. Combine YouTube search + conference website scraping + Sessionize.
- **Twitter/X**: Post-acquisition API pricing makes it impractical for research at free/low-cost tier.
- **WHOIS**: Post-GDPR, most EU registrars redact personal data. Historical data (pre-2018) via SecurityTrails may still be valuable.
