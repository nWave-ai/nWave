---
name: nw-lean-canvas-methodology
description: Lean Canvas and Value Proposition Canvas generation methodology with assumption mapping, pivot triggers, and anti-patterns
disable-model-invocation: true
---

# Lean Canvas Methodology

## Canvas Selection

- **Lean Canvas**: Default for startups and new product lines pre-product-market-fit. High uncertainty. Focus on problem/solution fit.
- **Business Model Canvas (BMC)**: Established businesses optimizing existing models or exploring adjacent ones.
- **Value Proposition Canvas (VPC)**: Deep dive on customer-value fit. Use alongside either canvas above.

## Lean Canvas Template (9 Blocks)

Generate in this order (problem-first, not solution-first):

```
1. CUSTOMER SEGMENTS         Who has the problem? (start here)
   - Early adopter profile    - Specific, not generic
   - Segment by JTBD          - "CTOs at 50-200 person SaaS companies" not "enterprises"

2. PROBLEM (top 3)           What are the top 3 problems for this segment?
   - Existing alternatives    - How do they solve it today?
   - Cost of status quo       - Quantify in time/money/risk

3. UNIQUE VALUE PROPOSITION  Single clear sentence: why different AND worth attention
   - High-level concept       - Analogy: "X for Y" (e.g., "Uber for freight")
   - Avoid jargon             - Customer language, not product language

4. SOLUTION                  Top 3 features mapped to top 3 problems (1:1)
   - Minimum viable           - Smallest thing that solves the problem
   - Evidence-backed          - What validates this solves the problem?

5. CHANNELS                  Path to customers (ranked by cost/reach)
   - Owned: blog, events      - Free/slow but sustainable
   - Earned: referrals, PR    - Free/unpredictable
   - Paid: ads, sponsorships  - Fast/expensive

6. REVENUE STREAMS           How you make money
   - Model type               - Subscription/usage/licensing/consulting
   - Pricing basis            - Per seat/per outcome/flat fee
   - First revenue milestone  - When does first EUR come in?

7. COST STRUCTURE            What it costs to operate
   - Fixed: salaries, tools   - Regardless of customers
   - Variable: hosting, CAC   - Scales with customers
   - Burn rate                - Monthly cash out

8. KEY METRICS               One metric that matters most right now
   - Pirate Metrics: AARRR    - Acquisition/Activation/Retention/Revenue/Referral
   - Stage-appropriate        - Pre-PMF: activation. Post-PMF: retention.

9. UNFAIR ADVANTAGE          What cannot be easily copied or bought
   - Not features             - Those can be copied
   - Examples: expertise, data, network, community, team, IP
   - Honest: "none yet" is valid for early stage
```

## Value Proposition Canvas Template

```
CUSTOMER PROFILE (right side)
  Jobs-to-be-Done:
    Functional: practical tasks they need to accomplish
    Social: how they want to be perceived
    Emotional: feelings they seek or avoid
  Pains: obstacles, frustrations, risks, undesired outcomes
    Rank: extreme / severe / moderate
  Gains: desired outcomes, benefits, aspirations
    Rank: essential / expected / desired / unexpected

VALUE MAP (left side)
  Products & Services: what you offer (list concretely)
  Pain Relievers: how each product addresses specific pains
    Map: pain reliever -> pain (explicit 1:1)
  Gain Creators: how each product produces specific gains
    Map: gain creator -> gain (explicit 1:1)

FIT CHECK:
  Every critical pain has a reliever?     [yes/no + gaps]
  Every essential gain has a creator?     [yes/no + gaps]
  Unmapped products (features without jobs)? [list — candidates for removal]
```

## Assumption Mapping

Every canvas block generates assumptions. Track them.

```
ASSUMPTION TEMPLATE:
  Block: [which canvas block]
  Assumption: [stated belief]
  Risk: (Impact if wrong: 1-5) x (Uncertainty: 1-5) = Risk Score
  Test: [how to validate — interview, landing page, prototype, data]
  Status: untested / testing / validated / invalidated
  Evidence: [what we learned]

PRIORITIZATION: Test highest risk score first. Top 3 assumptions are your sprint.

PIVOT TRIGGERS (per block):
  Problem invalidated -> Customer segment pivot or need pivot
  Solution fails testing -> Zoom-in or zoom-out pivot
  Channel too expensive -> Channel pivot
  Revenue model rejected -> Value capture pivot
  No unfair advantage forming -> Technology or platform pivot
```

## Anti-Patterns

- Completing canvas top-down without customer evidence (solution-first trap)
- Treating canvas as final deliverable rather than living hypothesis map
- Using BMC for early-stage startup (wrong abstraction level)
- Filling "Unfair Advantage" with features (those are copyable)
- Generic customer segments ("enterprises") instead of specific profiles
- Problems stated as absence of solution ("no tool for X") instead of actual pain
- Revenue model chosen before value proposition validated
