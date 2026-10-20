# ContentForge

> **8-agent AI content pipeline for any OpenAI-compatible LLM**
>
> From topic to edited article: research, outline, write, SEO review, edit, quality-score, translate and package for publishing, with eight specialised agents orchestrated through one pipeline.

[![CI](https://github.com/aimanmalib/contentforge/actions/workflows/ci.yml/badge.svg)](https://github.com/aimanmalib/contentforge/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Works with **OpenAI, OpenRouter, Ollama, Groq, DeepSeek, Together, Mistral, Xiaomi MiMo**, or any endpoint that speaks the OpenAI `/chat/completions` protocol (vLLM, llama.cpp, LM Studio, a local proxy). Pick a provider with one environment variable or one config line; no code changes.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     ContentForge Pipeline                        │
│               Any OpenAI-compatible LLM backend                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐       │
│  │1.Research│──▶│2.Outline │──▶│ 3.Writer │──▶│  4.SEO   │       │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘       │
│                                                    │ (optional)  │
│                                                    ▼             │
│  ┌──────────┐   ┌──────────┐      ┌───────────────────────────┐  │
│  │8.Publish │◀──│7.Translate│◀────│ 5.Editor ──▶ 6.Quality     │  │
│  └──────────┘   └──────────┘      │ (repeat while < threshold) │  │
│       │          (optional)       └───────────────────────────┘  │
│       ▼                                                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Token tracker: per-agent tokens, cached tokens, latency    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## The 8 agents

| # | Agent | Role |
|---|-------|------|
| 1 | **Research** | Background, key facts and angles on the topic |
| 2 | **Outline** | Section structure with word allocation |
| 3 | **Writer** | Full article draft from outline + research |
| 4 | **SEO** | Keyword, heading and meta-tag recommendations (skip with `--no-seo`) |
| 5 | **Editor** | Clarity, grammar and tone; applies SEO suggestions |
| 6 | **Quality** | Scores 8 dimensions and flags issues; the Editor → Quality loop repeats until the score meets `--threshold` or `--max-iter` is reached |
| 7 | **Translator** | Adapts the article to other languages (prompt tuned for zh/ms/ja/ko/id/th/vi/ar) |
| 8 | **Publisher** | Produces platform variants (Markdown, HTML, social snippets, newsletter subject, metadata) as JSON |

> **Note:** the Research agent has no web access. "Facts" come from the model's own knowledge, so verify statistics and quotes before publishing.

## Supported providers

Built-in presets (from [`core/config.py`](src/contentforge/core/config.py)):

| Provider | `provider=` | Default model | Auth | Env vars |
|----------|-------------|---------------|------|----------|
| OpenAI (default) | `openai` | `gpt-4o-mini` | Bearer | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| OpenRouter | `openrouter` | `openai/gpt-4o-mini` | Bearer | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` |
| Ollama (local) | `ollama` | `llama3.1` | Bearer | `OLLAMA_API_KEY`, `OLLAMA_BASE_URL` |
| Groq | `groq` | `llama-3.3-70b-versatile` | Bearer | `GROQ_API_KEY`, `GROQ_BASE_URL` |
| DeepSeek | `deepseek` | `deepseek-chat` | Bearer | `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` |
| Together | `together` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | Bearer | `TOGETHER_API_KEY`, `TOGETHER_BASE_URL` |
| Mistral | `mistral` | `mistral-small-latest` | Bearer | `MISTRAL_API_KEY`, `MISTRAL_BASE_URL` |
| Xiaomi MiMo | `mimo` | `mimo-v2.5-pro` | `api-key` header | `MIMO_API_KEY`, `MIMO_BASE_URL` |

Any other OpenAI-compatible server: keep `provider: openai` and set `OPENAI_BASE_URL` (or `base_url` in the config file) to its `/v1` URL.

## Quick start

```bash
git clone https://github.com/aimanmalib/contentforge.git
cd contentforge
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Default provider is OpenAI
export OPENAI_API_KEY="sk-..."

# Or choose another provider / model via env vars
# export CONTENTFORGE_PROVIDER=openrouter
# export OPENROUTER_API_KEY="sk-or-..."
# export CONTENTFORGE_MODEL="openai/gpt-4o-mini"   # optional model override

contentforge --help

# Generate an article (writes into ./output)
contentforge generate "AI in Healthcare" --words 800 --output ./output

# Cheaper run: skip SEO, one edit pass
contentforge generate "AI in Healthcare" --words 300 --no-seo --max-iter 1

# With translation
contentforge generate "AI Ethics" --translate zh --translate ms

# Per-agent token report for a finished run
contentforge report output/metrics/<run_id>.json

# List agents
contentforge agents
```

A run writes three files into the output directory:

- `<timestamp>_article.md`: the final edited article
- `<timestamp>_publisher.json`: the Publisher agent's platform variants and metadata
- `metrics/<run_id>.json`: per-agent calls, prompt/completion/cached tokens and latency

## Configuration file

Generate a starter file with `contentforge init` (it references your key as `${VAR}` and never writes the key itself), then run with `contentforge -c contentforge.yaml generate ...`.

```yaml
# contentforge.yaml
llm:
  provider: openai          # any preset name from the table above
  api_key: ${OPENAI_API_KEY} # ${VAR} references are expanded from the environment
  # base_url and model default from the preset; override if needed
  # base_url: http://localhost:8000/v1
  # model: gpt-4o-mini
  max_tokens: 4096
  temperature: 0.7
  max_retries: 3

pipeline:
  target_word_count: 2000
  language: en
  seo_enabled: true
  quality_threshold: 0.8    # 0-1, compared against the Quality agent's 0-100 score
  max_iterations: 3
  enable_translation: false
  target_languages: [zh, ms]
  publish_targets: [markdown, html]

agents:
  - name: writer
    temperature_override: 0.8
    max_tokens_override: 8192
  - name: quality
    system_prompt_override: "Custom quality rules..."
```

## Token usage

Usage depends on the model, the target length and how many Editor → Quality iterations run, so there is no single number to quote. Every run records its own per-agent figures in `metrics/<run_id>.json`; `contentforge report` prints them as a table. For a rough budget: a run makes one call per agent (plus one per translation language and per extra edit iteration), and each call includes the previous stage's output in its prompt.

## Usage as a library

```python
import asyncio
from contentforge.core.config import ContentForgeConfig
from contentforge.pipeline.orchestrator import PipelineOrchestrator

async def main():
    config = ContentForgeConfig.from_env()
    config.pipeline.target_word_count = 1000
    config.pipeline.enable_translation = True
    config.pipeline.target_languages = ["ms"]

    orchestrator = PipelineOrchestrator(config)
    result = await orchestrator.run("The Future of AI Agents")

    print(f"Article: {len(result.article.split())} words")
    print(f"Tokens: {result.total_tokens:,}")
    print(f"Duration: {result.pipeline_duration_s:.1f}s")
    print(f"Translations: {list(result.translations)}")
    print(orchestrator.tracker.report())

asyncio.run(main())
```

### LLMClient

```python
from contentforge.core.config import LLMConfig
from contentforge.core.llm_client import ChatMessage, LLMClient

messages = [
    ChatMessage(role="system", content="You are helpful."),
    ChatMessage(role="user", content="Explain AI agents."),
]

async with LLMClient(LLMConfig(provider="openai")) as client:
    response = await client.chat(messages)
    print(response.content, response.usage.total_tokens)

    async for chunk in client.stream_chunks(messages):
        print(chunk.delta, end="", flush=True)
```

The auth header (`Authorization: Bearer` or `api-key`) is chosen from the provider preset. Models that return a `reasoning_content` field have it captured on the response. `MiMoClient` / `MiMoConfig` remain importable as backward-compatible aliases.

See [`docs/api-reference.md`](docs/api-reference.md) for the full API and [`examples/`](examples/) for runnable scripts.

## Development

```bash
pip install -e ".[dev]"
ruff check src/ tests/
ruff format --check src/ tests/
pytest                     # unit + integration tests, no network calls
pytest -m unit             # unit tests only
```

CI runs lint, format check and tests on Python 3.10–3.13. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Project structure

```
src/contentforge/
├── cli.py                 # Click CLI with Rich output
├── agents/                # base.py + the 8 agents (research, outline, writer, seo,
│                          #   editor, quality, translator, publisher)
├── core/
│   ├── config.py          # Pydantic config + provider presets
│   ├── llm_client.py      # OpenAI-compatible async client (retries, optional SSE streaming)
│   ├── mimo_client.py     # Backward-compat shim → llm_client
│   └── token_tracker.py   # Per-agent token metrics
├── pipeline/
│   └── orchestrator.py    # 8-agent pipeline coordinator
└── utils/                 # text helpers (word count, JSON extraction, ...) + exporters
```

## License

MIT, see [LICENSE](LICENSE).

---

Built by [Sasa Teguh](https://sasateguh.com) · Malaysia
