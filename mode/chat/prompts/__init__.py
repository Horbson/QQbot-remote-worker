# -*- coding: utf-8 -*-
from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent


def read_prompt_file(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def build_system_prompt() -> str:
    return read_prompt_file("IDENTITY.md")
