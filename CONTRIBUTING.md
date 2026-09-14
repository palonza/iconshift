# Contributing to IconShift

Thank you for your interest in contributing to **IconShift**! 

IconShift is an open-source Python toolkit for auditing, resolving, generating, and adapting application icons for Linux desktop environments according to the Freedesktop specifications.

We welcome contributions from developers of all skill levels, whether you are fixing a bug, adding new desktop environment support, improving documentation, or proposing new features.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Design Principles](#design-principles)
- [Development Setup](#development-setup)
- [Workflow & Branching](#workflow--branching)
- [Architecture Overview](#architecture-overview)
- [Coding Guidelines](#coding-guidelines)
- [Testing](#testing)
- [Commit Message Conventions](#commit-message-conventions)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Build & Release Commands](#build--release-commands)

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please treat all contributors and maintainers with respect, empathy, and constructive feedback.

---

## Design Principles

When contributing code to IconShift, keep these core principles in mind:

1. **Zero External Runtime Dependencies:**
   IconShift's core functionality relies entirely on Python's standard library (Python 3.10+). Do not introduce third-party runtime dependencies into `pyproject.toml` unless discussed and approved.
2. **Safety and Non-Destructive Defaults:**
   IconShift must never overwrite system-managed files under `/usr/` without explicit flags. User-space installation (`~/.local/share/icons/`) is always the default.
3. **Freedesktop Standards Compliance:**
   IconShift adheres strictly to the Freedesktop Icon Theme Specification and Desktop Entry Specification.
4. **Unix Philosophy:**
   Output should be clean, modular, and pipeline-friendly (`tsv`, `csv`, `json`, `paths`, `icons`).

---

## Development Setup

### Prerequisites

- **Linux** (Arch Linux, Fedora, Ubuntu, or Debian)
- **Python 3.10+**
- **uv** (recommended package and environment manager) or Python `venv`
- **git**

### Setting Up the Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/palonza/iconshift.git
   cd iconshift
   ```

2. **Synchronize dependencies with `uv`:**
   ```bash
   uv sync
   ```

3. **Verify the development CLI:**
   ```bash
   uv run iconshift --help
   ```

4. **Run the test suite:**
   ```bash
   uv run pytest -v
   ```

---

## Workflow & Branching

We use standard feature-branch workflows:

1. Fork the repository and clone your fork.
2. Create a dedicated branch off `main`:
   ```bash
   git checkout -b feat/my-new-feature
   # or
   git checkout -b fix/resolve-fallback-symlink
   ```
3. Use descriptive branch prefixes:
   - `feat/`: New features or capabilities.
   - `fix/`: Bug fixes.
   - `docs/`: Documentation additions or edits.
   - `refactor/`: Code improvements that do not change external behavior.
   - `test/`: Adding or improving tests.
   - `chore/`: Build configuration, dependencies, or maintenance.

---

## Architecture Overview

IconShift follows classic, modular object-oriented design patterns:

- **Command Pattern (`src/iconshift/commands.py`):**
  Each CLI action (`scan`, `generate`, `palette`) is implemented as an independent Command class implementing `execute()`.
- **Chain of Responsibility (`src/iconshift/resolver.py`):**
  Icon discovery is implemented via a chain of resolver links (`TargetThemeLink` → `InheritedThemesLink` → `PixmapsLink`) that inspect `index.theme` inheritance (`Inherits=`) and standard paths.
- **Strategy Pattern (`src/iconshift/colorizer.py`):**
  SVG color transformation algorithms are pluggable strategies (`MonochromeStrategy`, `TwoToneStrategy`, `AdaptiveStrategy`) inheriting from `SVGColorizerStrategy`.
- **XML / SVG Manipulation (`src/iconshift/colorizer.py`):**
  SVG manipulation uses `xml.etree.ElementTree` without altering the geometric definitions, paths, transforms, or viewBox attributes.

---

## Coding Guidelines

- **Python Version:** Code must be compatible with Python 3.10 and later.
- **Type Annotations:** Use Python type hints (`typing`) across all function and method signatures.
- **PEP 8 Compliance:** Keep code clean, readable, and properly formatted.
- **Docstrings & Comments:** Document public functions, classes, and non-obvious algorithms with clear docstrings explaining intent and edge cases.
- **Exception Handling:** Raise specific exceptions (e.g., `FileNotFoundError`, `ValueError`) with actionable error messages rather than catching generic `Exception`.

---

## Testing

IconShift maintains a high test coverage across all commands, resolvers, and SVG transformers.

### Running Unit Tests Locally

Run unit tests and check test coverage with `uv`:

```bash
uv run pytest -v --cov=iconshift --cov-report=term-missing
```

### Running Tests in Isolated VM

The repository provides automated scripts to sync code and run the test suite inside an isolated KVM/QEMU virtual machine (`ulir-dev`):

```bash
make test
# or: ./scripts/test/run_tests_in_vm.sh
```

### Writing New Tests

- All new features and bugfixes must include corresponding unit tests under `tests/`.
- Tests should use temporary directories (`tmp_path` fixture) to simulate file systems and prevent side effects.
- Test SVG parsing using standard fixture strings or mock file trees.

---

## Commit Message Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```text
<type>(<scope>): <short summary>

[optional body explaining context and rationale]

[optional footer(s), e.g., Closes #123]
```

### Allowed Types

- `feat`: A new user-facing feature or CLI option.
- `fix`: A bug fix.
- `docs`: Documentation-only changes.
- `style`: Changes that do not affect the meaning of the code (formatting, white-space).
- `refactor`: Code changes that neither fix a bug nor add a feature.
- `perf`: Performance improvements.
- `test`: Adding missing tests or correcting existing tests.
- `build`: Changes affecting the build system or packaging.
- `ci`: Changes to CI/CD workflows and automated scripts.
- `chore`: Housekeeping, dependency updates, or internal scripts.

### Examples

- `feat(resolver): support recursive XDG_DATA_DIRS icon lookup`
- `fix(commands): ensure index.theme is linked into user theme root`
- `docs: add Arch Linux environment and yay setup guide to README`
- `test(colorizer): add unit tests for two-tone SVG fill replacement`

---

## Submitting a Pull Request

1. **Check your branch:** Ensure all tests pass locally (`uv run pytest`) and code is clean.
2. **Push to your fork:**
   ```bash
   git push origin feat/my-new-feature
   ```
3. **Open a Pull Request:** Navigate to the IconShift GitHub repository and open a PR targeting the `main` branch.
4. **PR Description:**
   - Clearly explain the problem being solved or feature introduced.
   - Reference any related issues (e.g., `Fixes #42`).
   - Describe any manual or automated verification performed.
5. **Review:** Maintainers will review your PR, suggest improvements, and guide it to merge.

---

## Build & Release Commands

The project includes a `Makefile` with common maintenance and automation targets:

| Command | Description |
| :--- | :--- |
| `make build` | Build standalone Linux executable in `dist/iconshift` via PyInstaller |
| `make install` | Install the built binary to `$HOME/.local/bin/iconshift` |
| `make package` | Package the binary into a release tarball and generate SHA-256 |
| `make test` | Execute test suite inside the isolated `ulir-dev` VM |
| `make clean` | Clean build artifacts (`build/`, `dist/`, `release/`, `*.spec`) |
| `make vm-start` | Boot the `ulir-dev` virtual machine |
| `make vm-status` | Display status and IP address of the testing VM |
| `make vm-ssh` | Open an interactive SSH session to the testing VM |
| `make aur-update` | Update Arch Linux AUR `PKGBUILD` and regenerate `.SRCINFO` |

---

## Questions & Getting Help

If you have questions, encountered a problem, or want to discuss a new idea before writing code:
- Open a GitHub Issue for bug reports or feature requests.
- Start a GitHub Discussion for architectural questions or general feedback.
