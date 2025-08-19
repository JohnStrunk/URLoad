# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working
with code in this repository.

## Development Commands

**Build and Testing:**

- `./hack/check.sh` - Run all checks (linting, type checking, formatting, and tests)
- `uv run pytest` - Run all tests
- `uv run pytest tests/test_<command>_command.py` - Run tests for specific command
- `uv run pytest tests/test_<command>_command.py::test_function_name` - Run
  specific test
- `uv run ruff check --fix` - Run linter with auto-fix
- `uv run pyright` - Run type checker
- `uv run ruff format` - Format code

**Running the Application:**

- `uv run urload` - Start interactive CLI
- `uv run urload script.txt` - Run commands from file

**Dependency Management:**

- `uv add <package>` - Add runtime dependency
- `uv add --dev <package>` - Add development dependency
- Never modify `uv.lock` directly or use `pip`

## Architecture Overview

URLoad is an interactive CLI tool for web scraping built with a modular
command architecture:

**Core Components:**

- `src/urload/main.py` - Entry point with interactive shell, tab completion,
  and command execution loop
- `src/urload/commands/base.py` - Abstract `Command` class and `CommandError` exception
- `src/urload/url.py` - `URL` class with metadata support (headers) and serialization
- `src/urload/settings.py` - `AppSettings` class using Pydantic with TOML persistence

**Command System:**

- All commands inherit from abstract `Command` base class
- Commands implement `run(args, url_list, settings) -> list[URL]` method
- Each command has `name` and `description` class attributes
- Commands are registered in `main.py:build_command_objs()`
- Commands can raise `CommandError` for user-facing errors

**URL Management:**

- `URL` objects encapsulate both URL string and HTTP headers
- URLs support serialization to/from single-line format with JSON headers
- URL list is the primary data structure passed between commands
- Session directories use 4-digit numeric naming (0000, 0001, etc.)

**Testing Patterns:**

- Each command has corresponding test file: `tests/test_<command>_command.py`
- Tests verify command behavior with various inputs and edge cases
- Use `pytest.CaptureFixture` for testing output
- Test both successful operations and error conditions

**Key Design Patterns:**

- Immutable command execution: commands return new URL lists rather than
  modifying in-place
- Settings auto-save on exit via `atexit.register()`
- Range expansion syntax `[start-end]` in URLs (see `AddCommand`)
- Web scraping uses BeautifulSoup4 for HTML parsing
- Interactive shell with history and tab completion via prompt-toolkit

**Adding New Commands:**

1. Create `src/urload/commands/newcommand.py` inheriting from `Command`
2. Add corresponding test file `tests/test_newcommand_command.py`
3. Register in `main.py:build_command_objs()`
4. Follow existing patterns for argument parsing and error handling
