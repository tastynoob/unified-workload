#!/usr/bin/env python3
"""Generate the fixed argv used by a SPEC Linux initramfs workload."""

from __future__ import annotations

import argparse
import json
import os
import shlex
from pathlib import Path


def c_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def generate(executable: str, arguments: list[str]) -> str:
    argv = [executable, *arguments]
    lines = [
        "#include <stddef.h>",
        "",
    ]
    for index, argument in enumerate(argv):
        lines.append(f"static char spec_arg_{index}[] = {c_string(argument)};")
    lines.extend(["", "char *spec_argv[] = {"])
    lines.extend(f"    spec_arg_{index}," for index in range(len(argv)))
    lines.extend([
        "    (char *)0,",
        "};",
        f"const int spec_argc = {len(argv)};",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    arguments = shlex.split(os.environ.get("SPEC_ARGS", ""))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate(args.executable, arguments), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
