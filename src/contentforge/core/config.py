"""Configuration management for ContentForge pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class MiMoConfig(BaseModel):
    """MiMo API connection settings."""
    api_key: str = Field(default_factory=lambda: os.environ.get("MIMO_API_KEY", ""))
    base_url: str = Field(
        default_factory=lambda: os.environ.get(
            "MIMO_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1"
        )
    )
    model: str = "mimo-v2.5-pro"
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0

    @property
    def headers(self) -> dict[str, str]:
        return {
            "api-key": self.api_key,  # MiMo uses api-key, NOT Authorization: Bearer
            "Content-Type": "application/json",
        }


class PipelineConfig(BaseModel):
    """Pipeline execution settings."""
    topic: str = ""
    target_word_count: int = 2000
    language: str = "en"
    output_format: str = "markdown"
    seo_enabled: bool = True
    quality_threshold: float = 0.8
    max_iterations: int = 3
    enable_translation: bool = False
    target_languages: list[str] = Field(default_factory=lambda: ["zh", "ms"])
    publish_targets: list[str] = Field(default_factory=lambda: ["markdown"])


class AgentConfig(BaseModel):
    """Per-agent configuration overrides."""
    name: str
    enabled: bool = True
    model_override: Optional[str] = None
    temperature_override: Optional[float] = None
    max_tokens_override: Optional[int] = None
    system_prompt_override: Optional[str] = None


class ContentForgeConfig(BaseModel):
    """Root configuration."""
    mimo: MiMoConfig = Field(default_factory=MiMoConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    agents: list[AgentConfig] = Field(default_factory=list)
    log_level: str = "INFO"
    output_dir: str = "./output"
    cache_dir: str = "./.cache"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ContentForgeConfig":
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    @classmethod
    def from_env(cls) -> "ContentForgeConfig":
        return cls(mimo=MiMoConfig())

    def get_agent_config(self, name: str) -> AgentConfig:
        for agent in self.agents:
            if agent.name == name:
                return agent
        return AgentConfig(name=name)
