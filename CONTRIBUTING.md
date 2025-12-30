# Contributing to Simple Usage Monitor

Thank you for your interest in contributing to Simple Usage Monitor! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Contributions](#making-contributions)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Areas for Contribution

We welcome contributions in the following areas:

- **Bug fixes**: Fix issues reported in the issue tracker
- **New features**: Add support for new models, export formats, or UI improvements
- **Documentation**: Improve README, add examples, write tutorials
- **Tests**: Add test coverage for edge cases
- **Performance**: Optimize parsing, caching, or rendering

### Finding Issues

- Check the [issue tracker](https://github.com/SrivathsanSivakumar/simple-usage-monitor/issues) for open issues
- Look for issues labeled `good first issue` or `help wanted`
- Feel free to open new issues for bugs or feature requests

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Claude Code CLI (for testing)

### Setup Instructions

1. **Fork the repository**

   Click the "Fork" button on GitHub to create your own copy.

2. **Clone your fork**

   ```bash
   git clone https://github.com/YOUR_USERNAME/simple-usage-monitor.git
   cd simple-usage-monitor
   ```

3. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install development dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

5. **Verify the setup**

   ```bash
   pytest
   ```

## Making Contributions

### Workflow

1. **Create a branch**

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**

   - Write clean, readable code
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**

   ```bash
   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=src --cov-report=html

   # Run specific test file
   pytest tests/test_pricing.py
   ```

4. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat: add support for new model"
   # or
   git commit -m "fix: correct tiered pricing calculation"
   ```

   Use conventional commit messages:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `test:` for test additions/changes
   - `refactor:` for code refactoring
   - `perf:` for performance improvements

5. **Push to your fork**

   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**

   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill out the PR template with details

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test class
pytest tests/test_pricing.py::TestTieredPricing

# Run with coverage report
pytest --cov=src --cov-report=term-missing
```

### Writing Tests

- Place tests in the `tests/` directory
- Use descriptive test names: `test_calculates_sonnet_above_tier`
- Group related tests in classes: `class TestTieredPricing:`
- Use fixtures for common setup (see `tests/conftest.py`)
- Aim for high coverage of edge cases

Example test structure:

```python
class TestNewFeature:
    """Tests for the new feature"""

    def test_basic_functionality(self):
        """Test that basic case works"""
        # Arrange
        input_data = create_test_data()

        # Act
        result = process_data(input_data)

        # Assert
        assert result == expected_output

    def test_edge_case(self):
        """Test edge case handling"""
        # ...
```

## Code Style

### General Guidelines

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write docstrings for classes and functions
- Keep functions focused and concise
- Use meaningful variable names

### Code Example

```python
def calculate_cost(
    tokens: int,
    price_per_million: float,
    tier_break: Optional[int] = None
) -> float:
    """Calculate the cost for a given number of tokens.

    Args:
        tokens: Number of tokens to calculate cost for
        price_per_million: Price per million tokens
        tier_break: Optional tier break point for tiered pricing

    Returns:
        Total cost in dollars
    """
    # Implementation
    pass
```

### File Organization

- `src/sumonitor/data/` - Data processing and log reading
- `src/sumonitor/session/` - Session tracking and management
- `src/sumonitor/terminal/` - Terminal UI and overlay
- `tests/` - Test files mirroring src structure

## Submitting Changes

### Pull Request Guidelines

1. **PR Title**: Use a clear, descriptive title
   - Good: "Add support for Claude Sonnet 3.5 Opus"
   - Bad: "Update code"

2. **Description**: Explain what and why
   - What changes were made?
   - Why were they necessary?
   - How were they tested?

3. **Link Issues**: Reference related issues
   - "Fixes #123"
   - "Closes #456"

4. **Tests**: Ensure all tests pass
   - Include new tests for new features
   - Update existing tests if behavior changes

5. **Documentation**: Update relevant docs
   - README if user-facing changes
   - Docstrings for code changes
   - CHANGELOG for notable changes

### Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged
4. Your contribution will be credited in the release notes

## Questions?

If you have questions or need help:

- Open an issue for discussion
- Tag maintainers in your PR
- Check existing issues and PRs for similar topics

---

Thank you for contributing to Simple Usage Monitor! Your efforts help make this tool better for everyone in the Claude Code community.
