# Copilot Instructions for SmartHashtag

## Project Overview

This repository contains a **Home Assistant custom integration** for Smart #1 and #3 vehicles. It connects to the Smart vehicle cloud API to retrieve vehicle status, location, charging information, and other telemetry data for use in Home Assistant.

The integration is distributed via [HACS](https://hacs.xyz/) (Home Assistant Community Store) and follows Home Assistant's custom component patterns.

## Tech Stack

- **Language**: Python 3.12+
- **Framework**: Home Assistant custom component
- **Testing**: pytest with pytest-homeassistant-custom-component
- **Linting**: ruff, flake8
- **Formatting**: ruff format, prettier (for non-Python files)
- **Pre-commit**: Configured for automated code quality checks
- **Dependencies**: pysmarthashtag (Python library for Smart vehicle API)

## Project Structure

```
SmartHashtag/
├── custom_components/
│   └── smarthashtag/          # Main integration code
│       ├── __init__.py        # Integration setup and entry point
│       ├── binary_sensor.py   # Binary sensor entities
│       ├── climate.py         # Climate control entities
│       ├── config_flow.py     # Configuration UI flow
│       ├── const.py           # Constants and configuration
│       ├── coordinator.py     # Data update coordinator
│       ├── device_tracker.py  # Vehicle location tracking
│       ├── entity.py          # Base entity classes
│       ├── select.py          # Select entities
│       ├── sensor.py          # Sensor entities
│       ├── manifest.json      # Integration manifest
│       └── translations/      # Localization files
├── tests/                     # Test files
├── scripts/                   # Development scripts
├── .github/                   # GitHub configuration
└── requirements*.txt          # Dependencies
```

## Development Setup

### Prerequisites

- Python 3.12+
- Virtual environment (recommended)

### Setup Commands

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_test.txt

# Install pre-commit hooks
pre-commit install
```

## Building and Testing

### Running Tests

```bash
# Run all tests with coverage
pytest --durations=10 --cov-report term-missing --cov=custom_components/smarthashtag tests/

# Run a specific test file
pytest tests/test_sensors.py

# Run tests with verbose output
pytest -v tests/
```

### Running Linters

```bash
# Run ruff linter
ruff check .

# Run ruff with auto-fix
ruff check --fix .

# Run ruff formatter
ruff format .

# Run all pre-commit checks
pre-commit run --all-files
```

## Code Style Guidelines

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines
- Use type hints for function parameters and return values
- Use `async`/`await` for all asynchronous operations (required by Home Assistant)
- Keep functions focused and single-purpose
- Write docstrings for public classes and functions
- Use constants from `const.py` instead of magic strings/numbers

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions or modifications
- `refactor:` - Code refactoring without functional changes
- `chore:` - Maintenance tasks

See `.copilot-commit-message-instructions.md` for detailed commit message guidelines.

## Adding New Entities

When adding new sensors or entities:

1. Add entity descriptions in the appropriate entity file (e.g., `sensor.py`, `binary_sensor.py`)
2. Update `const.py` if new constants are needed
3. Add translations in `translations/en.json` and other language files
4. Add corresponding tests in the `tests/` directory
5. Update the coordinator if new data fields are required

## Key Files to Understand

- **`coordinator.py`**: Manages data fetching from the Smart API
- **`entity.py`**: Base classes for all entities
- **`const.py`**: All constants, configuration keys, and entity descriptions
- **`manifest.json`**: Integration metadata and dependencies

## Testing Considerations

- Use `pytest-homeassistant-custom-component` fixtures for Home Assistant testing
- Mock external API calls using `conftest.py` fixtures
- Test both successful scenarios and error handling
- Ensure new sensors have corresponding test cases

## Boundaries and Restrictions

### DO NOT

- Modify production configuration files in `.devcontainer/`
- Commit API keys, tokens, or other secrets
- Modify GitHub Actions workflows without explicit request
- Change the integration domain name (`smarthashtag`)
- Remove or disable existing tests without justification
- Directly access or modify files outside the repository

### ALWAYS

- Run tests before submitting changes
- Update translations when adding user-facing strings
- Follow Home Assistant's async patterns
- Maintain backward compatibility when possible
- Document breaking changes clearly

## External Dependencies

- **pysmarthashtag**: Core library for Smart vehicle API communication ([GitHub](https://github.com/DasBasti/pySmartHashtag))
- **Home Assistant**: The home automation platform this integrates with

## Useful Links

- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)
- [Home Assistant Custom Component Guide](https://developers.home-assistant.io/docs/creating_component_index)
- [pySmartHashtag Library](https://github.com/DasBasti/pySmartHashtag)
- [HACS Documentation](https://hacs.xyz/)
