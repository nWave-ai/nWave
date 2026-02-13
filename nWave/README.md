<!-- version: 1.5.2 -->

# nWave Framework

## Overview

The nWave framework implements the comprehensive DISCOVER→DISCUSS→DESIGN→DEVOP→DISTILL→DELIVER methodology. This framework provides a streamlined, integrated workflow with complete knowledge preservation for critical technical execution agents and comprehensive 5-layer testing framework.

## nWave Methodology

The nWave methodology implements a systematic approach to software development through six distinct waves:

1. **DISCOVER**: Evidence-based product discovery and market validation
2. **DISCUSS**: Requirements gathering and business analysis
3. **DESIGN**: Architecture design with visual representation
4. **DEVOP**: Platform readiness, CI/CD, infrastructure, and deployment design
5. **DISTILL**: Acceptance test creation and business validation scenarios
6. **DELIVER**: Outside-In TDD implementation with production readiness validation

## Core and Specialist Agents (10 Total)

### 🌊 nWave Core Agents

1. **product-discoverer** → DISCOVER wave (evidence-based discovery)
2. **business-analyst** → DISCUSS wave (requirements gathering)
3. **solution-architect** → DESIGN wave (architecture & technology)
4. **acceptance-designer** → DISTILL wave (test scenarios)
5. **test-first-developer** → DELIVER wave (outside-in TDD)
6. **feature-completion-coordinator** → DELIVER wave (production readiness)

### 🔧 Specialist Agents (Standalone & Collaborative)

7. **systematic-refactorer** → Essential for Level 1-6 refactoring
8. **mikado-refactoring-specialist-enhanced** → Complex refactoring roadmaps
9. **root-cause-analyzer** → Debugging, post-mortem, problem research
10. **architecture-diagram-manager** → Visual architecture maintenance & updates

## Command Structure

### nWave Core Commands (DW Prefix)

- `/nw:discover [product-concept]` - Wave 1: Evidence-based product discovery
- `/nw:discuss [requirements]` - Wave 2: Business analysis
- `/nw:design [system-context]` - Wave 3: Architecture design
- `/nw:devops [deployment-target]` - Wave 4: Platform readiness and infrastructure
- `/nw:distill [acceptance-criteria]` - Wave 5: Test scenarios
- `/nw:deliver [feature-description]` - Wave 6: Outside-In TDD implementation

### Specialist Commands

- `/nw:mikado [target] [options]` - Complex refactoring roadmaps
- `/nw:root-why [problem-description]` - Root cause analysis & debugging
- `/nw:diagram [scope] [action]` - Architecture diagram management

## Knowledge Preservation Guarantee

This expansion pack implements **ZERO KNOWLEDGE REDUCTION** for the three critical technical execution agents:

- **test-first-developer**: Complete 925-line methodology preserved
- **systematic-refactorer**: COMPLETE refactoring mechanics database (24 techniques + safety protocols)
- **mikado-refactoring-specialist-enhanced**: Full enhanced methodology with discovery tracking

## Workflow Templates

### Greenfield Development

Complete greenfield project development with full visual architecture lifecycle.

### Brownfield Integration

Legacy system enhancement with visual refactoring roadmaps and systematic improvement.

### Rapid Prototyping

Streamlined validation workflow with essential visual architecture and accelerated feedback.

## Architecture Diagram Integration

The architecture-diagram-manager provides complete visual architecture lifecycle management:

- **Creation**: Architecture diagrams from solution-architect decisions
- **Evolution**: Real-time updates throughout development
- **Validation**: Visual verification against implementation
- **Synchronization**: Coordination with refactoring and development progress

## Installation

1. Place this framework in your nWave installation:

   ```
   nwave/nWave/
   ```

2. Update your configuration to include the nWave framework.

3. Agents will be available via the standard agent syntax.

## Usage Examples

### Execute Full nWave Cycle

**Option 1: Automated DELIVER Wave (Recommended)**
```bash
/nw:discover "User authentication market research"
/nw:discuss "User registration and login requirements"
/nw:design "Microservices with JWT authentication"
/nw:distill "User can register and login securely"
/nw:devops "user-authentication"
/nw:distill "User can register and login securely"
/nw:deliver "Implement user authentication with JWT"
  # Automatically: roadmap → execute all steps → finalize
  # Quality gates: 3 + 3N reviews (e.g., 10 steps = 33 reviews)
```

**Option 2: Manual Granular Control (Advanced)**
```bash
# DISCOVER and DISCUSS and DESIGN waves
/nw:discover "User authentication market research"
/nw:discuss "User registration requirements"
/nw:design "JWT authentication architecture"

# DELIVER wave - manual orchestration
/nw:roadmap @solution-architect "Implement user authentication"

# Execute individual steps with 11-phase TDD
/nw:execute @software-crafter "docs/feature/user-authentication/steps/01-01.json"
/nw:execute @software-crafter "docs/feature/user-authentication/steps/01-02.json"
# ... (repeat for all steps)

/nw:finalize @platform-architect "user-authentication"

# DELIVER wave
/nw:deliver "user-authentication"
```

**Option 3: Execute Single Step with Complete 11-Phase TDD**
```bash
# For executing one specific step with full TDD workflow
/nw:execute @software-crafter "docs/feature/user-auth/steps/01-02.json"
  # Automatic: PREPARE → RED → GREEN → REVIEW → REFACTOR → VALIDATE → COMMIT
  # Includes mandatory reviews and progressive refactoring (L1-L4)
```

### Complex Refactoring with Visual Tracking

```
/nw:mikado "legacy-auth-modernization" --with-diagrams
/nw:diagram mikado-tree "auth-refactoring" --visualize-dependencies
```

### Walking Skeleton with Architecture Validation

```
/nw:diagram skeleton "user-auth" --minimal-slice
```

## Quality Assurance

- Complete knowledge preservation for technical execution agents
- Zero-risk refactoring with comprehensive safety protocols
- Visual architecture validation throughout development lifecycle
- Full integration with nWave core functionality
- 5-layer testing framework including mutation testing (Layer 5)

## Support

This framework provides complete functionality through the proven nWave methodology with comprehensive visual architecture integration.

Join the **[nWave Discord community](https://discord.gg/DeYdSNk6)** to get help, share ideas, and showcase what you've built with the framework.
