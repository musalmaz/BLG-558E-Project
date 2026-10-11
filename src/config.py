"""Shared config loader for experiment.yaml."""
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def load_config(path: str | Path = ROOT / "config" / "experiment.yaml") -> dict:
    """Load the experiment YAML config."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(rel: str) -> Path:
    """Resolve a config-relative path against the repo root."""
    return ROOT / rel
