---
name: nw-ux-tui-patterns
description: Terminal UI and CLI design patterns for product owners. Load when designing command-line tools, interactive terminal applications, or writing CLI-specific acceptance criteria.
disable-model-invocation: true
---

# TUI and CLI Patterns

Actionable terminal interface patterns for requirements gathering and design review. Use when target is CLI tool or interactive terminal application.

## CLI Argument Design

### Command Structure
Follow `program subcommand [flags] [arguments]` (e.g., `git commit -m "message"`).

### Flags and Options
- Both short (`-h`) and long (`--help`) for common flags
- Reserve single-letter flags for frequently used options
- Standard flags always: `--help`, `--version`, `--verbose`/`--quiet`, `--no-color`
- Never accept secrets via flags (use files, stdin, or env vars)
- Make flag order independent

### Subcommands
- Verbs for actions: `create`, `delete`, `list`, `show`, `update`
- Nouns for targets: `user`, `project`, `config`
- Pick one pattern (`tool resource action` or `tool action resource`) consistently
- Provide shell completion scripts for discoverability

### Argument Design Principles
Required arguments are positional; optional use flags. Accept stdin for piping. Support glob patterns for file arguments. Provide `--dry-run` for destructive/complex operations.

## Interactive TUI Patterns

### Framework Architectures

| Framework | Language | Architecture | Best For |
|-----------|----------|-------------|----------|
| **Bubble Tea** | Go | Elm (Model-Update-View) | Full TUI apps with complex state |
| **Rich** | Python | Declarative rendering | Beautiful output, progress, tables |
| **Ink** | JavaScript | React component model | Teams with React experience |
| **Textual** | Python | CSS-like styling, widgets | Dashboard-style applications |
| **Ratatui** | Rust | Immediate-mode rendering | High-performance terminal apps |

### Key Architectural Pattern (Elm Architecture)
- **Model**: Application state (single data structure)
- **Update**: Pure function taking model + message, returns new model
- **View**: Pure function rendering model to string

Unidirectional data flow makes TUI state predictable and testable.

### Interactive Selection Patterns
Arrow keys to navigate, Enter to select. Type-ahead filtering for long lists. Multi-select with space bar, confirm with Enter. Show selected count with clear visual indicator. Support Esc to cancel.

## Color and Formatting

### Color Conventions
**Red**: errors, failures, deletions | **Yellow/amber**: warnings, attention | **Green**: success, confirmations, additions | **Blue/cyan**: information, links, highlights | **Dim/gray**: secondary info, metadata

### Color Rules
- Never use color as only way to convey information (accessibility)
- Respect `NO_COLOR` environment variable (no-color.org)
- Detect TTY: disable color when piped or redirected
- Test with color-blindness simulators (protanopia, deuteranopia)

### Formatting Patterns
Bold for emphasis and headings | Tables for structured data | Indentation for hierarchy | Horizontal rules for section breaks | Unicode box-drawing for visual structure (provide ASCII fallback)

## Error Message Design

Every CLI error answers three questions:

1. **What happened?** Clear, jargon-free description
2. **Why?** The cause or context
3. **What to do?** Concrete next step

### Good Example
```
Error: Could not connect to database at localhost:5432

  The connection was refused. The database server may not be
  running or is not accepting connections on this port.

  Try:
    1. Check if PostgreSQL is running:  pg_isready -h localhost -p 5432
    2. Start the server:                sudo systemctl start postgresql
    3. Verify the port in config:       cat ~/.config/myapp/database.yaml

  Documentation: https://docs.myapp.com/troubleshooting/database
```

### Bad Example
```
Error: ECONNREFUSED
```

### Error Guidelines
- Never blame user ("You entered invalid..." becomes "The value ... is not valid because...")
- Suggest most likely correction (did-you-mean for typos)
- Exit codes consistent: 0=success, 1=general error, 2=usage error
- Log verbose diagnostics to file, not stderr by default

## Help Text Design

### `--help` Output Structure
```
tool-name - One-line description

USAGE
  tool-name <command> [flags]

COMMANDS
  create    Create a new resource
  list      List existing resources
  delete    Remove a resource

FLAGS
  -h, --help       Show this help message
  -v, --version    Show version information
  -q, --quiet      Suppress non-error output

EXAMPLES
  # Create a new project
  tool-name create my-project --template=web

  # List all projects
  tool-name list --format=table

LEARN MORE
  Documentation:  https://docs.tool-name.com
  Report issues:  https://github.com/org/tool-name/issues
```

### Help Text Principles
Lead with examples (users scan for examples first). Show common commands/flags first. One line per description. Link to detailed docs. Support both `tool help <cmd>` and `tool <cmd> --help`.

## Output Design

### Human-Readable (Default)
Detect TTY: terminal gets colors, tables, progress bars. Disable animations/spinners in non-TTY mode. Use structured formatting (headers, indentation, alignment).

### Machine-Parseable Alternatives
- `--json` for structured output (most important machine format)
- `--plain` or `--tsv` for tabular data compatible with grep, awk, cut
- `--quiet` for scripts needing only exit code

### Output Contract
Once `--json` schema published, treat as API contract. Breaking changes require major version bump or `--output-version` flag.

## Progress and Responsiveness

- Respond within 100ms: output something immediately, especially before network calls
- Spinner for operations 1-5 seconds
- Progress bar with percentage for operations >5 seconds
- Multi-step: `[3/7] Installing dependencies...`
- Make operations idempotent where possible (safe to re-run after interruption)
- Handle Ctrl+C cleanly with proper cleanup

## CLI/TUI Anti-Patterns

| Anti-Pattern | Alternative |
|-------------|-------------|
| Wall of unformatted text | Structured output with headers, tables, color |
| Raw exception stack traces | Caught errors rewritten in human language |
| No --help or misleading help | Comprehensive, example-led help text |
| Requiring interactive input in CI/CD | Detect non-TTY and accept flags/env vars |
| Breaking JSON output between versions | Treat machine output as versioned API contract |
| Secrets accepted via flags | Use files, stdin, or environment variables |
| Color as only information channel | Pair color with text labels or symbols |

## CLI/TUI Review Checklist

### Discoverability
- [ ] --help produces useful, example-led output
- [ ] Subcommands use consistent verb/noun patterns
- [ ] Shell completion scripts available
- [ ] Did-you-mean suggestions for typos

### Output
- [ ] Default output is human-readable with color in TTY
- [ ] --json flag available for machine consumption
- [ ] Color never only way to convey information
- [ ] NO_COLOR environment variable respected
- [ ] Animations disabled in non-TTY mode

### Error Handling
- [ ] Errors answer: what happened, why, what to do
- [ ] No raw stack traces in user-facing output
- [ ] Exit codes consistent (0=success, 1=error, 2=usage)
- [ ] Suggestions for common mistakes

### Responsiveness
- [ ] First output within 100ms
- [ ] Spinner for 1-5 second operations
- [ ] Progress bar for longer operations
- [ ] Ctrl+C handled with clean cleanup

### Configuration
- [ ] Precedence: flags > env vars > project config > user config > defaults
- [ ] Secrets never via flags
- [ ] Sensible defaults for all optional config
