# Feature: Milestone 3 - Distribution Convergence & Hardening
# Based on: story-map.md Release 3 (manifest, CI validation, public/private filtering, distribution convergence)
# Stories covered: US-07, US-08, US-09, US-10, US-11, US-12
# Date: 2026-03-15 (updated for converged distribution architecture)

Feature: Skill Distribution Convergence and Hardening
  As a framework maintainer
  I want all 4 distribution targets to converge on a shared module with robust install, uninstall, build, and CI validation
  So that the skill system is consistent, safe for all users, and resilient to errors

  Background:
    Given the nWave source tree contains skill directories
    And the installer plugin is available

  # --- US-07: Manifest-Based Uninstall ---

  Scenario: Manifest created during installation
    Given a clean installation directory exists
    When the skills plugin installs all skills
    Then a manifest file exists in the skills directory
    And the manifest lists every installed skill directory name
    And the manifest entry count matches the installed directory count

  Scenario: Uninstall removes only manifest-listed directories
    Given the manifest lists "nw-tdd-methodology" and 108 other directories
    And the user has a custom skill "my-custom-skill" not in the manifest
    When the skills plugin runs uninstall
    Then "nw-tdd-methodology" directory is removed
    And "my-custom-skill" directory still exists
    And the manifest file is removed

  Scenario: Uninstall without manifest warns and uses legacy fallback
    Given no manifest file exists
    And the old "nw/" namespace directory exists
    When the skills plugin runs uninstall
    Then a warning is logged about the missing manifest
    And the old "nw/" directory is removed
    And no nw-prefixed flat directories are removed

  Scenario: Re-install overwrites manifest with current state
    Given a manifest exists from a previous installation with 100 entries
    When the skills plugin installs 109 skills
    Then the manifest contains exactly 109 entries
    And the old 100-entry manifest is replaced

  # --- US-08: Build Distribution ---

  Scenario: Build produces flat skill layout in distribution
    Given the source tree has skills in nw-prefixed directories
    When the distribution build runs
    Then the dist directory contains skill directories without nw/ wrapper
    And each skill directory in dist contains a SKILL.md file
    And no "skills/nw/" path exists in the distribution

  Scenario: Installer handles new flat distribution layout
    Given the distribution contains "nw-tdd-methodology/SKILL.md" in the flat layout
    When the skills plugin detects the distribution layout
    Then it copies from the flat skills directory
    And installation succeeds with the correct file count

  Scenario: Installer handles old distribution layout for backward compatibility
    Given the distribution contains skills in the old "nw/" wrapper layout
    When the skills plugin detects the distribution layout
    Then it uses the legacy copy logic
    And installation succeeds

  # --- US-09: CI Validation ---

  Scenario: CI detects agent referencing non-existent skill
    Given an agent lists "nonexistent-skill" in its frontmatter
    And no directory named "nw-nonexistent-skill" exists
    When CI validation runs the skill-agent consistency check
    Then the check fails
    And the error names the agent and the missing skill

  Scenario: CI warns about orphan skill directories
    Given a skill directory "nw-experimental-technique" exists
    And no agent references "nw-experimental-technique" in its frontmatter
    When CI validation runs the skill-agent consistency check
    Then a warning is emitted for the orphan skill
    And the check does not fail

  Scenario: CI passes when all skill-agent mappings are correct
    Given every agent skill reference has a matching directory
    And every skill directory is referenced by at least one agent
    When CI validation runs the skill-agent consistency check
    Then the check passes with no errors or warnings

  Scenario: CI enforces nw-prefix on all skill directories
    Given a skill directory without the "nw-" prefix exists
    When CI validation runs the naming convention check
    Then the check fails
    And the error identifies the non-compliant directory name

  # --- ADR-003: Public/Private Skill Filtering ---

  Scenario: Private agent skills excluded from public installation
    Given the workshopper agent is marked as private in the catalog
    And the workshopper agent has 11 skills in its frontmatter
    When the skills plugin installs for a public distribution
    Then none of the workshopper's skills are installed
    And only public agent skills are present in the target

  Scenario: Skill shared between public and private agents is included
    Given a skill is referenced by both a public and a private agent
    When the skills plugin filters for public distribution
    Then the skill is included because at least one owner is public

  Scenario: Ownership map built correctly from agent frontmatter
    Given all agent definitions have skills listed in frontmatter
    When the skill-to-agent ownership map is built
    Then every skill directory has at least one owning agent
    And the map correctly identifies multi-agent ownership

  Scenario: Filtering falls back gracefully when catalog is missing
    Given the framework catalog file does not exist
    When the skills plugin attempts to filter skills
    Then all skills are treated as public
    And installation proceeds without errors

  # --- US-10: End-to-End Verification ---

  Scenario: Post-install verification confirms all skills are present
    Given the skills plugin has completed installation
    When the verification check runs
    Then the expected number of SKILL.md files exist
    And each file is non-empty
    And each agent's skill list entries match installed directory names

  Scenario: Docker verification container validates skill layout
    Given a clean Docker container runs the installer
    When the verification suite runs
    Then all skill directories are created
    And the skill count matches the expected total
    And no files exist in the old namespace path

  # --- Agent Builder Output Paths ---

  Scenario: Agent builder produces skills in nw-prefixed SKILL.md format
    Given the agent builder creates a new agent with skills
    When the builder outputs the skill files and agent definition
    Then skills are created at "nWave/skills/nw-{name}/SKILL.md" paths
    And the agent frontmatter lists skills with "nw-" prefixed names
    And the Skill Loading section uses "~/.claude/skills/nw-{skill}/SKILL.md" Read paths

  # --- Error and Edge Cases ---

  Scenario: Manifest with extra entries does not cause errors during uninstall
    Given the manifest lists a directory that no longer exists on disk
    When the skills plugin runs uninstall
    Then the missing directory is silently skipped
    And all other listed directories are removed
    And uninstall completes successfully

  Scenario: Interrupted installation produces partial but valid manifest
    Given installation was interrupted after installing 50 of 109 skills
    When the manifest is inspected
    Then the manifest lists the 50 successfully installed directories
    And subsequent uninstall removes only those 50 directories

  Scenario: Build distribution excludes private agent skills
    Given private agents have skills in the source tree
    When the distribution build runs
    Then private skills are not included in the dist directory
    And the dist skill count matches the public-only count

  # --- US-11: Plugin Builder Convergence ---

  Scenario: Plugin build produces flat nw-prefixed skill layout
    Given the source tree has skills in nw-prefixed directories
    When the plugin build runs
    Then the plugin directory contains nw-prefixed skill directories
    And each skill directory contains a SKILL.md file
    And no agent-grouped skill directories exist in the plugin output

  Scenario: Plugin build does not generate SKILL.md index files
    Given the source tree has skills with individual SKILL.md files
    When the plugin build runs
    Then no generated SKILL.md index files exist
    And only source SKILL.md files are present

  Scenario: Plugin build does not rewrite agent skill references
    Given agent definitions reference individual nw-prefixed skills in frontmatter
    When the plugin build runs
    Then agent frontmatter in plugin output is unchanged from source
    And no bundle-name rewriting occurs

  Scenario: Plugin build excludes private agent skills
    Given private agents have skills in the source tree
    When the plugin build runs with public filtering
    Then none of the private agents' skills appear in the plugin output

  Scenario: Plugin validation passes with flat skill layout
    Given the plugin has been built with the flat nw-prefixed layout
    When plugin validation runs
    Then the skills section validation passes
    And the agent count and skill count are reported correctly

  # --- US-12: OpenCode Distribution Convergence ---

  Scenario: OpenCode install produces nw-prefixed skill directories
    Given the source tree has skills in nw-prefixed directories
    When the OpenCode skills plugin installs
    Then skills are installed to the OpenCode skills directory
    And each installed skill directory has the nw- prefix
    And each directory contains a SKILL.md file

  Scenario: OpenCode install does not perform collision detection
    Given the source tree has skills with pre-resolved collision names
    When the OpenCode skills plugin installs
    Then no collision detection or target name resolution is performed
    And installation completes without any name resolution warnings

  Scenario: OpenCode install does not rewrite SKILL.md frontmatter
    Given skills have frontmatter names matching their directory names
    When the OpenCode skills plugin installs
    Then SKILL.md content is byte-identical to the source
    And no frontmatter rewriting occurs

  Scenario: OpenCode manifest uses nw-prefixed names
    Given the OpenCode skills plugin completes installation
    Then the manifest file lists nw-prefixed directory names
    And the manifest format is compatible with the shared module

  Scenario: OpenCode upgrade from non-prefixed to nw-prefixed layout
    Given an existing OpenCode installation with non-prefixed skill directories
    And a manifest listing the old non-prefixed names
    When the OpenCode skills plugin installs the new version
    Then old manifest-listed directories are removed
    And new nw-prefixed directories are installed
    And the manifest is updated with nw-prefixed names

  Scenario: OpenCode and Claude Code produce consistent layouts
    Given the same source tree is used for both installations
    When the Claude Code skills plugin and OpenCode skills plugin both install
    Then both target directories contain the same set of nw-prefixed skill names
    And both contain identical SKILL.md content for each skill

  # --- Shared Distribution Module ---

  Scenario: Shared module enumerate_skills lists all nw-prefixed directories
    Given the source tree has 109 nw-prefixed skill directories
    When enumerate_skills is called on the source directory
    Then it returns exactly 109 entries
    And each entry starts with "nw-"

  Scenario: Shared module filter_public_skills excludes private skills
    Given the ownership map shows skill X belongs only to a private agent
    When filter_public_skills is called
    Then skill X is excluded from the result
    And all skills owned by at least one public agent are included

  Scenario: Shared module copy_skills copies directories to target
    Given a list of 5 nw-prefixed source directories
    When copy_skills is called with a target path
    Then 5 nw-prefixed directories exist under the target path
    And each contains a SKILL.md file identical to the source

  Scenario: Shared module write_manifest creates correct format
    Given a list of installed skill names
    When write_manifest is called
    Then a .nwave-manifest.json file is created
    And it contains an "installed_skills" array with the skill names
    And it contains a "version" field

  # --- Cross-Target Consistency ---

  Scenario: All 4 distribution targets converge on identical nw-prefixed layout
    Given the source tree contains nw-prefixed skill directories
    When all distribution targets are built from the same source
    Then all targets contain identical nw-prefixed directory names
    And all targets contain identical SKILL.md content for each skill
