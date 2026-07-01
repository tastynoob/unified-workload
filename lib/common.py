from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, List, Mapping, Optional


class BuildError(RuntimeError):
    pass


def log(message: str) -> None:
    print(f"[unified-workload] {message}", flush=True)


def run(
    cmd: List[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    dry_run: bool = False,
) -> None:
    shown_cwd = f" (cwd={cwd})" if cwd else ""
    log("$ " + " ".join(cmd) + shown_cwd)
    if dry_run:
        return
    subprocess.run(cmd, cwd=cwd, env=dict(env) if env else None, check=True)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_text(path: Path, content: str, dry_run: bool) -> None:
    log(f"write {path}")
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_symbol(path: Path, symbol: str) -> Any:
    if not path.exists():
        raise BuildError(f"Module does not exist: {path}")

    spec = importlib.util.spec_from_file_location(f"uw_{path.parent.name}_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise BuildError(f"Cannot load module: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    value = getattr(module, symbol, None)
    if value is None:
        raise BuildError(f"Module {path} has no symbol {symbol}")
    return value
