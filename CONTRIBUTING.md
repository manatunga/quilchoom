# Contributing to Quilchoom

Thanks for your interest in contributing to Quilchoom!

Quilchoom is an early-stage open-source project, and contributions of all sizes are welcome — including bug fixes, documentation improvements, tests, developer experience improvements, and focused feature work.

## Before you start

For small fixes and straightforward improvements, feel free to open a pull request directly.

For larger features, architectural changes, or changes to Quilchoom's core evidence, knowledge, or documentation model, please open an issue first so the approach can be discussed before significant implementation work begins.

This helps keep contributions aligned with the project's architecture and avoids duplicated or incompatible work.

## Development setup

Quilchoom requires:

- Python 3.14 or later
- Git
- [uv](https://docs.astral.sh/uv/)

Clone the repository:

```bash
git clone https://github.com/manatunga/quilchoom.git
cd quilchoom
```

Install the project and development dependencies:

```bash
uv sync
```

You can then run the CLI inside the development environment:

```bash
uv run quilchoom --version
uv run quilchoom --help
```

## Running the test suite

Run the complete test suite with:

```bash
uv run pytest
```

When working on a focused change, you can run a specific test file while developing:

```bash
uv run pytest tests/path/to/test_file.py
```

Before submitting a pull request, run the complete test suite.

## Code quality

Quilchoom uses Ruff for linting and formatting checks and Pyright for static type checking.

Run the quality checks with:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

All tests and quality checks should pass before a pull request is submitted.

## Pull requests

Keep pull requests focused on one change or closely related set of changes.

When opening a pull request:

- Explain what the change does and why it is needed.
- Include or update tests when behavior changes.
- Update documentation when user-facing behavior changes.
- Keep unrelated refactoring out of the same pull request where possible.
- Make sure the test suite, Ruff checks, and Pyright checks pass.

Smaller, focused pull requests are generally easier to review and merge.

## Project architecture

Quilchoom follows a layered architecture:

```text
CLI → Application → Domain ← Infrastructure
```

The domain and application layers define Quilchoom's core behavior. Infrastructure provides implementations for concerns such as Git, persistence, AI providers, configuration, and filesystem access.

When contributing, preserve dependency direction and avoid introducing infrastructure concerns into the domain layer.

Some of Quilchoom's core design principles include:

- Development activity is captured as evidence before interpretation.
- Project knowledge remains traceable to the evidence behind it.
- Observations and inferences should remain distinguishable.
- Generated documentation remains traceable to project knowledge.
- Corrections should preserve rather than erase historical interpretation.
- Local-first behavior and explicit credential handling should be preserved.

If a proposed change affects these principles, please discuss it in an issue before implementation.

## Reporting bugs

When reporting a bug, include enough information to reproduce the problem where possible:

- Quilchoom version
- Python version
- Operating system
- Command that produced the problem
- Expected behavior
- Actual behavior
- Minimal reproduction steps

Do not include API keys, credentials, secrets, or other sensitive information in issues, logs, screenshots, or pull requests.

## Feature ideas

Feature requests and ideas are welcome.

When proposing a feature, describe the problem or workflow it would improve rather than only the proposed implementation. This makes it easier to evaluate different approaches while keeping the project coherent.

## License

By contributing to Quilchoom, you agree that your contributions will be licensed under the project's [Apache License 2.0](LICENSE).