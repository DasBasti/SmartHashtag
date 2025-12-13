# Linting Guide for Copilot Agents

This document explains how to test for linting errors in this repository to avoid issues in pull requests.

## Overview

This repository uses multiple linting tools to ensure code quality:

- **ruff**: Fast Python linter and formatter
- **flake8**: Additional Python linting
- **pre-commit**: Runs all linting tools in a consistent way
- **prettier**: For formatting non-Python files (JSON, YAML, etc.)

## Quick Reference

### Before Submitting a PR

**Always run these commands before committing:**

```bash
# 1. Run pre-commit on all files (this is what CI uses)
pre-commit run --all-files

# 2. If any files were modified, commit them
git add .
git commit -m "Fix linting errors"

# 3. Run tests to ensure nothing broke
python -m pytest tests/
```

## Detailed Instructions

### 1. Install Required Tools

```bash
pip install -r requirements_test.txt
pip install pre-commit ruff flake8
```

### 2. Run Linting Checks

#### Option A: Using pre-commit (Recommended - matches CI exactly)

```bash
# Run all linting checks
pre-commit run --all-files

# If this modifies any files, check what changed
git diff

# Add and commit the changes
git add .
```

#### Option B: Run individual linters

```bash
# Run ruff linter
ruff check .

# Auto-fix ruff issues
ruff check --fix .

# Run ruff formatter
ruff format .

# Run flake8
flake8
```

### 3. Understanding Common Errors

#### PT001: Use `@pytest.fixture` over `@pytest.fixture()`

This error means pytest fixtures should NOT have parentheses when they don't take arguments.

**Wrong:**

```python
@pytest.fixture()
def my_fixture():
    pass
```

**Correct:**

```python
@pytest.fixture
def my_fixture():
    pass
```

**Exception:**

```python
@pytest.fixture(autouse=True)  # Parentheses required when passing arguments
def my_fixture():
    pass
```

#### PT023: Use `@pytest.mark.` without parentheses

This is already ignored in our ruff.toml configuration.

### 4. Pre-commit Configuration

The repository uses `.pre-commit-config.yaml` to configure pre-commit hooks. Key settings:

- **ruff version**: Must match the version used in CI (currently v0.14.9)
- **ruff args**: `--fix` to automatically fix issues
- **Other hooks**: check-yaml, trailing-whitespace, end-of-file-fixer, prettier

### 5. Troubleshooting

#### Pre-commit and ruff versions mismatch

If you see different results between `ruff check .` and `pre-commit run`, check versions:

```bash
# Check installed ruff version
ruff --version

# Check pre-commit ruff version
grep -A2 "astral-sh/ruff" .pre-commit-config.yaml
```

The versions should match. Update `.pre-commit-config.yaml` if needed.

#### Cache issues

If pre-commit is behaving strangely, clear the cache:

```bash
pre-commit clean
pre-commit run --all-files
```

## Best Practices for Copilot Agents

1. **Always run pre-commit before committing**: This ensures your code passes the same checks as CI
2. **Check git diff after linting**: Sometimes linters auto-fix files; make sure to commit those changes
3. **Run tests after fixing linting**: Ensure linting fixes didn't break anything
4. **Update this document**: If you find new linting issues or solutions, update this guide

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/tests.yml`) runs:

- Pre-commit hooks (including ruff, flake8, prettier)
- Pytest test suite
- HACS validation
- Hassfest validation

All of these must pass before a PR can be merged.

## Quick Checklist

- [ ] Installed all linting tools (`pip install -r requirements_test.txt pre-commit ruff flake8`)
- [ ] Ran `pre-commit run --all-files`
- [ ] Committed any files that were auto-fixed
- [ ] Ran `python -m pytest tests/` to ensure tests pass
- [ ] Checked `git status` to ensure no unexpected changes
- [ ] Ready to commit and push!
