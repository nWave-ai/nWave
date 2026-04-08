/**
 * Automates the Anthropic Plugin Directory submission form using Playwright.
 * Fills all fields from the submission draft and pauses before submit.
 *
 * Usage: npx playwright test --config=playwright.config.mjs scripts/submit-plugin-form.mjs
 *    or: node scripts/submit-plugin-form.mjs
 */

import { chromium } from "playwright";

const FORM_URL =
  "https://docs.google.com/forms/d/e/1FAIpQLSc31jdYDs_1z649BmFfX85mSSdyTXi0GOLsHD7tWKj0F_k9Dg/viewform";

// ── Submission data (from docs/marketplace/submission-draft.md) ──────────────

const PLUGIN_NAME = "nw";

const DESCRIPTION = `nWave orchestrates 23 specialized AI agents through six development waves: Discover, Discuss, Design, Devops, Distill, and Deliver. You work one feature at a time — each wave is a human-machine loop where the agent produces artifacts and you review, refine, and approve before moving on. The Deliver wave enforces Outside-In TDD: every feature ships with tests, and a runtime guard ensures agents stay on track. A meta-agent (/nw:forge) creates custom agents tailored to your domain. Works equally well for greenfield features and legacy modernization.`;

const TARGET_PLATFORM = "Claude Code";

const GITHUB_REPO = "https://github.com/nWave-ai/nWave";

const COMPANY_URL = "https://github.com/nWave-ai";

const CONTACT_EMAIL = "hello@nwave.ai";

const EXAMPLES = `Example 1: Full lifecycle — from market validation to working code

/nw:discover "team task management"         # Validate the problem exists
/nw:discuss "task assignment and tracking"  # Requirements + user stories
/nw:design --architecture=hexagonal         # Architecture + ADRs
/nw:devops                                  # CI/CD, infrastructure, deployment
/nw:distill "task-assignment"               # BDD acceptance tests (Given-When-Then)
/nw:deliver                                 # TDD implementation

Six waves, six human checkpoints. One feature flows through the entire pipeline — the agent proposes, you decide. Start from Discover for greenfield projects, or jump straight to Deliver for existing codebases. The Deliver phase enforces Outside-In TDD: failing test first, then implementation, then refactor — with automated phase tracking.

Example 2: Create custom agents with the meta-agent

/nw:forge "security auditor for OWASP Top 10 compliance"

The forge agent analyzes your request, researches best practices, generates a complete agent specification (YAML frontmatter + markdown), creates matching skills with domain knowledge, and validates the result against nWave's quality standards. The new agent integrates with the existing wave system — it can be dispatched via /nw:execute and reviewed via /nw:review. Build agents tailored to your team's domain without writing specifications by hand.

Example 3: Modernize legacy code with structured refactoring

/nw:refactor "payments module"              # Systematic: naming → complexity → structure → abstractions
/nw:mikado "migrate from REST to GraphQL"   # Map dependencies, tackle in safe order

Legacy code gets the same structured treatment as greenfield. /nw:refactor walks through four levels — from quick readability fixes to deep abstraction redesign — with an architect planning the target and a crafter (OOP or functional) executing each step under TDD. /nw:mikado handles large-scale changes by mapping what depends on what, so you never break the system mid-migration. Use /nw:rigor to scale quality depth and token cost to match the task.`;

// ── Form automation ─────────────────────────────────────────────────────────

async function fillForm() {
  const browser = await chromium.launch({
    headless: false,
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  });
  const page = await context.newPage();

  console.log("Opening form...");
  await page.goto(FORM_URL, { waitUntil: "networkidle" });

  // Google Forms uses aria labels matching the field labels.
  // All text inputs/textareas can be targeted by their label text.

  console.log("Filling: Plugin Name");
  await page
    .getByRole("textbox", { name: /Plugin Name/i })
    .fill(PLUGIN_NAME);

  console.log("Filling: Plugin Description");
  await page
    .getByRole("textbox", { name: /Plugin Description/i })
    .fill(DESCRIPTION);

  console.log("Selecting: Claude Code");
  await page.getByRole("radio", { name: TARGET_PLATFORM }).click();

  console.log("Filling: GitHub link");
  await page
    .getByRole("textbox", { name: /Link to GitHub/i })
    .fill(GITHUB_REPO);

  console.log("Filling: Company URL");
  await page
    .getByRole("textbox", { name: /Company.*Organization.*URL/i })
    .fill(COMPANY_URL);

  console.log("Filling: Contact Email");
  await page
    .getByRole("textbox", { name: /Primary Contact Email/i })
    .fill(CONTACT_EMAIL);

  console.log("Filling: Plugin Examples");
  await page
    .getByRole("textbox", { name: /Plugin Examples/i })
    .fill(EXAMPLES);

  console.log("\n✅ All fields filled.");
  console.log("📋 Review the form in the browser, then submit manually.");
  console.log("   Press Ctrl+C here when done.\n");

  // Keep browser open until user closes it or presses Ctrl+C
  await new Promise(() => {});
}

fillForm().catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});
