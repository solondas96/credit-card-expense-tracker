# Design Decisions

This file documents assumptions and trade-offs made during development.

## Milestone 1 (Scaffold)
- **Project structure**: Using `src/` layout with `src/ccstmt/` following Python best practices for packaging.
- **Configuration**: Separate YAML files for issuers and categories; .env for secrets and runtime config.
- **Logging directory**: Pre-created at `logs/` with log files managed by Python's RotatingFileHandler (to be added in milestone 8).
- **CLI framework**: Typer with Rich for console output; structured logging added in milestone 8.
