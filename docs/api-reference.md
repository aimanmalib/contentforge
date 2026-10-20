# API Reference

## Core Modules

### `contentforge.core.config`

Configuration management using Pydantic models.

#### `LLMConfig`

```python
LLMConfig(
    provider: str,          # Preset name; default "openai" (see PROVIDER_PRESETS)
    api_key: str,           # Default: the preset's env var, e.g. OPENAI_API_KEY
    base_url: str,          # Default: the preset's *_BASE_URL env var, else its URL
    model: str,             # Default: the preset's model, e.g. gpt-4o-mini
    auth_style: str,        # "bearer" | "api-key"; default from the preset
    max_tokens: int,        # Default: 4096
    temperature: float,     # Default: 0.7
    top_p: float,           # Default: 0.9
    timeout: int,           # Default: 120s
    max_retries: int,       # Default: 3
)
```

Unknown provider names fall back to the `openai` preset (Bearer auth), so a custom
endpoint only needs `base_url`. `MiMoConfig` is a backward-compatible subclass whose
provider defaults to `mimo` (which uses the `api-key` header).

#### `ContentForgeConfig`

- `ContentForgeConfig.from_env()`: provider from `CONTENTFORGE_PROVIDER` (default
  `openai`), optional model override from `CONTENTFORGE_MODEL`, key/base URL from the
  preset's env vars.
- `ContentForgeConfig.from_yaml(path)`: loads YAML; `${VAR}` references are expanded
  from the environment (unset → empty, which then falls back to the preset's env var).
- `config.to_template()`: dict safe to write to disk (API key replaced by `${VAR}`).
- `config.mimo`: deprecated alias of `config.llm`.

### `contentforge.core.llm_client`

#### `LLMClient`

Async context manager for any OpenAI-compatible `/chat/completions` endpoint.
`MiMoClient` (in `contentforge.core.mimo_client`) is a backward-compatible alias.

```python
async with LLMClient(config.llm) as client:
    response = await client.chat(messages)
    async for chunk in client.stream_chunks(messages):
        print(chunk.delta)
```

#### `ChatMessage`

```python
ChatMessage(role: str, content: str, reasoning_content: Optional[str] = None)
```

#### `ChatResponse`

```python
ChatResponse(
    content: str,
    reasoning_content: Optional[str],
    usage: TokenUsage,
    model: str,
    finish_reason: str,
    latency_ms: float,
)
```

#### `TokenUsage`

```python
TokenUsage(
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cached_tokens: int,
)
```

### `contentforge.core.token_tracker`

#### `TokenTracker`

```python
tracker = TokenTracker(output_dir="./output")
tracker.start_pipeline()
tracker.record("agent_name", prompt_tokens=100, completion_tokens=50, latency_ms=200)
tracker.end_pipeline()
print(tracker.report())
tracker.save()
```

## Agents

### `BaseAgent`

Abstract base class. All agents implement:

```python
async def execute(**kwargs) -> AgentResult
async def run(**kwargs) -> AgentResult  # wraps execute with error handling
```

### `AgentResult`

```python
AgentResult(
    agent_name: str,
    status: str,          # "success" | "partial" | "failed"
    content: str,
    metadata: dict,
    tokens_used: int,
    latency_ms: float,
    error: Optional[str],
    reasoning: Optional[str],
)
```

### Agent-Specific Parameters

| Agent | `execute()` params |
|-------|-------------------|
| Research | `topic: str` |
| Outline | `research_data: str, target_words: int` |
| Writer | `outline: str, research_data: str, language: str` |
| SEO | `content: str, target_keywords: list[str]` |
| Editor | `content: str, seo_recommendations: str, target_reading_level: str` |
| Translator | `content: str, target_language: str, source_language: str, preserve_keywords: list[str]` |
| Quality | `content: str, threshold: float, title: str` |
| Publisher | `content: str, title: str, publish_targets: list[str], output_dir: str` |

## Pipeline

### `PipelineOrchestrator`

```python
orchestrator = PipelineOrchestrator(config)
result = await orchestrator.run(topic="Your Topic")
```

### `PipelineResult`

```python
PipelineResult(
    status: str,
    article: str,
    research: str,
    outline: str,
    seo_analysis: str,
    quality_report: str,
    publisher_output: str,
    translations: dict[str, str],
    agent_results: dict[str, AgentResult],
    metrics_path: str,
    total_tokens: int,
    pipeline_duration_s: float,
)
```

## Utilities

### `contentforge.utils.text.extract_json(text)`

Parses JSON from an LLM reply, tolerating Markdown code fences and surrounding prose.
Returns `None` when nothing parses. Used by the Quality agent to read its score.
