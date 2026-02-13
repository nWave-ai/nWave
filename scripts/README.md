# nWave Scripts Directory

Scripts for nWave framework operations, validation, and installation.

## Directory Structure

```
scripts/
├── hooks/               # Pre-commit and post-commit hooks
│   ├── prevent_shell_scripts.py       # Block shell/PowerShell/batch scripts
│   ├── check_formatter_available.py   # Detect missing formatters
│   ├── check_documentation_freshness.py # Validate docs aren't stale
│   ├── detect_conflicts.py            # Conflicting file detection
│   ├── validate_docs.py               # Documentation version validation
│   ├── validate_tests.py              # Pytest wrapper
│   ├── nwave-tdd-validator.py         # TDD phase completion gate
│   ├── nwave-step-structure-validator.py # Step file structure validation
│   ├── nwave-bypass-detector.py       # Commit bypass audit logger
│   ├── commit-msg                     # Commit message hook (CI)
│   └── commit_msg.py                  # Commit message validation
│
├── validation/          # CI/CD validators
│   ├── validate_yaml_files.py         # YAML syntax validation
│   └── validate_source_frontmatter.py # Source frontmatter validation
│
├── framework/           # Framework operations
│   ├── create_github_tarballs.py       # GitHub Release tarball creator
│   ├── release_validation.py          # Release error detection
│   ├── sync_agent_names.py            # Agent name synchronization
│   └── validate_tdd_phases_ci.py      # CI TDD phase validation
│
├── install/             # Installation system (cross-platform)
│   ├── install_nwave.py               # Main installer
│   ├── uninstall_nwave.py             # Framework removal
│   ├── verify_nwave.py                # Installation verification
│   ├── install_des_hooks.py           # DES hook installer
│   ├── plugins/                       # Modular installation plugins
│   └── README.md                      # Detailed installation docs
│
├── update/              # Update system
│   ├── update_orchestrator.py         # Update workflow coordinator
│   └── backup_manager.py             # Backup creation adapter
│
├── mutation/            # Mutation testing
│   └── generate_scoped_configs.py     # Scoped Cosmic Ray configs
│
├── build_dist.py                      # Build dist/ from source (copy + DES rewrite)
├── local_ci.py                        # Local CI/CD runner
├── testpypi_validation.py             # TestPyPI release validation
├── validate_step_file.py              # Step file schema validator
├── validate_steps_complete.py         # Finalization completeness gate
└── install_nwave_target_hooks.py      # Target project hook installer
```

## Usage

### Pre-Commit Hooks

Hooks run automatically via `.pre-commit-config.yaml`:
```bash
pre-commit run --all-files
```

### Installation

```bash
python scripts/install/install_nwave.py
python scripts/install/uninstall_nwave.py --backup
```

See `scripts/install/README.md` for details.

### Framework Operations

```bash
python scripts/framework/validate_tdd_phases_ci.py    # CI TDD validation
python scripts/framework/create_github_tarballs.py     # Build GitHub tarballs
```

### Local CI

```bash
python scripts/local_ci.py
```
