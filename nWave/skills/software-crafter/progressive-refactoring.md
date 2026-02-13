---
name: progressive-refactoring
description: Progressive L1-L6 refactoring hierarchy, 22 code smell taxonomy, atomic transformations, test code smells, and Fowler refactoring catalog
---

# Progressive Refactoring (Refactoring Priority Premise)

Based on the Refactoring Priority Premise (RPP) from the Alcor Academy curriculum.

## RPP Levels (L1-L6)

Execute levels in mandatory sequence. Lower levels before higher.

### Level 1: Foundation (Readability)
Focus: eliminate clutter, improve naming, remove dead code.
Smells addressed: Dead Code, Comments (how-comments), Speculative Generality, Lazy Class.
Transformations: Rename, Extract (variables/constants), Safe Delete.
Impact: 80% of readability improvement value.
Test smells: Obscure Test, Hard-Coded Test Data, Assertion Roulette.

### Level 2: Complexity Reduction (Simplification)
Focus: method extraction, duplication elimination.
Smells addressed: Long Method, Duplicate Code, Complex Conditionals.
Transformations: Extract (methods), Move (common code).
Impact: 20% additional readability improvement.
Test smells: Eager Test, Test Code Duplication, Conditional Test Logic.

### Level 3: Responsibility Organization
Focus: class responsibilities, coupling reduction.
Smells addressed: Large Class, Feature Envy, Inappropriate Intimacy, Data Class, Divergent Change, Shotgun Surgery.
Transformations: Move, Extract (classes).
Test smells: Test Class Bloat, Mystery Guest, General Fixture.

### Level 4: Abstraction Refinement
Focus: parameter objects, value objects, abstractions.
Smells addressed: Long Parameter List, Data Clumps, Primitive Obsession, Middle Man.
Transformations: Extract (objects), Inline, Move.

### Level 5: Design Pattern Application
Focus: Strategy, State, Command patterns.
Smells addressed: Switch Statements, complex state-dependent behavior.
Transformations: Extract (interfaces), Move (to polymorphic structure).

### Level 6: SOLID++ Principles
Focus: SOLID principles, architectural patterns.
Smells addressed: Refused Bequest, Parallel Inheritance Hierarchies.
Transformations: Extract (interfaces), Move (responsibilities), Safe Delete (violations).

### RPP Cascade Rule
MANDATORY: complete each level fully before moving to the next. Do not skip levels.
80% of refactoring value comes from readability improvements (L1-L2).
Focus effort on L1-L2 for maximum impact. Move to higher levels only when needed.

### Fast-Path for Small Changes
When GREEN phase produced < 30 LOC of new production code:
- Quick scan for obvious naming/duplication issues (2-3 min max)
- Mark COMPLETED with note "fast-path: <30 LOC"

### L4-L6 Timing
L4-L6 architecture refactoring runs at orchestrator Phase 2.25 (once after all steps complete), not during each TDD inner loop.

---

## 22 Code Smell Taxonomy

### Bloaters
| Smell | Detection | Treatment | Level |
|-------|-----------|-----------|-------|
| Long Method | >20 lines, multiple responsibilities | Extract Method, Compose Method | L2 |
| Large Class | >300 lines, too many fields | Extract Class, Extract Subclass | L3 |
| Primitive Obsession | Raw strings for domain concepts, magic numbers | Replace Data Value with Object | L4 |
| Long Parameter List | >=4 parameters | Introduce Parameter Object | L4 |
| Data Clumps | Same parameter groups repeated | Extract Class, Introduce Parameter Object | L4 |

### Object-Orientation Abusers
| Smell | Detection | Treatment | Level |
|-------|-----------|-----------|-------|
| Switch Statements | Switch on type, complex if-else chains | Replace with Polymorphism, Strategy | L5 |
| Temporary Field | Fields empty most of the time | Extract Class, Null Object | L3 |
| Refused Bequest | Subclass doesn't support parent interface | Push Down, Replace Inheritance with Delegation | L6 |
| Alternative Classes, Different Interfaces | Same function, different names | Rename Method, Extract Superclass | L3 |

### Change Preventers
| Smell | Detection | Treatment | Level |
|-------|-----------|-----------|-------|
| Divergent Change | One class changed for different reasons | Extract Class | L3 |
| Shotgun Surgery | Change requires many small changes to many classes | Move Method, Move Field, Inline Class | L3 |
| Parallel Inheritance Hierarchies | Creating subclass requires another subclass | Move Method, Move Field | L6 |

### Dispensables
| Smell | Detection | Treatment | Level |
|-------|-----------|-----------|-------|
| Comments (how-comments) | Comments explaining complex code | Extract Method, Rename Method | L1 |
| Duplicate Code | Same code structure in multiple places | Extract Method, Pull Up Method | L2 |
| Lazy Class | Class with few methods, little functionality | Inline Class, Collapse Hierarchy | L1 |
| Data Class | Only fields and getters/setters | Move Method, Encapsulate Field | L3 |
| Dead Code | Unused variables, methods, classes | Delete unused code | L1 |
| Speculative Generality | Abstractions for future features | Collapse Hierarchy, Inline Class | L1 |

### Couplers
| Smell | Detection | Treatment | Level |
|-------|-----------|-----------|-------|
| Feature Envy | Method uses another object's data more than its own | Move Method, Extract Method | L3 |
| Inappropriate Intimacy | Classes know too much about each other | Move Method, Extract Class, Hide Delegate | L3 |
| Message Chains | a.getB().getC().getD() | Hide Delegate, Extract Method | L3 |
| Middle Man | Class only delegates to another | Remove Middle Man, Inline Method | L4 |

---

## 5 Atomic Transformations

### Rename
Change name without changing behavior. Applies to: variables, methods, classes, fields, parameters.
Safety: use IDE refactoring tools, verify all references updated, run tests, commit.

### Extract
Take portion of code and create new element. Applies to: methods, classes, variables, constants, interfaces.
Safety: identify code, create element with intention-revealing name, move code, replace original with call, test, commit.

### Inline
Replace code element with its implementation. Applies to: methods, variables, classes.
Safety: verify no side effects, replace all calls, remove original, test, commit.

### Move
Relocate code element to different scope or class. Applies to: methods, fields, classes.
Safety: check dependencies, create in target, update references, remove from source, test, commit.

### Safe Delete
Remove unused code elements. Applies to: methods, fields, classes, parameters, variables.
Safety: verify truly unused, check for dynamic references, remove, compile and test, commit.

---

For test code smells (9 smells with detection patterns and before/after examples), load the test-refactoring-catalog skill.

---

## Refactoring Techniques Catalog (Fowler)

### Composing Methods
- **Extract Function**: workhorse refactoring. If you need a comment to explain a block, extract to method with that explanation as name.
- **Compose Method** (Kerievsky): transform method into composition at same abstraction level. Repeated Extract Function until body reads like pseudocode.
- **Inline Function**: remove unnecessary abstraction when body is as clear as name. Use in "inline then re-extract" dance.
- **Replace Temp with Query**: replace temporary variable with method call.

### Moving Features
- **Move Function**: relocate to more appropriate class/module. Addresses Feature Envy.
- **Move Field**: move field to class that uses it most.
- **Extract Class**: decompose Large Class by moving related data+methods to new class.

### Organizing Data
- **Replace Data Value with Object**: turn simple data value into full object. Addresses Primitive Obsession.
- **Introduce Parameter Object**: group parameters that go together. Addresses Long Parameter List.
- **Encapsulate Variable/Collection**: protect data from direct access. Return unmodifiable view.

### Simplifying Conditionals
- **Decompose Conditional**: extract condition + branches to named functions showing intent.
- **Guard Clauses**: handle exceptional cases early, return, leave main logic unnested.
- **Replace Conditional with Polymorphism**: replace type-based conditionals with class hierarchy.

### Refactoring to Patterns (Kerievsky)
Don't design patterns upfront - refactor toward them as needs emerge:
- Extract Method repeatedly -> Compose Method -> Template Method
- Encapsulate Field + Move Method -> Strategy
- Extract Class + Move Method -> Decorator

### Key Principles
- Behavior-preserving: if behavior changes, it's not refactoring
- Automated refactoring (IDE) preferred over manual
- Cohesion and clarity over line-count thresholds
- Function size: Single Responsibility + Consistent Abstraction + Self-Documenting names

---

For complex architectural refactoring, load the mikado-method skill.
