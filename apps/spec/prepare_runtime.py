#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import json
import os
import shlex
import tempfile
from pathlib import Path


ALIGNMENT = 16


def write_text_if_changed(path: Path, content: str) -> None:
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def input_files(
    input_dirs: list[Path], embed_inputs: bool
) -> list[tuple[str, Path]]:
    if not embed_inputs:
        return []
    if not input_dirs:
        raise ValueError("no SPEC input directories were found")

    files: dict[str, Path] = {}
    for input_dir in input_dirs:
        if not input_dir.is_dir():
            raise ValueError(f"SPEC input directory does not exist: {input_dir}")
        for path in input_dir.rglob("*"):
            if not path.is_file() or any(part.startswith("._") for part in path.parts):
                continue
            files[path.relative_to(input_dir).as_posix()] = path
    return sorted(files.items())


def pack_inputs(
    files: list[tuple[str, Path]], output: Path
) -> list[tuple[str, int, int]]:
    output.parent.mkdir(parents=True, exist_ok=True)
    index: list[tuple[str, int, int]] = []

    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        offset = 0
        for relative, path in files:
            padding = (-offset) % ALIGNMENT
            if padding:
                temporary.write(b"\0" * padding)
                offset += padding
            size = path.stat().st_size
            index.append((relative, offset, size))
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    temporary.write(chunk)
                    offset += len(chunk)
        if offset == 0:
            temporary.write(b"\0")

    if output.is_file() and filecmp.cmp(temporary_path, output, shallow=False):
        temporary_path.unlink()
    else:
        temporary_path.replace(output)
    return index


def c_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def runtime_config(executable: str, arguments: list[str], stdin_path: str,
                   files: list[tuple[str, int, int]]) -> str:
    argv = [executable, *arguments]
    lines = [
        "#include <stddef.h>",
        "",
        "struct spec_embedded_file {",
        "    const char *path;",
        "    size_t offset;",
        "    size_t size;",
        "};",
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
        f"const char *spec_stdin_path = {c_string(stdin_path) if stdin_path else '(const char *)0'};",
        "",
        "const struct spec_embedded_file spec_embedded_files[] = {",
    ])
    if files:
        for path, offset, size in files:
            lines.append(f"    {{ {c_string(path)}, {offset}U, {size}U }},")
    else:
        lines.append("    { (const char *)0, 0U, 0U },")
    lines.extend([
        "};",
        f"const size_t spec_embedded_file_count = {len(files)}U;",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    parser.add_argument("--input-dir", type=Path, action="append", default=[])
    parser.add_argument("--embed-inputs", type=int, choices=(0, 1), required=True)
    parser.add_argument("--binary-output", type=Path, required=True)
    parser.add_argument("--c-output", type=Path, required=True)
    args = parser.parse_args()

    arguments = shlex.split(os.environ.get("SPEC_ARGS", ""))
    stdin_path = os.environ.get("SPEC_STDIN", "").removeprefix("./")
    source_dirs = [path.resolve() for path in args.input_dir]
    files = input_files(source_dirs, bool(args.embed_inputs))
    index = pack_inputs(files, args.binary_output.resolve())

    if stdin_path and stdin_path not in {entry[0] for entry in index}:
        parser.error(f"SPEC_STDIN is not embedded: {stdin_path}")

    config = runtime_config(args.executable, arguments, stdin_path, index)
    write_text_if_changed(args.c_output.resolve(), config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
