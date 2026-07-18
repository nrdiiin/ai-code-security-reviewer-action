# Contributing to AI Code Security Reviewer Action

Thank you for your interest in contributing!

## Development Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/nrdiiin/ai-code-security-reviewer-action.git
   cd ai-code-security-reviewer-action
   ```

2. Install test dependencies:
   ```bash
   pip install pytest ruff
   ```

3. Run tests:
   ```bash
   pytest tests/ -v
   ```

4. Run linting:
   ```bash
   ruff check .
   ```

## Project Structure

- `action.yml` — The composite GitHub Action definition
- `scripts/format_pr_comment.py` — Formats scan JSON into PR comment markdown
- `scripts/post_pr_comment.py` — Posts/updates PR comments via GitHub API
- `examples/` — Example workflow files for users
- `tests/` — Python tests for the scripts

## Guidelines

- This action is an **orchestration layer only**. Do not add scanning logic here — that lives in the [CLI](https://github.com/nrdiiin/ai-code-security-reviewer-cli) and [Core SDK](https://github.com/nrdiiin/ai-code-security-reviewer).
- Keep scripts minimal and dependency-free (stdlib only where possible).
- All Python code must pass `ruff check` and `pytest`.

## Submitting Changes

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Open a PR against `main`
