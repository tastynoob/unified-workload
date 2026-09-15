from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Mapping

from lib.common import BuildError, load_json, load_symbol


OPTION_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)=(.+)$")


def load_platform(root: Path, name: str) -> tuple[dict[str, Any], Any, Path]:
    platform_dir = root / "plat" / name
    config_path = platform_dir / "platform.json"
    workflow_path = platform_dir / "workflow.py"
    if not config_path.exists():
        raise BuildError(f"Platform config does not exist: {config_path}")
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise BuildError(f"Invalid platform config: {config_path}")
    build_firmware = load_symbol(workflow_path, "build_firmware")
    module = sys.modules[build_firmware.__module__]
    return config, module, config_path


def parse_options(values: list[str], option_name: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for value in values:
        match = OPTION_RE.match(value)
        if match is None:
            raise BuildError(
                f"{option_name} must use KEY=VALUE syntax"
            )
        key, option_value = match.groups()
        result.setdefault(key.replace("-", "_"), []).append(option_value)
    return result


def validate_option_keys(
    options: Mapping[str, list[str]],
    allowed: set[str],
    repeatable: set[str] | None = None,
    option_name: str = "platform",
) -> None:
    repeatable = repeatable or set()
    unknown = sorted(set(options) - allowed)
    if unknown:
        raise BuildError(
            f"unsupported {option_name} option(s): " + ", ".join(unknown)
        )
    duplicate = sorted(
        key for key, values in options.items()
        if len(values) > 1 and key not in repeatable
    )
    if duplicate:
        raise BuildError(
            f"{option_name} option may be specified only once: "
            + ", ".join(duplicate)
        )
