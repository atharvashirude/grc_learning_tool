# GRC Learning Platform

An interactive Governance, Risk, and Compliance (GRC) learning platform featuring hands-on simulations using open-source, real-world GRC applications and stateful AI orchestration (LangGraph).

## Core Architecture

- **Domain Core**: ISO/IEC 27001:2022 clause and control specifications, audit rubrics, and finding evaluators.
- **AI Orchestration**: Stateful multi-turn ISO 27001 Lead Auditor and GRC Tutor agents built with LangGraph.
- **Simulation Target**: Programmatic orchestration and verification against real-world open-source GRC systems (e.g., Eramba, Wazuh).
- **Architecture Pattern**: Hexagonal (Ports & Adapters) enforcing zero external framework coupling on domain models.

## Development Setup

### Prerequisites
- Python 3.11+
- Poetry

### Installation
```bash
poetry config virtualenvs.in-project true
poetry install
```

### Quality Gates & Testing
```bash
# Linting & Formatting
poetry run ruff check .
poetry run ruff format --check .

# Static Type Checking (Strict)
poetry run mypy src tests

# Security AST Scan
poetry run bandit -c pyproject.toml -r src

# Test Suite with Coverage Gate
poetry run pytest
```
