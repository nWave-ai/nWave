# Skills

## nw-ab-agent-template

- [nw-ab-agent-template](nw-ab-agent-template.md) — KNOWLEDGE — the canonical agent-spec template (frontmatter + body skeleton). Reference loaded by the create/migrate procedures; no sequence.

## nw-ab-anti-patterns

- [nw-ab-anti-patterns](nw-ab-anti-patterns.md) — KNOWLEDGE — agent/skill/command anti-pattern catalog with fixes. Reference scanned by validate-spec; no sequence.

## nw-ab-create-agent

- [nw-ab-create-agent](nw-ab-create-agent.md) — PROCEDURE — create a NEW agent via the 5-phase workflow (ANALYZE→DESIGN→CREATE→VALIDATE→REFINE). Trigger: build a new AI agent. Composes nw-ab-validate-spec.

## nw-ab-critique-dimensions

- [nw-ab-critique-dimensions](nw-ab-critique-dimensions.md) — Review dimensions for validating agent quality - template compliance, safety, testing, and priority validation

## nw-ab-examples

- [nw-ab-examples](nw-ab-examples.md) — KNOWLEDGE — canonical worked examples for agent creation, migration, and command optimization. Reference for the relevant procedures; no sequence.

## nw-ab-house-style

- [nw-ab-house-style](nw-ab-house-style.md) — KNOWLEDGE — caveman-native authoring house style + by-construction guarantees (Reasoning Mandate injection, measured-gain compression). Reference for create/migrate; no sequence.

## nw-ab-merge-agents

- [nw-ab-merge-agents](nw-ab-merge-agents.md) — PROCEDURE — merge agent B into agent A, relocating skills and cleaning up all references. Trigger: two agents must become one. Composes nw-ab-validate-spec.

## nw-ab-migrate-monolith

- [nw-ab-migrate-monolith](nw-ab-migrate-monolith.md) — PROCEDURE — migrate one legacy monolithic agent to a lean core plus routed skills. Trigger: an existing agent has measured size, embedded-configuration, duplication, aggressive-language, or multi-responsibility debt. Composes agent validation and requested skill optimization.

## nw-ab-optimize-command

- [nw-ab-optimize-command](nw-ab-optimize-command.md) — PROCEDURE — optimize a bloated command file to a lean declarative definition (forge.md pattern). Trigger: a command file over its size target with reducible content.

## nw-ab-optimize-skill

- [nw-ab-optimize-skill](nw-ab-optimize-skill.md) — PROCEDURE — optimize one requested existing skill. Measures multi-trigger, duplication, and resident-context debt before editing; preserves its name as the lean core and behavioral projections.

## nw-ab-validate-spec

- [nw-ab-validate-spec](nw-ab-validate-spec.md) — PROCEDURE — validate an EXISTING agent spec against the nw-ab-validation-checklist. Trigger: checking a spec for compliance (also the shared composition target create/migrate/merge invoke). One job: run the checklist, report pass/fail.

## nw-ab-validation-checklist

- [nw-ab-validation-checklist](nw-ab-validation-checklist.md) — KNOWLEDGE (data) — the agent-spec validation checklist. The item definitions the validate-spec procedure RUNS against. No sequence of its own.

## nw-abr-critique-dimensions

- [nw-abr-critique-dimensions](nw-abr-critique-dimensions.md) — Review dimensions for validating agent quality - template compliance, safety, testing, and priority validation

## nw-ad-critique-dimensions

- [nw-ad-critique-dimensions](nw-ad-critique-dimensions.md) — Review dimensions for acceptance test quality - happy path bias, GWT compliance, business language purity, coverage completeness, walking skeleton user-centricity, priority validation, observable behavior assertions, traceability coverage, and walking skeleton boundary proof

## nw-agent-creation-workflow

- [nw-agent-creation-workflow](nw-agent-creation-workflow.md) — Detailed 5-phase workflow for creating agents - from requirements analysis through validation and iterative refinement

## nw-agent-evals

- [nw-agent-evals](nw-agent-evals.md) — Lightweight eval method for testing nWave AGENTS and SKILLS (LLM behavior) as a lean alternative to heavy BDD/ATD. An eval = one prompt -> one captured run (trace + artifacts) -> a small set of checks -> a comparable score over time. Load when validating agent behavior, building a regression net for an agent/skill, or reducing agent-test bloat.

## nw-agent-testing

- [nw-agent-testing](nw-agent-testing.md) — 5-layer testing approach for agent validation including adversarial testing, security validation, and prompt injection resistance

## nw-algebraic-design-protocol

- [nw-algebraic-design-protocol](nw-algebraic-design-protocol.md) — The METHOD for finding a design — name observations and equality before constructors, then follow any contradiction to the type or observation that causes it. Use when a design decision is contested, a law has exceptions, a census or model keeps producing wrong answers, or a representation change must preserve meaning. Complements nw-fp-algebra-driven-design, which catalogues the structures; this says how to arrive at one and what to do when it breaks.

## nw-architectural-styles-tradeoffs

- [nw-architectural-styles-tradeoffs](nw-architectural-styles-tradeoffs.md) — Architectural style selection decision matrices, trade-off analysis, structural enforcement rules, and combination patterns. Load when choosing or evaluating architecture styles.

## nw-architecture-patterns

- [nw-architecture-patterns](nw-architecture-patterns.md) — Comprehensive architecture patterns, methodologies, quality frameworks, and evaluation methods for solution architects. Load when designing system architecture or selecting patterns.

## nw-at-completeness-check

- [nw-at-completeness-check](nw-at-completeness-check.md) — Verify that one minimal oracle falsifies every declared delivery obligation without checklist ceremony or duplicate tests.

## nw-authoritative-sources

- [nw-authoritative-sources](nw-authoritative-sources.md) — Domain-specific authoritative source databases, search strategies by topic category, and source freshness rules

## nw-auto

- [nw-auto](nw-auto.md) — Evaluates and revises Request S/M/L and delivery choices from evidence, then uses nwdes to construct delivery artifacts.

## nw-bdd-methodology

- [nw-bdd-methodology](nw-bdd-methodology.md) — BDD patterns for acceptance test design - Given-When-Then as a language-neutral specification style, scenario writing rules, realization in the project's incumbent native scenario syntax (Python pytest-bdd binding labelled), anti-patterns, and living documentation

## nw-bdd-requirements

- [nw-bdd-requirements](nw-bdd-requirements.md) — BDD requirements discovery methodology - Example Mapping, Three Amigos, conversational patterns, Given-When-Then translation, and collaborative specification

## nw-brainstorming

- [nw-brainstorming](nw-brainstorming.md) — Structured divergent thinking techniques — HMW framing, SCAMPER, Crazy 8s mechanics, and option diversity guarantees. Enforces strict separation of generation and evaluation phases.

## nw-buddy

- [nw-buddy](nw-buddy.md) — Read-only nWave concierge for methodology, current project evidence, command routing, migration, and troubleshooting.

## nw-buddy-command-catalog

- [nw-buddy-command-catalog](nw-buddy-command-catalog.md) — Current public nWave delivery commands.

## nw-buddy-project-reading

- [nw-buddy-project-reading](nw-buddy-project-reading.md) — Evidence-first project reading protocol based on durable authorities, Git, tests, and installed surfaces.

## nw-buddy-ssot-knowledge

- [nw-buddy-ssot-knowledge](nw-buddy-ssot-knowledge.md) — Single Source of Truth detection — where truth lives in an nWave repo and how to avoid contradicting it.

## nw-bugfix

- [nw-bugfix](nw-bugfix.md) — Routes an observed defect through host-owned diagnosis and nwdes delivery artifacts.

## nw-canary

- [nw-canary](nw-canary.md) — Canary skill for auto-injection detection

## nw-certainty-by-construction

- [nw-certainty-by-construction](nw-certainty-by-construction.md) — Turn a stable layer claim (domain, application, adapter, or infrastructure) into a construction boundary so the invalid state cannot be built, and state honestly what remains unguarded. Use when a requirement says an invalid state or transition must not occur, when values need a canonical form, or when a rewrite/cache/optimisation must preserve meaning. Complements nw-fp-domain-modeling, which shows the encodings; this decides whether to encode, how strong the claim really is, and what obligation is left over.

## nw-cicd-and-deployment

- [nw-cicd-and-deployment](nw-cicd-and-deployment.md) — CI/CD pipeline design methodology, deployment strategies, GitHub Actions patterns, and branch/release strategies. Load when designing pipelines or deployment workflows.

## nw-code-analysis-port

- [nw-code-analysis-port](nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.

## nw-code-craftsmanship

- [nw-code-craftsmanship](nw-code-craftsmanship.md) — Universal OO/FP craftsmanship foundation — domain-language naming, small cohesive units, semantic DRY/SSOT, reuse-before-new, one owner per rule/config/fact, prefactoring before new behavior, ports/adapters for testability. Consult before writing or reviewing any unit of code, either paradigm.

## nw-code-design-fp

- [nw-code-design-fp](nw-code-design-fp.md) — FP code-design SSOT — the WHAT-to-design catalog (algebra-driven design, domain modelling with types, railway/error-track isolation) shared by the solution architect (design-time) and the functional crafter (execution-time).

## nw-code-design-oo

- [nw-code-design-oo](nw-code-design-oo.md) — OO code-design SSOT — the WHAT-to-design anti-smell catalog (Object Calisthenics, RPP smell taxonomy, effect isolation) shared by the solution architect (design-time) and the crafter (execution-time).

## nw-collapse-detection

- [nw-collapse-detection](nw-collapse-detection.md) — Documentation collapse anti-patterns - detection rules, bad examples, and remediation strategies for type-mixing violations

## nw-command-design-patterns

- [nw-command-design-patterns](nw-command-design-patterns.md) — Best practices for command definition files - size targets, declarative template, anti-patterns, and canonical examples based on research evidence

## nw-command-design-patterns-authoring

- [nw-command-design-patterns-authoring](nw-command-design-patterns-authoring.md) — The v2.8+ new-command installation contract - which three files to produce and their frontmatter when creating a brand-new command

## nw-command-design-patterns-classification

- [nw-command-design-patterns-classification](nw-command-design-patterns-classification.md) — How to size and categorize a command, the declarative command template, and the WHAT-vs-HOW logic-placement rule

## nw-command-design-patterns-reduction

- [nw-command-design-patterns-reduction](nw-command-design-patterns-reduction.md) — What is reducible in a bloated command - the duplication triangle, the anti-pattern catalog, and the compress/never-compress rules

## nw-command-optimization-workflow

- [nw-command-optimization-workflow](nw-command-optimization-workflow.md) — Step-by-step workflow for converting bloated command files to lean declarative definitions

## nw-cross-cutting-context-residency

- [nw-cross-cutting-context-residency](nw-cross-cutting-context-residency.md) — KNOWLEDGE — use when choosing resident, map-only, or on-demand context.

## nw-cross-cutting-evidence-instrumentation

- [nw-cross-cutting-evidence-instrumentation](nw-cross-cutting-evidence-instrumentation.md) — KNOWLEDGE — use when evaluating a claim, check, measurement, or shared-log count.

## nw-cross-cutting-input-data-contracts

- [nw-cross-cutting-input-data-contracts](nw-cross-cutting-input-data-contracts.md) — KNOWLEDGE — use when adding data, declaring inputs, or choosing a join key.

## nw-cross-cutting-invariants

- [nw-cross-cutting-invariants](nw-cross-cutting-invariants.md) — Cross-cutting normative invariants — routing core for the software/model boundary doctrine, gate/construction principles and on-demand knowledge lenses. Cite clause ids; never re-declare.

## nw-css-implementation-recipes

- [nw-css-implementation-recipes](nw-css-implementation-recipes.md) — Concrete CSS code snippets for futuristic UI patterns -- glassmorphism, neon glows, HUD elements, data grids, holographic effects

## nw-data-architecture-patterns

- [nw-data-architecture-patterns](nw-data-architecture-patterns.md) — Data architecture patterns (warehouse, lake, lakehouse, mesh), ETL/ELT pipelines, streaming architectures, scaling strategies, and schema design patterns

## nw-database-technology-selection

- [nw-database-technology-selection](nw-database-technology-selection.md) — Database comparison catalogs, RDBMS vs NoSQL selection criteria, CAP/ACID/BASE theory, OLTP vs OLAP, and technology-specific characteristics

## nw-ddd-architect

- [nw-ddd-architect](nw-ddd-architect.md) — DDD architect design-time mandates — the Fixture-Fanout Enumeration Mandate for shared-substrate per-caller migration (enumerate production callers plus fixture sites plus atomic bundle scope, mechanically enforced) that both the ddd-architect and its reviewer load by name

## nw-ddd-event-modeling

- [nw-ddd-event-modeling](nw-ddd-event-modeling.md) — Event Modeling facilitation technique — brainstorm events, identify commands and views, define aggregate boundaries, write Given-When-Then specifications

## nw-ddd-eventsourcing

- [nw-ddd-eventsourcing](nw-ddd-eventsourcing.md) — Event Sourcing and CQRS as DDD implementation patterns — when to use, aggregate event streams, projections, snapshots, sagas, upcasting, conflict resolution

## nw-ddd-strategic

- [nw-ddd-strategic](nw-ddd-strategic.md) — Strategic DDD — bounded context discovery, context mapping patterns, subdomain classification, ubiquitous language, and organizational alignment

## nw-ddd-tactical

- [nw-ddd-tactical](nw-ddd-tactical.md) — Tactical DDD — aggregate design rules, entities, value objects, domain events, repositories, domain services, and anti-pattern detection

## nw-deliver

- [nw-deliver](nw-deliver.md) — Routes one strict Request through host-owned delivery using nwdes artifacts.

## nw-deployment-strategies

- [nw-deployment-strategies](nw-deployment-strategies.md) — Rollback procedures, risk assessment, pre/post-deployment validation, and contingency planning. Load when orchestrating deployment or preparing rollback plans. For deployment strategy details (canary, blue-green, rolling), see `cicd-and-deployment` skill.

## nw-der-review-criteria

- [nw-der-review-criteria](nw-der-review-criteria.md) — Evaluation criteria and scoring for data engineering artifact reviews

## nw-design

- [nw-design](nw-design.md) — Establishes durable architecture, reuse, boundaries, cross-layer algebra, residual stress behavior, paradigm, and prefactoring decisions for deterministic minimal handover construction.

## nw-design-patterns

- [nw-design-patterns](nw-design-patterns.md) — 7 agentic design patterns with decision tree for choosing the right pattern for each agent type

## nw-devops

- [nw-devops](nw-devops.md) — Establishes durable deployment, environment, observability, recovery, and CI constraints when platform risk requires the DEVOPS lens.

## nw-diagram

- [nw-diagram](nw-diagram.md) — Generates C4 architecture diagrams (context, container, component) in Mermaid or PlantUML. Use when creating or updating architecture visualizations.

## nw-discover

- [nw-discover](nw-discover.md) — Tests whether a product problem and opportunity are real, then updates the durable product evidence authorities without creating delivery state.

## nw-discovery-workflow

- [nw-discovery-workflow](nw-discovery-workflow.md) — 4-phase discovery workflow with decision gates, phase transitions, success metrics, and state tracking

## nw-discuss

- [nw-discuss](nw-discuss.md) — PO-led product conversation, visible feedback increments and human-readable briefs.

## nw-distill

- [nw-distill](nw-distill.md) — Produce an executable public oracle from durable authority.

## nw-distill-port-treatment-policy

- [nw-distill-port-treatment-policy](nw-distill-port-treatment-policy.md) — Port-to-port acceptance criteria + the Architecture of Reference (port-class → test treatment) + the Project Infrastructure Policy (concrete mechanism per port) + the walking-skeleton canonical definition and not-applicable exemptions. Consult while classifying a port's test treatment and the concrete mechanism for this codebase.

## nw-distill-prior-wave-reading

- [nw-distill-prior-wave-reading](nw-distill-prior-wave-reading.md) — Reads and reconciles durable product, architecture, and platform authorities before DISTILL compiles an executable oracle.

## nw-distill-red-scaffolding

- [nw-distill-red-scaffolding](nw-distill-red-scaffolding.md) — Prepare declared native oracle/supports and establish failure for the promised business reason without production stubs, invented reports or runner substitution.

## nw-diverge

- [nw-diverge](nw-diverge.md) — Generates 3-5 divergent design directions through JTBD analysis, competitive research, structured brainstorming, and taste evaluation before convergence. Use when the team has a validated problem but hasn't chosen a solution approach.

## nw-diverger-review-criteria

- [nw-diverger-review-criteria](nw-diverger-review-criteria.md) — Review criteria for the nw-diverger-reviewer — validates JTBD rigor, research quality, option diversity, taste application correctness, and recommendation coherence in DIVERGE wave artifacts

## nw-divio-framework

- [nw-divio-framework](nw-divio-framework.md) — DIVIO/Diataxis four-quadrant documentation framework - type definitions, classification decision tree, and signal catalog

## nw-doc-as-artifact

- [nw-doc-as-artifact](nw-doc-as-artifact.md) — Use briefs and HTML as shared reading surfaces for human understanding and collaborative review.

## nw-document

- [nw-document](nw-document.md) — Creates evidence-based documentation following DIVIO/Diataxis principles. Use when writing tutorials, how-to guides, reference docs, or explanations.

## nw-domain-driven-design

- [nw-domain-driven-design](nw-domain-driven-design.md) — Strategic and tactical DDD patterns, bounded context discovery, context mapping, aggregate design rules, and decision frameworks for when to apply DDD

## nw-dr-review-criteria

- [nw-dr-review-criteria](nw-dr-review-criteria.md) — Critique dimensions, severity framework, verdict decision matrix, and review output format for documentation assessment reviews

## nw-expectation-charter

- [nw-expectation-charter](nw-expectation-charter.md) — Supplies or reviews user-view qualitative charter facts when EXAMINE applies.

## nw-five-whys-methodology

- [nw-five-whys-methodology](nw-five-whys-methodology.md) — Toyota 5 Whys methodology with multi-causal branching, evidence requirements, and validation techniques

## nw-forge

- [nw-forge](nw-forge.md) — Backward-compatible router for creating agents, validating existing agents, migrating existing agent monoliths, or optimizing one existing skill.

## nw-formal-verification-tlaplus

- [nw-formal-verification-tlaplus](nw-formal-verification-tlaplus.md) — TLA+ and PlusCal for specifying distributed system invariants. Decision heuristics for when formal verification adds value, key patterns, state explosion management, and alternatives comparison.

## nw-fp-algebra-driven-design

- [nw-fp-algebra-driven-design](nw-fp-algebra-driven-design.md) — Algebra-driven API design with monoids, semigroups, and interpreters via algebraic equations

## nw-fp-clojure

- [nw-fp-clojure](nw-fp-clojure.md) — Clojure language-specific patterns, data-first modeling, REPL-driven development, and spec

## nw-fp-domain-modeling

- [nw-fp-domain-modeling](nw-fp-domain-modeling.md) — Domain modeling with algebraic data types, smart constructors, and type-level error handling

## nw-fp-erlang-elixir

- [nw-fp-erlang-elixir](nw-fp-erlang-elixir.md) — Erlang/Elixir language-specific patterns, OTP as the effect model, and runtime-enforced immutability

## nw-fp-fsharp

- [nw-fp-fsharp](nw-fp-fsharp.md) — F# language-specific patterns, Railway-Oriented Programming, and Computation Expressions

## nw-fp-haskell

- [nw-fp-haskell](nw-fp-haskell.md) — Haskell language-specific patterns, GADTs, type classes, and effect systems

## nw-fp-kotlin

- [nw-fp-kotlin](nw-fp-kotlin.md) — Kotlin language-specific patterns with Arrow, Raise DSL, and coroutine-based effects

## nw-fp-principles

- [nw-fp-principles](nw-fp-principles.md) — Core functional programming thinking patterns and type system foundations, language-agnostic

## nw-fp-rust

- [nw-fp-rust](nw-fp-rust.md) — Rust language-specific patterns, compiler-verified exhaustive ADTs, and Result/Option as railway-oriented programming

## nw-fp-scala

- [nw-fp-scala](nw-fp-scala.md) — Scala 3 language-specific patterns with ZIO, Cats Effect, and opaque types

## nw-fp-typescript

- [nw-fp-typescript](nw-fp-typescript.md) — TypeScript language-specific patterns with fp-ts/Effect, discriminated unions, and railway-oriented error handling

## nw-futuristic-color-typography

- [nw-futuristic-color-typography](nw-futuristic-color-typography.md) — Color palettes, font pairing, and visual treatments for sci-fi aesthetics -- concrete values with rationale

## nw-hotspot

- [nw-hotspot](nw-hotspot.md) — Git change frequency hotspot analysis — find the most-changed files in your codebase

## nw-human-collaboration

- [nw-human-collaboration](nw-human-collaboration.md) — Collaborate with the human to refine product, architecture and operational decisions before implementation; preserve explicit delegation preferences.

## nw-infrastructure-and-observability

- [nw-infrastructure-and-observability](nw-infrastructure-and-observability.md) — Infrastructure as Code patterns (Terraform, Kubernetes), observability design (SLOs, metrics, alerting, dashboards), and pipeline security stages. Load when designing infrastructure, observability, or security scanning.

## nw-interaction-choreography

- [nw-interaction-choreography](nw-interaction-choreography.md) — Animation principles, timing, easing curves, and choreography sequences for futuristic interfaces -- motion as communication

## nw-interviewing-techniques

- [nw-interviewing-techniques](nw-interviewing-techniques.md) — Mom Test questioning toolkit, JTBD analysis, interview conduct, assumption testing framework, and hypothesis design

## nw-investigation-techniques

- [nw-investigation-techniques](nw-investigation-techniques.md) — Evidence collection methods, problem categorization, analysis techniques, and solution design patterns

## nw-jtbd-analysis

- [nw-jtbd-analysis](nw-jtbd-analysis.md) — JTBD methodology for extracting real jobs behind feature requests — job statements, abstraction layers, first-principles extraction, ODI outcome statements, and opportunity scoring

## nw-jtbd-core

- [nw-jtbd-core](nw-jtbd-core.md) — Core JTBD theory and job story format - job dimensions, job story template, job stories vs user stories, 8-step universal job map, outcome statements, and forces of progress

## nw-jtbd-interviews

- [nw-jtbd-interviews](nw-jtbd-interviews.md) — JTBD discovery techniques adapted for AI product owner context. Four Forces extraction, job dimension probing, question banks, and anti-patterns for interactive feature discovery conversations.

## nw-jtbd-opportunity-scoring

- [nw-jtbd-opportunity-scoring](nw-jtbd-opportunity-scoring.md) — JTBD opportunity scoring and prioritization - outcome statement format, opportunity algorithm, scoring interpretation, feature prioritization, and opportunity matrix template

## nw-jtbd-workflow-selection

- [nw-jtbd-workflow-selection](nw-jtbd-workflow-selection.md) — JTBD workflow classification and routing - ODI two-phase framework, five job types with workflow sequences, baseline type selection, workflow anti-patterns, and common recipes

## nw-mikado

- [nw-mikado](nw-mikado.md) — [EXPERIMENTAL] Complex refactoring roadmaps with visual tracking

## nw-mode-select

- [nw-mode-select](nw-mode-select.md) — Choose or change how to collaborate with the human for the current scope; reuses human-collaboration guidance without runtime gates.

## nw-mutation-test

- [nw-mutation-test](nw-mutation-test.md) — Run an explicit mutation probe over a named production delta, or support the project-level nightly-delta policy. Disabled by default.

## nw-nwdes

- [nw-nwdes](nw-nwdes.md) — nwdes routes and verbs for host-led delivery of a Request.

## nw-operational-safety

- [nw-operational-safety](nw-operational-safety.md) — Tool safety protocols, adversarial output validation, error recovery patterns, and I/O contracts for research operations

## nw-opportunity-mapping

- [nw-opportunity-mapping](nw-opportunity-mapping.md) — Opportunity Solution Trees, opportunity scoring, Lean Canvas, JTBD job mapping, and technique selection guide

## nw-optimize-tests

- [nw-optimize-tests](nw-optimize-tests.md) — Consolidates a test scope to the fewest tests that preserve coverage and behavior, deleting duplication, parametrize inflation, language-guarantee tests, AST-shape tests, and stale migration nets. An independent read-only reviewer with veto always validates the result.

## nw-outcome-kpi-framework

- [nw-outcome-kpi-framework](nw-outcome-kpi-framework.md) — Outcome KPI definition methodology - synthesizes Who Does What By How Much (Gothelf/Seiden), Running Lean (Maurya), and Measure What Matters (Doerr) into a practical framework for measurable outcome KPIs

## nw-par-critique-dimensions

- [nw-par-critique-dimensions](nw-par-critique-dimensions.md) — Platform design review critique dimensions and severity levels. Load when reviewing CI/CD pipelines, infrastructure, deployment strategies, observability, or security designs.

## nw-par-review-criteria

- [nw-par-review-criteria](nw-par-review-criteria.md) — Quality dimensions and review checklist for devop reviews

## nw-pbt-dotnet

- [nw-pbt-dotnet](nw-pbt-dotnet.md) — .NET property-based testing with FsCheck, CsCheck, and fsharp-hedgehog frameworks

## nw-pbt-erlang-elixir

- [nw-pbt-erlang-elixir](nw-pbt-erlang-elixir.md) — Erlang/Elixir property-based testing with PropEr, PropCheck, and StreamData frameworks

## nw-pbt-go

- [nw-pbt-go](nw-pbt-go.md) — Go property-based testing with rapid and gopter frameworks

## nw-pbt-haskell

- [nw-pbt-haskell](nw-pbt-haskell.md) — Haskell property-based testing with QuickCheck and Hedgehog frameworks

## nw-pbt-jvm

- [nw-pbt-jvm](nw-pbt-jvm.md) — JVM property-based testing with jqwik, ScalaCheck, and ZIO Test frameworks

## nw-pbt-python

- [nw-pbt-python](nw-pbt-python.md) — Python property-based testing with Hypothesis framework, strategies, and pytest integration

## nw-pbt-rust

- [nw-pbt-rust](nw-pbt-rust.md) — Rust property-based testing with proptest, quickcheck, and bolero frameworks

## nw-pbt-typescript

- [nw-pbt-typescript](nw-pbt-typescript.md) — TypeScript/JavaScript property-based testing with fast-check framework and arbitraries

## nw-pdr-review-criteria

- [nw-pdr-review-criteria](nw-pdr-review-criteria.md) — Evidence quality validation and decision gate criteria for product discovery reviews

## nw-persona-jtbd-analysis

- [nw-persona-jtbd-analysis](nw-persona-jtbd-analysis.md) — Structured persona creation and JTBD analysis methodology - persona templates, ODI job step tables, pain point mapping, success metric quantification, and multi-persona segmentation

## nw-platform-engineering-foundations

- [nw-platform-engineering-foundations](nw-platform-engineering-foundations.md) — Foundational platform engineering knowledge from key references -- Continuous Delivery, SRE, Accelerate, Team Topologies, Chaos Engineering, and Secure Delivery. Load when contextual grounding in platform engineering theory is needed.

## nw-po-review-dimensions

- [nw-po-review-dimensions](nw-po-review-dimensions.md) — Requirements quality critique dimensions for peer review - confirmation bias detection, completeness validation, clarity checks, testability assessment, and priority validation

## nw-po-scenario-exploration

- [nw-po-scenario-exploration](nw-po-scenario-exploration.md) — Assess product values for Quint relevance and explore them through actual traces and mechanically rendered scenarios for human review.

## nw-por-review-criteria

- [nw-por-review-criteria](nw-por-review-criteria.md) — Review dimensions and bug patterns for journey artifact reviews

## nw-post-mortem-framework

- [nw-post-mortem-framework](nw-post-mortem-framework.md) — Blameless post-mortem structure, incident timeline reconstruction, response evaluation, and organizational learning

## nw-product-value-slicing

- [nw-product-value-slicing](nw-product-value-slicing.md) — Product-owner foundation for slicing value — elephant carpaccio thin vertical slices, one walking skeleton per feature (not per slice), feature identity from user/product authority, JTBD/domain language framing. Consult when decomposing a feature into independently observable increments.

## nw-production-readiness

- [nw-production-readiness](nw-production-readiness.md) — Monitoring, observability, operational procedures, CI/CD lessons learned, and quality gate definitions. Load when assessing production readiness or validating operational excellence.

## nw-property-based-testing

- [nw-property-based-testing](nw-property-based-testing.md) — Property-based testing strategies (PBT — ACTIVE, authored by the acceptance-designer during DISTILL), shrinking, PBT+TDD integration.

## nw-quality-validation

- [nw-quality-validation](nw-quality-validation.md) — Type-specific validation checklists, six quality characteristics, and quality gate thresholds for documentation assessment

## nw-query-optimization

- [nw-query-optimization](nw-query-optimization.md) — SQL and NoSQL query optimization techniques, indexing strategies, execution plan analysis, JOIN algorithms, cardinality estimation, and database-specific query patterns

## nw-refactor

- [nw-refactor](nw-refactor.md) — Applies the Refactoring Priority Premise (RPP) levels L1-L6 for systematic code refactoring. Use when improving code quality through structured refactoring passes.

## nw-research

- [nw-research](nw-research.md) — Gathers knowledge from web and files, cross-references across multiple sources, and produces cited research documents. Use when investigating technologies, patterns, or decisions that need evidence backing.

## nw-research-methodology

- [nw-research-methodology](nw-research-methodology.md) — Research output templates, distillation workflow, and quality standards for evidence-driven research

## nw-review

- [nw-review](nw-review.md) — Dispatches an independent reviewer for a durable authority, immutable oracle, candidate diff, charter set, or operational artifact.

## nw-review-output-format

- [nw-review-output-format](nw-review-output-format.md) — YAML output format and approval criteria for platform design reviews. Load when generating review feedback.

## nw-rigor

- [nw-rigor](nw-rigor.md) — Configure explicit Codex or Claude model facts for nWave defaults or published roles, consumed by the native host where supported. Never derives a model from a competence label.

## nw-role-invocation

- [nw-role-invocation](nw-role-invocation.md) — KNOWLEDGE — how a wave entrypoint invokes its specialist: the real installed role definition, never a generic persona. Load when a wave delegates to a role.

## nw-root-why

- [nw-root-why](nw-root-why.md) — Root cause analysis and debugging

## nw-rr-critique-dimensions

- [nw-rr-critique-dimensions](nw-rr-critique-dimensions.md) — Critique dimensions and scoring for research document reviews

## nw-sa-critique-dimensions

- [nw-sa-critique-dimensions](nw-sa-critique-dimensions.md) — Architecture quality critique dimensions for peer review. Load when invoking solution-architect-reviewer or performing self-review of architecture documents.

## nw-sar-critique-dimensions

- [nw-sar-critique-dimensions](nw-sar-critique-dimensions.md) — Architecture quality critique dimensions for peer review. Load when performing architecture document reviews.

## nw-sc-review-dimensions

- [nw-sc-review-dimensions](nw-sc-review-dimensions.md) — Reviewer critique dimensions for peer review - implementation bias detection, test quality validation, completeness checks, and priority validation

## nw-sci-fi-design-patterns

- [nw-sci-fi-design-patterns](nw-sci-fi-design-patterns.md) — Catalog of UI patterns from games, anime, and films with analysis of why they work -- structural principles extractable to real interfaces

## nw-sd-case-studies

- [nw-sd-case-studies](nw-sd-case-studies.md) — 25 real-world system design case studies condensed from Alex Xu's System Design Interview Vol 1 and 2 - requirements, architecture, deep dive insights, key takeaways

## nw-sd-framework

- [nw-sd-framework](nw-sd-framework.md) — 4-step system design framework with back-of-envelope estimation, scaling ladder, and common pitfalls

## nw-sd-patterns

- [nw-sd-patterns](nw-sd-patterns.md) — Core distributed systems patterns - load balancing, caching, sharding, consistent hashing, message queues, rate limiting, CDN, Bloom filters, ID generation, replication, conflict resolution, CAP theorem

## nw-sd-patterns-advanced

- [nw-sd-patterns-advanced](nw-sd-patterns-advanced.md) — Advanced distributed patterns - event sourcing, CQRS, saga, stream processing, append-only log, exactly-once delivery, sequencer, double-entry ledger, erasure coding, order book, watermarks

## nw-security-and-governance

- [nw-security-and-governance](nw-security-and-governance.md) — Database security (encryption, access control, injection prevention), data governance (lineage, quality, MDM), and compliance frameworks (GDPR, CCPA, HIPAA)

## nw-security-by-design

- [nw-security-by-design](nw-security-by-design.md) — Security design principles, STRIDE threat modeling, OWASP Top 10 architectural mitigations, and secure patterns. Load when designing systems or reviewing architecture for security.

## nw-solution-architect-formal-verification

- [nw-solution-architect-formal-verification](nw-solution-architect-formal-verification.md) — PROCEDURE — formally verify every design's algebraic claims with need-selected checkers and explicit host-relayed installation or human waiver.

## nw-source-verification

- [nw-source-verification](nw-source-verification.md) — Source reputation tiers, cross-referencing methodology, bias detection, and citation format requirements

## nw-speculative-dispatch

- [nw-speculative-dispatch](nw-speculative-dispatch.md) — Speculative parallel implementation methodology — dispatch N candidate implementations, audit all, score, pick best. Auditability mandate: ALL candidates logged (not just winner).

## nw-spike

- [nw-spike](nw-spike.md) — A bounded probe of one product, visual-experience or technical uncertainty; returns evidence to its owner without starting a wave or promoting code automatically.

## nw-spike-methodology

- [nw-spike-methodology](nw-spike-methodology.md) — Guides a bounded, decision-relevant probe for a product, visual or technical uncertainty without creating wave authority

## nw-stakeholder-engagement

- [nw-stakeholder-engagement](nw-stakeholder-engagement.md) — Demonstration preparation, audience-tailored presentations, feedback collection, and business outcome measurement. Load when preparing demos or measuring business value delivery.

## nw-stress-analysis

- [nw-stress-analysis](nw-stress-analysis.md) — Advanced architecture stress analysis methodology for designing systems that survive unknown stresses. Load on its semantic trigger — external/nondeterministic dependency, recovery/retry/compensation/degradation, contagion, infrastructure/substrate uncertainty, high-uncertainty socio-technical/business boundary — or on explicit --residuality (force-on).

## nw-swarm

- [nw-swarm](nw-swarm.md) — How a root LLM runs several nwdes lanes in parallel with one lane orchestrator per lane, on any host. Load when more than one feature or lane is open or about to be.

## nw-taste-evaluation

- [nw-taste-evaluation](nw-taste-evaluation.md) — Design taste evaluation framework — DVF primary filter, Apple/Google/Jobs design principles as explicit scoring criteria, weighted decision matrix, and option ranking for the DIVERGE wave

## nw-tdd-cross-language

- [nw-tdd-cross-language](nw-tdd-cross-language.md) — Port the state-delta + property-based testing paradigm to languages other than Python. DIY recipes per language; canonical Python ref shipped in nwave_ai.state_delta.

## nw-tdd-methodology

- [nw-tdd-methodology](nw-tdd-methodology.md) — Deep knowledge for Outside-In TDD - double-loop architecture, ATDD integration, port-to-port testing, walking skeletons, and test doubles policy

## nw-tdd-methodology-paradigm

- [nw-tdd-methodology-paradigm](nw-tdd-methodology-paradigm.md) — Native contract-driven unit and acceptance testing: generative broad laws, finite examples, public-state preservation and real-boundary evidence.

## nw-tdd-methodology-pbt-deep

- [nw-tdd-methodology-pbt-deep](nw-tdd-methodology-pbt-deep.md) — Deep property-based-testing mechanics (Hebert) - stateful PBT command-precondition anti-patterns (A13/P6), the four property-finding strategies, the two shrinking mechanisms, and targeted/search-based PBT with its hard limitations

## nw-tdd-methodology-port-to-port

- [nw-tdd-methodology-port-to-port](nw-tdd-methodology-port-to-port.md) — What a test asserts on and where it enters - port-to-port discipline at all test levels, the layer-specific Universe, refactoring-resilience, and the hexagonal per-layer testing strategy

## nw-tdd-methodology-test-doubles

- [nw-tdd-methodology-test-doubles](nw-tdd-methodology-test-doubles.md) — Choosing and building a test double - Meszaros taxonomy, classical-vs-mockist verification, the mock-only-at-port-boundaries policy, and the contract that every InMemory double must validate inputs like the real adapter

## nw-tdd-methodology-walking-skeleton

- [nw-tdd-methodology-walking-skeleton](nw-tdd-methodology-walking-skeleton.md) — Building and validating a walking skeleton - the WS protocol scoped to the FEATURE (one skeleton, extended by every slice), Mandate 5 adapter port-class real-I/O treatment (resource table), and Mandate 6 adapter-integration real-I/O requirement

## nw-test-design-mandates

- [nw-test-design-mandates](nw-test-design-mandates.md) — Design mandates for acceptance tests - hexagonal boundary, business language abstraction, user journey completeness, pure function extraction, 3 Pillars (domain language / chained narrative / production composition), and the layered ATD discipline (Universe-bound assertion, layer-dependent PBT mode, two-tier acceptance, example-based sad paths). Lean recomposing core - routes to three narrow mandate modules.

## nw-test-design-mandates-composition-contract

- [nw-test-design-mandates-composition-contract](nw-test-design-mandates-composition-contract.md) — Composition-root authoring-contract mandates for acceptance tests — SSOT + Zero Duplication via Types + Services + DSL, Driving-Port-Only Boundary (Farley four-layer protocol-driver contract, fixture-theater/tautological-test anti-pattern), Contract Shape Classification (@in-memory/@real-io tag-vs-composition), and Dormant-Seam Reconciliation (AT drives the DESIGN-declared seam, not the new component). Consult while composing the AT's driving surface, structuring step/type/service code, and tagging the contract shape. Canonical definitions; SSOT for these mandates.

## nw-test-design-mandates-layered-mechanics

- [nw-test-design-mandates-layered-mechanics](nw-test-design-mandates-layered-mechanics.md) — Layered acceptance-test mechanics: public state preservation, native generative laws, real-boundary journeys and explicit failure observations.

## nw-test-design-mandates-scenario-design

- [nw-test-design-mandates-scenario-design](nw-test-design-mandates-scenario-design.md) — Scenario-design mandates for acceptance tests — Hexagonal Boundary Enforcement (drive through driving ports, never internals), Business Language Abstraction (three abstraction layers), User Journey Completeness, Pure Function Extraction Before Fixtures, Algebraic Analysis Before the Scenario (name the law, find its narrowest surface, declare every gated input, prove the scenario can fail), the 3 Pillars style backbone, and Walking Skeleton Strategy. Consult while shaping or judging a scenario's boundary, language, journey completeness, and fixture strategy. Canonical definitions; SSOT for these mandates.

## nw-test-optimization

- [nw-test-optimization](nw-test-optimization.md) — Methodology for minimizing test count while maximizing behavioral coverage - lean core composing behavior-counting, anti-patterns, consolidation, paradigm-match, coverage-validation, scope-selection modules

## nw-test-optimization-consolidation

- [nw-test-optimization-consolidation](nw-test-optimization-consolidation.md) — Coverage-preserving consolidation patterns applied in order - parametrize-collapse, dict-iteration, fixture-scope, xdist-group, migration-collapse lifecycle, cross-tier dedup, single-lifecycle consolidation, state-delta cross-ref

## nw-test-optimization-paradigm-match

- [nw-test-optimization-paradigm-match](nw-test-optimization-paradigm-match.md) — Decision rule matching test SHAPE to the right paradigm before authoring/migrating - closed-world vs multi-step-setup vs state-mutation vs unbounded-invariant vs few-examples, plus the falsifier-gate that blocks PBT on finite domains

## nw-test-organization-conventions

- [nw-test-organization-conventions](nw-test-organization-conventions.md) — Test directory structure patterns by architecture style, language conventions, naming rules, and fixture placement. Decision tree for selecting test organization strategy.

## nw-test-refactoring-catalog

- [nw-test-refactoring-catalog](nw-test-refactoring-catalog.md) — Detailed refactoring mechanics with step-by-step procedures, and test code smell catalog with detection patterns and before/after examples

## nw-throughput

- [nw-throughput](nw-throughput.md) — Evidence-led orchestration for maximizing delivery throughput with independent fan-out, capacity-bounded local test runs, long runs batched off the box, and concise whole-value evidence.

## nw-type-level-design

- [nw-type-level-design](nw-type-level-design.md) — Design or review evidence-preserving APIs that model invalid states, state transitions, capabilities, and trusted construction proportionately to the target language.

## nw-typesafe-system-one

- [nw-typesafe-system-one](nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.

## nw-usability-engineering

- [nw-usability-engineering](nw-usability-engineering.md) — Cognitive science principles applied to futuristic interface design -- Fitts, Hick, Miller, cognitive load theory, and Nielsen heuristics

## nw-user-story-mapping

- [nw-user-story-mapping](nw-user-story-mapping.md) — User story mapping knowledge for exploring journeys, release boundaries, activity gaps, and outcome-based prioritization.
