"""Shared utilities for AppAgent command-line entry points."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ScriptCommand:
    """Represent a command that executes an internal Python script."""

    script_path: str
    args: tuple[str, ...] = ()

    def to_argv(self) -> list[str]:
        return [sys.executable, self.script_path, *self.args]


class CommandRunner:
    """Run script commands and raise exceptions on failures."""

    @staticmethod
    def run(command: ScriptCommand) -> None:
        subprocess.run(command.to_argv(), check=True)

    @classmethod
    def run_many(cls, commands: Iterable[ScriptCommand]) -> None:
        for command in commands:
            cls.run(command)


def normalize_app_name(raw_name: str) -> str:
    """Normalize user-provided app names to match prior behavior."""

    return raw_name.replace(" ", "")


def build_common_args(*, app: str, root_dir: str) -> tuple[str, ...]:
    """Construct shared CLI args expected by downstream scripts."""

    return ("--app", app, "--root_dir", root_dir)
