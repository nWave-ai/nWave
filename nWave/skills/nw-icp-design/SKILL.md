---
name: nw-icp-design
description: Ideal Customer Profile schema, signal catalog, scoring methodology, and Go-to-Market phase design for small teams
disable-model-invocation: true
---

# ICP Design

## ICP Schema (Machine-Readable)

Generate as YAML. Every field is a scoring dimension.

```yaml
icp:
  version: "1.0"
  product: "{product_name}"
  date: "{YYYY-MM-DD}"

  firmographics:
    industry:
      include: [list of target industries]
      exclude: [industries to avoid]
      weight: 0-10
    company_size:
      employees_min: number
      employees_max: number
      weight: 0-10
    revenue:
      annual_min: number  # EUR
      annual_max: number
      weight: 0-10
    geography:
      regions: [list]
      languages: [list]
      weight: 0-10
    stage:
      values: [startup, growth, mature, enterprise]
      weight: 0-10

  technographics:
    tech_stack:
      required: [technologies they must use]
      preferred: [technologies that indicate fit]
      disqualifying: [technologies that indicate misfit]
      weight: 0-10
    maturity:
      values: [early-adopter, mainstream, laggard]
      weight: 0-10
    tool_spend:
      annual_min: number
      weight: 0-10

  behavioral_signals:
    buying_signals:
      - signal: "description"
        source: "where to detect"
        weight: 0-10
    pain_indicators:
      - signal: "description"
        source: "where to detect"
        weight: 0-10
    engagement_signals:
      - signal: "description"
        source: "where to detect"
        weight: 0-10

  decision_maker:
    titles: [target titles]
    reports_to: [their manager's title]
    budget_authority: true/false
    pain_owner: true/false

  scoring:
    threshold_qualified: number  # minimum score to pursue
    threshold_ideal: number      # score for priority pursuit
    max_possible: number         # sum of all weights
    formula: "weighted sum of matching dimensions"

  disqualifiers:  # instant no-go regardless of score
    - "description of hard disqualifier"
```

## Signal Catalog

Behavioral signals that indicate a company matches your ICP. Organized by detection source.

```
PUBLIC SIGNALS (free to detect):
  Job postings:
    - Hiring for roles your product replaces/augments
    - Job descriptions mentioning your problem domain
    - Surge in engineering hiring (growth signal)

  Company announcements:
    - Funding round (budget available)
    - New CTO/VP Engineering (change agent)
    - Digital transformation initiative
    - Compliance deadline approaching

  Technology signals:
    - GitHub activity in relevant technologies
    - Stack adoption visible on job boards
    - Conference talks on related topics

  Content signals:
    - Blog posts about the problem you solve
    - Executives speaking at industry events
    - RFP/RFI published in your domain

ENGAGEMENT SIGNALS (from your own channels):
  High intent:
    - Visited pricing page (2+ times)
    - Downloaded technical whitepaper
    - Attended webinar AND asked question
    - Requested demo

  Medium intent:
    - Opened 3+ emails in sequence
    - Engaged with case study content
    - Connected on LinkedIn after event

  Low intent:
    - Newsletter subscriber
    - Single blog visit
    - Generic event attendance
```

## Scoring Methodology

```
FOR EACH PROSPECT COMPANY:

1. Score each dimension:
   Match = weight value (0-10)
   Partial match = weight x 0.5
   No match = 0
   Disqualifier present = DISQUALIFIED (skip scoring)

2. Calculate total:
   Total = sum of all dimension scores
   Percentage = Total / max_possible x 100

3. Classify:
   >= threshold_ideal    -> IDEAL (prioritize, allocate best resources)
   >= threshold_qualified -> QUALIFIED (pursue, standard process)
   < threshold_qualified  -> UNQUALIFIED (do not pursue)

4. Review quarterly:
   - Which scored-ideal companies converted? (validate model)
   - Which unexpected wins came from low scores? (missing signals)
   - Adjust weights based on closed-won analysis
```

## Go-to-Market Phases (Small Team)

For a 3-person company scaling from training/consulting to enterprise.

```
PHASE 1: FOUNDATION (Months 1-3)
  Goal: Validate ICP with first 5 paying customers
  Channel: Personal network, conference warm leads
  Pricing: Custom quotes, learn willingness-to-pay
  Team: All 3 founders doing sales + delivery
  Metrics: 5 customers, avg deal size, close rate

PHASE 2: REPEATABILITY (Months 4-8)
  Goal: Standardize offer, document sales process
  Channel: Content marketing + conference pipeline
  Pricing: Published tiers (Good/Better/Best)
  Team: 1 person focused on sales, 2 on delivery
  Metrics: Repeat purchase rate, referral rate, CAC

PHASE 3: SCALE (Months 9-18)
  Goal: Grow pipeline beyond personal network
  Channel: Inbound (content + SEO) + outbound (signal-based)
  Pricing: Self-serve Good tier + sales-led Better/Best
  Team: Consider first sales hire or partner channel
  Metrics: MRR growth, LTV:CAC, payback period

PHASE 4: ENTERPRISE (Months 18+)
  Goal: Land enterprise accounts
  Channel: ABM (Account-Based Marketing) for top 20 targets
  Pricing: Custom enterprise with annual contracts
  Team: Dedicated enterprise sales + customer success
  Metrics: ACV growth, net revenue retention, logo count
```

## Market Sizing Template

```
TAM (Total Addressable Market):
  Top-down: [Analyst report figure] x [% relevant to your category]
  Bottom-up: [Total companies matching ICP] x [ACV if all bought]
  Source requirement: cite analyst report + year

SAM (Serviceable Addressable Market):
  = TAM x (% you can technically serve)
  Factors: geography, language, integrations, compliance

SOM (Serviceable Obtainable Market) -- 3-year target:
  = SAM x (realistic market share %)
  Rule: <5% SAM in Year 3 is credible; >10% needs strong justification

VALIDATION:
  Compare SOM to revenue needed for business viability
  If SOM < viable revenue -> market too small or ACV too low
  If SOM >> target revenue -> credible, market exists
```

## Anti-Patterns

- ICP too broad ("any company with >50 employees") -- no targeting value
- ICP too narrow (addressable market < 100 companies) -- no growth room
- Scoring without validation against closed-won data
- Treating ICP as permanent (review quarterly)
- Confusing buyer persona with ICP (ICP = company, persona = person)
- Missing disqualifiers (wasting time on companies that will never buy)
