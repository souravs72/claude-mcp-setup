# Contributing to Claude MCP Setup

Thank you for your interest in contributing to Claude MCP Setup! This is a personal project by Sourav Singh, and contributions from the community are welcome and appreciated.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Code Style and Standards](#code-style-and-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Issue Guidelines](#issue-guidelines)
- [Pull Request Guidelines](#pull-request-guidelines)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- Make (build automation tool)
- Docker & Docker Compose (optional, for Frappe/ERPNext)
- Redis Server (optional, for memory-cache server)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/claude-mcp-setup.git
   cd claude-mcp-setup
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/souravs72/claude-mcp-setup.git
   ```

## Development Setup

### 1. Install Dependencies

```bash
make setup
```

This will:

- Create a virtual environment
- Install all required dependencies
- Set up the development environment

### 2. Configure Environment

```bash
cp config/mcp_settings.json.template config/mcp_settings.json
# Edit config/mcp_settings.json with your credentials
```

### 3. Install Pre-commit Hooks

```bash
make install-hooks
```

This installs pre-commit hooks for code quality checks.

### 4. Verify Setup

```bash
make test
```

## Contributing Process

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write clean, readable code
- Follow the coding standards
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run linting
make lint-check

# Run tests
make test

# Test specific server
mcpctl test --server server-name
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add new MCP server for X"
```

Use conventional commit messages:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for test additions/changes
- `chore:` for maintenance tasks

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style and Standards

### Python Code

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions
- Keep functions small and focused

### Tools Used

- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Linting
- **MyPy**: Type checking (optional)

### Running Linting

```bash
# Check linting without fixing
make lint-check

# Fix linting issues
make lint
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Test specific functionality
python scripts/test_server_startup.py --server server-name

# Run with verbose output
mcpctl test --verbose
```

### Test Coverage

We aim for good test coverage. When adding new features:

- Write unit tests for new functions
- Add integration tests for server functionality
- Test error conditions and edge cases

## Documentation

### Documentation Standards

- Keep README.md updated
- Document new features in appropriate files
- Use clear, concise language
- Include code examples where helpful

### Files to Update

When adding new features, consider updating:

- `README.md` - Overview and quick start
- `SETUP.md` - Detailed setup instructions
- Server-specific documentation
- API documentation

## Issue Guidelines

### Before Creating an Issue

1. Check existing issues to avoid duplicates
2. Ensure you're using the latest version
3. Try to reproduce the issue

### Issue Templates

Use the appropriate issue template:

- **Bug Report**: For unexpected behavior
- **Feature Request**: For new functionality
- **Documentation**: For documentation improvements
- **Question**: For general questions

### Good Issue Reports Include

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] PR description explains the changes

### PR Description Template

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

### Review Process

1. Automated checks must pass
2. Code review by maintainers
3. Address feedback and suggestions
4. Merge after approval

## Server Development

### Adding New MCP Servers

1. Create server file in `servers/` directory
2. Follow existing server patterns
3. Add configuration to `mcp_settings.json.template`
4. Update documentation
5. Add tests

### Server Structure

```python
#!/usr/bin/env python3
"""
Server description and purpose.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp import FastMCP
from servers.logging_config import setup_logging, log_server_startup, log_server_shutdown

# Setup logging
logger = setup_logging(__name__)

# Initialize MCP
mcp = FastMCP("server-name")

@mcp.tool()
def tool_name(param: str) -> str:
    """
    Tool description.

    Args:
        param: Parameter description

    Returns:
        Result description
    """
    # Implementation here
    pass

async def main():
    """Main server function."""
    log_server_startup("Server Name")
    try:
        await mcp.run()
    finally:
        log_server_shutdown("Server Name")

if __name__ == "__main__":
    asyncio.run(main())
```

## Getting Help

- Check existing issues and discussions
- Join our community discussions
- Contact maintainers for urgent issues

## Recognition

Contributors will be recognized in:

- Release notes
- Project documentation
- GitHub contributors list

## Project Ownership

This is a personal project by Sourav Singh. While contributions are welcome and appreciated, the project direction and final decisions remain with the project owner.

Thank you for contributing to Claude MCP Setup! 🚀
