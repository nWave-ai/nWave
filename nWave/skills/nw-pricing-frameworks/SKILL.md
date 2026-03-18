---
name: nw-pricing-frameworks
description: Hybrid margin-safe pricing (Base Floor + Value Capture + Success Fee), Good/Better/Best tiering, Cialdini anchoring, Ackerman deal structuring, unit economics, consulting-specific models
disable-model-invocation: true
---

# Pricing Frameworks

## Hybrid Margin-Safe Pricing (Consulting Services)

Default for consulting/professional services. Guarantees positive margins while pricing on value.

**The problem with pure value-based pricing**: Setting price at X% of client value ignores delivery cost. When value is low relative to effort (diagnostics, assessments), margins go negative. When value is high relative to effort (audits scaling across many people), prices become unacceptably high.

**Solution: differentiated formula by engagement type.**

```
FORMULA:
  Price = max(Cost x Multiplier, Cost + ValueCapture% x ClientValue)

  Where Multiplier and ValueCapture% vary by engagement type:

  DIAGNOSTICS (low-risk entry points):
    Price = Cost x 1.5
    Rationale: fixed 33% margin. Client perceives as affordable entry.
    No value capture % -- keeps price predictable and accessible.
    Example: 4 person-days x EUR 1,200 = EUR 4,800 cost -> EUR 7,200 price

  CAPABILITY BUILDING (workshops, coaching, residencies):
    Price = max(Cost x 1.4, Cost + 3% x ClientValue)
    Rationale: 29%+ margin floor, captures upside when value is high.
    Example: 8 person-days = EUR 9,600 cost, value EUR 137K
      Floor: 9,600 x 1.4 = EUR 13,440
      Value: 9,600 + 3% x 137K = EUR 13,710
      Price: EUR 13,700 (value capture wins, 30% margin)

  ENTERPRISE TRANSFORMATION (long-term, org-wide):
    Price = max(Cost x 1.4, Cost + 2% x ClientValue) + optional Success Fee
    Rationale: lower value %, higher absolute numbers. Success fee aligns incentives.
    Example: 25 person-days = EUR 30,000 cost, value EUR 120K
      Floor: 30,000 x 1.4 = EUR 42,000
      Value: 30,000 + 2% x 120K = EUR 32,400
      Price: EUR 42,000 (floor wins, 29% margin)

SUCCESS FEE (optional, Course 2-3 only):
  15% of base price, payable if agreed KPIs hit within 6 months
  KPIs must be: measurable, time-bound, jointly defined before engagement
  Examples:
    - Defect rate reduction >= 30% (Dojo)
    - Developer throughput increase >= 15% (Forge)
    - Internal trainers certified and 2 cohorts delivered (Academy)
    - 3+ teams onboarded with >60% adoption (Wiring)
  Purpose: reduces client risk perception, recovers margin on proven outcomes
```

### Client ROI Targets

```
SWEET SPOT: 5-6x ROI (industry consensus: Consulting Success, Simon-Kucher)
ACCEPTABLE RANGE: 3-10x ROI
BELOW 3x: client will question value -- strengthen ROI narrative or reduce price
ABOVE 10x: you are undercharging -- raise price or add success fee component

CHECK: Price / ClientValue should be 10-20% (client keeps 80-90%)
  If ratio < 10%: you are leaving money on the table
  If ratio > 25%: client will comparison-shop
```

## Value Quantification Process

Step 1 of any pricing engagement. Without this, pricing is guesswork.

```
Step 1: QUANTIFY customer value
  Annual savings = (Baseline Cost - Cost With Service) + Revenue Uplift
  Time saved = Hours saved x Hourly rate of person saved
  Risk reduced = Probability of incident x Cost of incident
  Scaling factor = Number of people/teams affected

Step 2: CALCULATE price using Hybrid Formula above
  Select engagement type (diagnostic / capability / enterprise)
  Apply appropriate formula
  Verify ROI is in 3-10x range

Step 3: VALIDATE willingness-to-pay
  Van Westendorp (4 questions):
    "At what price too cheap (quality concern)?"
    "At what price a bargain?"
    "At what price getting expensive but still acceptable?"
    "At what price too expensive?"
  Plot curves -> intersection = acceptable price range

Step 4: ANCHOR with high-value tier first
  Present highest tier first in every context
  Anchoring increases average contract value 15-20% (Simon-Kucher)
  Middle tier becomes "obvious choice" via contrast effect
```

**Anti-Patterns**:
- Pure value-based without cost floor (creates negative margins on low-value services)
- Cost-plus without value ceiling (leaves money on table for high-value services)
- Same formula for all engagement types (diagnostics vs enterprise need different logic)
- Competitor-matching without value differential (destroys margin)
- Discounting without trading concessions ("always trade, never give")
- Quoting before understanding buyer's value equation

## Boutique Firm Pricing Advantages

Small firms (2-5 people) have structural pricing advantages. Leverage them.

```
SCARCITY PREMIUM:
  Limited capacity = genuine scarcity (not fabricated)
  "We onboard max 2 enterprise clients per quarter" (if true)
  Senior practitioners on every engagement (no junior rotation)
  Scarcity justifies 30-50% premium over larger firms

EFFICIENCY PREMIUM:
  No internal politics, staffing rotations, or methodology compliance overhead
  Faster delivery = lower elapsed time for client
  Lean cost structure = healthy margins at lower absolute prices

CAPACITY SIGNALS:
  Utilization > 75% for 3+ months -> raise prices (market signal)
  Turning down work -> you are underpriced
  Price is a queue management tool, not just a revenue tool

ANCHORING AGAINST BIG FIRMS:
  McKinsey charges EUR 11,000-22,000/day per consultant
  Boutique at EUR 2,400/day looks like extraordinary value by comparison
  Frame: "Senior-only team at 1/5 the price of Big 3"
```

## McKinsey Pricing Shift (2025+)

```
TREND: Major firms moving from fixed fee -> performance-based
  Driven by: AI shortening "doing" time, focus shifting to outcomes
  Structure: Base fee (60-70%) + performance bonus (30-40%)
  Implication: Success fee model is industry-validated, not experimental
```

## Good/Better/Best Tiering

Dominant B2B model (40.8% of B2B SaaS). Design all three tiers simultaneously.

```
GOOD (Starter / Essentials)
  Purpose: Capture SMB, reduce purchase risk, land-and-expand entry
  Features: Core value, limited seats/usage, self-serve
  Price: 30-40% of Better tier
  Goal: Prove value quickly, upgrade trigger built in

BETTER (Professional / Growth) -- TARGET tier
  Purpose: Main revenue driver, optimal value/price ratio
  Features: Full core + advanced features, standard support
  Price: 100% (baseline for ratio calculation)
  Goal: 60-70% of customers land here

BEST (Enterprise / Scale)
  Purpose: Large accounts, price anchor, expansion revenue
  Features: All features + enterprise security + dedicated support
  Price: 2.5-4x Better tier
  Goal: Anchor perception AND capture high-value accounts

DECOY MECHANICS:
  Best makes Better look like a bargain
  Good makes Better look like a logical upgrade
  Price gaps: small Good->Better, large Better->Best
  Expected distribution: 20% Good / 65% Better / 15% Best
```

### Feature Matrix Design

For each tier, categorize features:

```
| Feature          | Good | Better | Best | Upgrade Trigger         |
|------------------|------|--------|------|-------------------------|
| Core capability  | Yes  | Yes    | Yes  | --                      |
| Advanced feature | --   | Yes    | Yes  | User hits limit in Good |
| Enterprise need  | --   | --     | Yes  | Compliance/scale need   |
| Support level    | Docs | Email  | Ded. | Response time SLA       |
| Usage limit      | Low  | Medium | High | Growth exceeds cap      |
```

## Cialdini Principles Applied to Pricing

Ethical application only. Surface real value compellingly. Never fabricate.

```
ANCHORING (most important for pricing):
  Present highest tier first in every context
  Use precise non-round numbers: EUR 47,400 not EUR 48,000
  Show "was / now" only with genuine price history
  ROI as multiple: "8.3x return" not "730% ROI"

SOCIAL PROOF:
  Logo bar of similar companies above pricing table
  "Most Popular" badge on Better tier (if true)
  Testimonials from peers in same segment

RECIPROCITY:
  Free ROI calculator or audit before pricing discussion
  Genuine value delivered before the ask
  Pre-proposal gift: relevant industry insight

SCARCITY (genuine only):
  "We onboard 3 enterprise clients per quarter" (if true)
  Limited implementation capacity (if true)
  Never: fake countdown timers or false urgency

COMMITMENT:
  Free trial -> paid (foot-in-the-door)
  Pilot project -> full engagement
  Assessment -> implementation
```

**Ethical boundary**: Every Cialdini application must pass the 24-hour test -- would the buyer still feel good about it tomorrow? If not, remove it.

## Ackerman Bargaining (Deal Structuring)

For negotiation preparation. From Chris Voss methodology.

```
TARGET PRICE: The price you want to achieve

SEQUENCE:
  Offer 1: 65% of target (extreme anchor)
  Offer 2: 85% of target (large concession)
  Offer 3: 95% of target (small concession)
  Offer 4: 100% of target (precise non-round number + non-monetary item)

RULES:
  Each concession smaller than the last (signals approaching limit)
  Use precise numbers at final offer (EUR 47,350 not EUR 47,000)
  Add non-monetary concession at final offer (extra training day, extended warranty)
  Never split the difference on price -- add/remove scope instead
  Calibrated questions when pushed: "How am I supposed to make this work at that price?"
```

## Unit Economics Template

```
INPUTS:
  Monthly new customers (MNC)
  Average Contract Value (ACV) -- annual
  Average customer lifetime (months)
  Monthly sales+marketing spend (S&M)
  Gross margin (%)

CALCULATIONS:
  CAC = S&M / MNC
  ARPU = ACV / 12
  LTV = ARPU x Avg lifetime x Gross margin %
  LTV:CAC ratio (target: >3:1, excellent: >5:1)
  CAC Payback = CAC / (ARPU x Gross margin%) -- target: <12 months

BENCHMARKS (2025):
  SMB:        CAC payback 8-12 months  | LTV:CAC 3-5:1
  Mid-Market: CAC payback 14-18 months | LTV:CAC 3-4:1
  Enterprise: CAC payback 18-24 months | LTV:CAC 2-3:1

HEALTH CHECK:
  LTV:CAC < 1:1 -> unsustainable, reduce CAC or increase LTV
  LTV:CAC 1-3:1 -> borderline, optimize
  LTV:CAC > 5:1 -> healthy (or underinvesting in growth)
  CAC Payback > 24 months -> cash flow risk
```

## Revenue Model Selection

| Model | When to Use | AI Generates |
|-------|------------|--------------|
| Subscription | Recurring value delivery | Tier pricing, breakeven ARR |
| Usage-based | Variable consumption | Usage calculator, P10/P50/P90 projections |
| Freemium | High volume, viral growth | Conversion funnel model, upgrade triggers |
| Licensing | IP asset, one-time | Seat vs site license crossover |
| Consulting/Training | Expertise delivery | Hybrid formula, success fee structure |
| Outcome-based | Measurable ROI | Fee at target ROI, success metric definition |

## Research Sources

- Simon-Kucher: Price anchoring increases average deal value 15-20%
- Consulting Success: 5-6x ROI sweet spot for consulting client acceptance
- McKinsey (2025): Moving to performance-based fees driven by AI productivity gains
- Slideworks: McKinsey fixed fee + performance bonus structure (60-70% base / 30-40% performance)
- Consulting Success: 3-10x ROI range for value-based consulting pricing
- Industry data: Boutique firms at EUR 300-600/hour vs independents EUR 100-200/hour
