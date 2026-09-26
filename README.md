# trade-agent-plus

Multi-agent LLM financial trading framework

## Setup

    uv venv --python 3.12
    source .venv/bin/activate
    uv pip install -e ".[dev]"

Copy `.env.example` to `.env` and add your API key.

## Test

    pytest
    ruff check .