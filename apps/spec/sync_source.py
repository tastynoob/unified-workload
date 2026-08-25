#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


def same_file(source: Path, destination: Path) -> bool:
    if not destination.is_file():
        return False
    source_stat = source.stat()
    destination_stat = destination.stat()
    return (
        source_stat.st_size == destination_stat.st_size
        and source_stat.st_mtime_ns == destination_stat.st_mtime_ns
    )


def sync_tree(source: Path, destination: Path) -> None:
    source_files: set[Path] = set()
    destination.mkdir(parents=True, exist_ok=True)

    for root, dirs, files in os.walk(source):
        dirs[:] = [name for name in dirs if not name.startswith("._")]
        source_root = Path(root)
        relative_root = source_root.relative_to(source)
        destination_root = destination / relative_root
        destination_root.mkdir(parents=True, exist_ok=True)

        for name in files:
            if name.startswith("._"):
                continue
            relative = relative_root / name
            source_file = source / relative
            destination_file = destination / relative
            source_files.add(relative)
            if same_file(source_file, destination_file):
                continue
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination_file)

    for path in sorted(destination.rglob("*"), reverse=True):
        relative = path.relative_to(destination)
        if path.is_file() and relative not in source_files:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()

    if not args.source.is_dir():
        parser.error(f"SPEC source directory does not exist: {args.source}")
    sync_tree(args.source.resolve(), args.destination.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
