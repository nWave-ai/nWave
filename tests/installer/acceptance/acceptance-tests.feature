# Feature: nWave Framework Rationalization for Open Source Publication

**Wave:** DISTILL
**Status:** Phase 0 - Agent and Template Rationalization
**Previous Wave:** DESIGN (architecture.md)
**Next Wave:** DEVELOP

---

# Phase 0: Agent and Template Rationalization

## Background: Foundation for Consistent Command/Task Creation
  Given the nWave framework uses agent-builder to create agents
  And the nWave framework uses commands to delegate to specialized agents
  And all commands should follow consistent minimal delegation patterns
  And command template defines the structure for command creation

## Scenario: Command template improved through research-based analysis
  @skip
  Given the researcher agent analyzes all existing commands
  When command template compliance analysis completes
  Then analysis report identifies commands exceeding 60-line limit
  And analysis report lists commands with embedded workflows
  And analysis categorizes patterns by frequency
  And command template is updated based on top violations
  And agent-builder-reviewer validates the updated template

## Scenario: Agent-builder enhanced with command creation capability
  @skip
  Given command template has been improved and validated
  When agent-builder dependencies are updated
  Then command template is referenced in dependencies
  And the forge-command capability is added to agent-builder
  And command creation guidance is added to the builder pipeline
  And documentation explains how to create minimal delegation commands

## Scenario: Agent-builder-reviewer validates command template compliance
  Given agent-builder creates a new command using command template
  When agent-builder-reviewer performs peer review
  Then the reviewer validates command size is 50-60 lines
  And the reviewer ensures zero workflow duplication
  And the reviewer confirms explicit context bundling is present
  And the reviewer verifies agent invocation pattern is used
  And critical violations block approval
  And the reviewer provides actionable feedback for non-compliant commands

## Scenario: New commands follow template structure consistently
  @skip
  Given agent-builder has command template in dependencies
  And agent-builder-reviewer validates template compliance
  When a developer creates a new command via forge capability
  Then the generated command is 50-60 lines in length
  And the command contains zero workflow implementation
  And the command bundles context with pre-discovered file paths
  And the command uses proper agent invocation pattern
  And the command passes reviewer validation

## Scenario: Command template validation fails for non-compliant command
  @skip
  Given agent-builder creates a command with embedded workflow
  When agent-builder-reviewer validates the command
  Then the reviewer detects embedded procedural steps
  And the reviewer blocks approval with actionable feedback
  And the feedback identifies where to move the embedded workflow
  And the feedback provides specific remediation steps

---

# Quality Gates Phase: Comprehensive Validation Before Handoff

## Background: Quality Gate Requirements for Production Readiness
  Given all previous phases have completed their work
  And the framework demonstrates command/task consistency
  And agents have clear delegation boundaries
  And acceptance criteria from all phases must be validated
  And no work can proceed to DEVELOP without passing all quality gates

## Scenario: Phase 0 command template compliance validation passes
  @skip
  Given command template has been analyzed and improved
  And agent-builder uses the improved template
  When quality gate validation runs for Phase 0
  Then all commands comply with the 50-60 line target
  And no command contains embedded orchestration workflows
  And all commands have ORCHESTRATOR BRIEFING sections
  And context bundling is explicit and complete
  And command template compliance checker passes

## Scenario: Phase 1 platform abstraction validation passes
  @skip
  Given the platform abstraction layer has been implemented
  And both JSON and YAML formatters have been created
  When quality gate validation runs for Phase 1
  Then JSON formatter produces valid output structure
  And YAML formatter produces valid output structure
  And formatters handle all tested scenarios correctly
  And shared content library shows no conflicts
  And platform abstraction tests all pass

## Scenario: Phase 2 shared content integration validation passes
  @skip
  Given agent specifications and command files have been created
  And shared content has been embedded in both
  When quality gate validation runs for Phase 2
  Then agent-builder references are consistent across files
  And command task descriptions match agent responsibilities
  And no content duplication exists between agent and command
  And shared content updates propagate correctly
  And integration tests show zero conflicts

## Scenario: Phase 3 wave handoff directory structure validation passes
  @skip
  Given wave handoff infrastructure has been created
  And directory structure follows the defined pattern
  When quality gate validation runs for Phase 3
  Then docs/features/framework-rationalization directories exist
  And all expected subdirectories (00-discuss through 04-develop) exist
  And handoff artifacts are in correct locations
  And index files reference all phases correctly
  And cross-phase traceability is maintained

## Scenario: Phase 4 pre-commit hook validation passes
  @skip
  Given pre-commit hooks have been implemented
  And hooks validate framework structure requirements
  When quality gate validation runs for Phase 4
  Then hooks detect command template violations
  And hooks catch embedded workflow patterns
  And hooks validate ORCHESTRATOR BRIEFING presence
  And hooks warn about non-compliant new files
  And hook validation can be bypassed only with explicit override

## Scenario: Phase 5 release packaging validation passes
  @skip
  Given release packaging has been configured
  And checksums have been generated for artifacts
  When quality gate validation runs for Phase 5
  Then release tarball contains all required files
  And checksum validation passes for all artifacts
  And version information is consistent
  And release notes document changes accurately
  And packaging process is repeatable

## Scenario: Phase 6 CI/CD workflow validation passes
  @skip
  Given CI/CD workflows have been implemented
  And workflows run framework validation automatically
  When quality gate validation runs for Phase 6
  Then GitHub Actions workflows execute successfully
  And command template validation step passes
  And agent specification validation step passes
  And pre-commit hook testing passes
  And CI/CD reports clear success status

## Scenario: All quality gates pass before DEVELOP wave handoff
  @skip
  Given all Phase 0-6 validations have completed successfully
  And all acceptance criteria from all phases are satisfied
  And all tests are executable and initially failing
  And tests use business language understandable by stakeholders
  When the quality gate validator aggregates all results
  Then all 6 phases show PASSED status
  And no critical violations remain
  And DEVELOP wave handoff is authorized
  And framework is ready for outside-in TDD development

---

# Production Integration Validation Phase

## Scenario: Service provider pattern implemented correctly
  @skip
  Given step definitions have been created for acceptance tests
  When step method implementation is validated
  Then each step method contains _serviceProvider.GetRequiredService calls
  And no step method implements business logic directly
  And all service dependencies are properly injected
  And step methods delegate all operations to production services
  And production service call validation passes

## Scenario: Test infrastructure boundaries enforced
  @skip
  Given test infrastructure and step definitions exist
  When test infrastructure validation runs
  Then no business logic exists in test setup/teardown
  And test infrastructure contains only setup and cleanup code
  And test data builders use production services to create data
  And no direct database manipulation in test infrastructure
  And anti-pattern detection confirms no infrastructure deception

## Scenario: Build system uses real implementations
  @skip
  Given build system and platform abstraction have been implemented
  When production integration validation runs
  Then build system is a real implementation, not a mock
  And platform formatters are real implementations, not stubs
  And integration between formatter and build occurs naturally
  And no test doubles replace core domain services
  And production code path execution is verified

## Scenario: External system boundaries properly mocked
  @skip
  Given the test environment has been configured
  When external system integration is validated
  Then only external service boundaries use test doubles
  And external service mocks simulate realistic behavior
  And mock boundaries are clearly documented
  And internal application services use real implementations
  And integration with real services is validated

## Scenario: Tests fail when production services unavailable
  @skip
  Given acceptance tests with production service dependencies
  When production services become unavailable
  Then tests fail with clear error messages
  And failures indicate missing service dependencies
  And test failure provides diagnostic information
  And no tests pass silently with mocked alternatives
  And real system behavior is validated through service availability

## Scenario: Production service integration validated
  Given step methods and test infrastructure have been implemented
  When production integration validation runs
  Then service provider pattern is consistently applied
  And no business logic exists in test infrastructure
  And all production services are real implementations
  And only external boundaries use test doubles
  And tests fail when production services are unavailable

---

# Phase 4: Pre-commit Hooks Integration

## Scenario: Pre-commit hook detects conflicting file changes
  @skip
  Given related files (agent specification and command file) exist in git index
  When pre-commit hook runs conflict detection
  Then hook displays conflict detected warning
  And hook suggests manual review before commit
  And hook shows specific discrepancy details
  And hook exits with warning status (non-blocking)

## Scenario: Code formatter unavailable during pre-commit
  @skip
  Given code formatter tools (ruff/mypy) are configured
  When code formatter tool is not installed
  Then hook fails with formatter not found error
  And hook provides installation instructions
  And hook suggests alternative formatter configurations
  And hook exits with error status (blocking)

---

# Cross-Phase E2E Integration Validation

## Scenario: Complete wave workflow execution
  @skip
  Given the nWave framework is configured for cross-phase integration
  When the DEVELOP wave execution workflow is triggered
  Then DISCUSS phase outputs are discoverable and documented
  And DESIGN wave references DISCUSS outputs
  And DISTILL wave references DESIGN outputs
  And DEVELOP wave references DISTILL outputs
  And pre-commit hook validates wave handoff integrity

## Scenario: Complete release workflow from commit to installation
  @skip
  Given the codebase has passed all acceptance tests
  When a code commit is pushed to the repository
  Then code commit triggers CI/CD pipeline
  And tests pass in CI environment
  And build artifact is created
  And release package is generated with checksums
  And package is uploaded to release repository
  And user can download package
  And user can extract package without errors
  And installation completes successfully
  And backup of previous version is created

## Scenario: Same command executed on different platforms produces identical output
  @skip
  Given agent specifications are defined for command interface
  When the same command is executed on Claude Code
  And the same command is executed on Codex
  Then output structure is identical on all platforms
  And output values are identical except for platform-specific metadata
  And differences are only in metadata fields

## Scenario: New command created from template complies with structure constraints
  @skip
  Given agent-builder has command template in dependencies
  When a developer creates a new command via forge capability
  Then command is 50-60 lines in length
  And command contains zero workflow implementation
  And command bundles context with pre-discovered file paths
  And command uses proper agent invocation pattern
  And command passes template compliance checker

## Scenario: Multi-platform build fails on path handling incompatibility
  @skip
  Given cross-platform build infrastructure is configured
  When build system processes file paths
  Then path normalization handles format correctly
  Or build fails with clear path format error
  And error specifies which path caused failure
  And cross-platform path guidelines are provided

## Scenario: Shared content and embedded content conflict on same location
  @skip
  Given shared content library uses BUILD:INCLUDE markers
  And embedded content uses BUILD:INJECT markers
  When both target the same location in a file
  Then resolver fails with marker conflict error
  And error specifies conflicting marker locations
  And suggested resolution separates the markers

## Scenario: Complete wave workflow interrupted mid-execution
  @skip
  Given wave workflow execution has been started
  When execution is interrupted at mid-point
  Then partial progress is saved to recovery file
  And next execution offers resume option
  And user can choose resume or restart
  And no work is lost from interruption

---

# Phase 6: CI/CD Integration and Release Workflow

## Background: CI/CD Pipeline Requirements
  Given the nWave framework requires automated testing on multiple platforms
  And the release workflow must validate code quality before creating releases
  And all platform-specific issues must be detected and reported
  And release artifacts must be properly versioned and tracked

## Scenario: CI workflow validates build on all platforms
  Given CI workflow matrix is configured for Ubuntu, macOS, and Windows
  When code is pushed to master or develop branch
  Then CI validates build on Ubuntu platform
  And CI validates build on macOS platform
  And CI validates build on Windows platform
  And all platform builds complete successfully
  And CI status is reported to pull request

## Scenario: Unix installer dry-run succeeds with valid installation structure
  @skip
  Given nWave installer script is available for Unix platforms
  When installer dry-run is executed
  Then installation structure is validated without making changes
  And dry-run confirms all target directories are accessible
  And dry-run identifies existing installations if present
  And dry-run completes successfully

## Scenario: Windows installer dry-run succeeds with valid installation structure
  @skip
  Given nWave installer PowerShell script is available for Windows
  When installer dry-run is executed on Windows
  Then installation structure is validated without making changes
  And dry-run confirms all target directories are accessible
  And dry-run identifies existing installations if present
  And dry-run completes successfully

## Scenario: Release trigger workflow activates when version tag is created
  @skip
  Given semantic versioning tag pattern is v* (e.g., v1.0.0)
  When a new version tag is pushed to repository
  Then release trigger workflow activates automatically
  And workflow retrieves version from tag
  And workflow extracts release notes from commits since previous tag
  And workflow prepares build artifacts for release

## Scenario: Release build successfully compiles and packages all artifacts
  @skip
  Given release trigger workflow has been activated
  When build process executes
  Then build compiles successfully on all target platforms
  And build packaging creates distributable artifacts
  And build artifacts are tagged with version number
  And checksums are generated for integrity verification

## Scenario: GitHub release is created with artifacts and release notes
  @skip
  Given release build has completed successfully
  When release creation workflow executes
  Then GitHub release is created with appropriate version tag
  And release notes are auto-generated from commit history
  And build artifacts are uploaded to release
  And release is marked as production-ready

## Scenario: Release workflow fails if build errors occur
  @skip
  Given release workflow is executing
  When build process encounters compilation errors
  Then workflow execution stops immediately
  And release is NOT created
  And workflow status shows failure
  And error logs are available for debugging

## Scenario: CI workflow fails due to missing dependencies
  @skip
  Given CI workflow validates dependencies
  When required dependencies are not available
  Then CI fails with missing dependency error
  And failure logs show missing dependency name
  And dependency installation instructions are provided

## Scenario: Release workflow fails when tag version mismatches configuration
  @skip
  Given release workflow validates version consistency
  When tag version does not match package.json or version file
  Then workflow fails with version mismatch error
  And error displays both versions for comparison
  And workflow halts before creating release

## Scenario: Release creation fails due to API rate limiting
  @skip
  Given release workflow creates GitHub release via API
  When GitHub API rate limit is exceeded
  Then API returns rate limit exceeded error
  And workflow logs rate limit reset time
  And retry guidance is provided in error output

## Scenario: Installer dry-run detects existing installation conflicts
  @skip
  Given installer is executed in environment with existing installation
  When installer dry-run detects structural conflicts
  Then installer detects structural conflict
  And installer reports migration required warning
  And installer provides migration guide link
  And installer lists specific conflicting paths
