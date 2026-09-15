from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from lib.common import BuildError, write_text
from lib.context import BuildContext


RESERVED_PATHS = {
    PurePosixPath("/init"),
    PurePosixPath("/dev"),
    PurePosixPath("/dev/console"),
    PurePosixPath("/dev/null"),
}
ELF_MACHINES = {
    "aarch64": 183,
    "riscv": 243,
}


@dataclass(frozen=True)
class FileMapping:
    source: Path
    destination: PurePosixPath


@dataclass(frozen=True)
class AnyConfig:
    elf: Path
    mappings: list[FileMapping]


def _host_path(value: str, option: str) -> Path:
    path = Path(value).expanduser()
    path = Path(os.path.abspath(path))
    if not path.exists() and not path.is_symlink():
        raise BuildError(f"{option} path does not exist: {path}")
    if any(character.isspace() for character in str(path)):
        raise BuildError(f"{option} path must not contain whitespace: {path}")
    return path


def _guest_path(value: str, option: str, *, allow_root: bool = False) -> PurePosixPath:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts:
        raise BuildError(f"{option} must be an absolute guest path without '..': {value}")
    if path == PurePosixPath("/") and not allow_root:
        raise BuildError(f"{option} must not be the guest root directory")
    if any(character.isspace() for character in str(path)):
        raise BuildError(f"{option} must not contain whitespace: {value}")
    return path


def _validate_elf(path: Path, arch: str) -> None:
    if not path.is_file():
        raise BuildError(f"workload option elf is not a regular file: {path}")
    with path.open("rb") as elf_file:
        header = elf_file.read(20)
    if len(header) < 20 or header[:4] != b"\x7fELF":
        raise BuildError(f"workload option elf is not an ELF file: {path}")
    if header[4] != 2:
        raise BuildError(f"workload option elf must be ELF64: {path}")
    if header[5] not in (1, 2):
        raise BuildError(f"workload option elf has an unsupported byte order: {path}")
    byte_order = "<" if header[5] == 1 else ">"
    elf_type = struct.unpack(f"{byte_order}H", header[16:18])[0]
    if elf_type not in (2, 3):
        raise BuildError(f"workload option elf is not an executable ELF: {path}")
    machine = struct.unpack(f"{byte_order}H", header[18:20])[0]
    expected = ELF_MACHINES.get(arch)
    if expected is not None and machine != expected:
        raise BuildError(
            f"workload option elf machine {machine} does not match architecture {arch}"
        )


def _parse_mapping(value: str) -> FileMapping:
    if "=" not in value:
        raise BuildError("workload option file must use HOST=GUEST syntax")
    host, guest = value.split("=", 1)
    if not host or not guest:
        raise BuildError("workload option file must use non-empty HOST=GUEST paths")
    return FileMapping(
        _host_path(host, "workload option file"),
        _guest_path(guest, "workload option file", allow_root=True),
    )


def load_config(ctx: BuildContext) -> AnyConfig:
    elf_values = ctx.workload_option_values("elf")
    if len(elf_values) != 1:
        raise BuildError("the any workload requires exactly one --workload-option elf=PATH")
    elf = _host_path(elf_values[0], "workload option elf")
    _validate_elf(elf, ctx.arch)

    return AnyConfig(
        elf=elf,
        mappings=[
            _parse_mapping(value)
            for value in ctx.workload_option_values("file")
        ],
    )


def _mode(path: Path, default: int) -> int:
    mode = path.stat(follow_symlinks=False).st_mode & 0o777
    return mode or default


class ManifestBuilder:
    def __init__(self) -> None:
        self.entries: dict[PurePosixPath, str] = {}

    def _check_path(self, path: PurePosixPath, kind: str) -> None:
        if not path.is_absolute() or ".." in path.parts:
            raise BuildError(f"invalid guest path in workload option file mapping: {path}")
        if any(character.isspace() for character in str(path)):
            raise BuildError(f"guest path must not contain whitespace: {path}")
        if path in RESERVED_PATHS:
            raise BuildError(f"workload option file conflicts with reserved path: {path}")
        existing = self.entries.get(path)
        if existing is not None and not (kind == "dir" and existing.startswith("dir ")):
            raise BuildError(f"duplicate workload option file guest path: {path}")

    def add_parents(self, path: PurePosixPath) -> None:
        for parent in reversed(path.parents):
            if parent == PurePosixPath("/"):
                continue
            if parent in RESERVED_PATHS:
                raise BuildError(f"workload option file conflicts with reserved path: {parent}")
            existing = self.entries.get(parent)
            if existing is not None and not existing.startswith("dir "):
                raise BuildError(f"workload option file parent is not a directory: {parent}")
            self.entries.setdefault(parent, f"dir {parent} 755 0 0")

    def add_dir(self, path: PurePosixPath, mode: int = 0o755) -> None:
        if path == PurePosixPath("/"):
            return
        self._check_path(path, "dir")
        self.add_parents(path)
        self.entries[path] = f"dir {path} {mode:o} 0 0"

    def add_file(self, source: Path, destination: PurePosixPath) -> None:
        if any(character.isspace() for character in str(source)):
            raise BuildError(f"host path must not contain whitespace: {source}")
        self._check_path(destination, "file")
        self.add_parents(destination)
        self.entries[destination] = (
            f"file {destination} {source} {_mode(source, 0o644):o} 0 0"
        )

    def add_symlink(self, source: Path, destination: PurePosixPath) -> None:
        if any(character.isspace() for character in str(source)):
            raise BuildError(f"host path must not contain whitespace: {source}")
        target = os.readlink(source)
        if PurePosixPath(target).is_absolute():
            raise BuildError(f"absolute host symlink cannot be mapped: {source} -> {target}")
        if any(character.isspace() for character in target):
            raise BuildError(f"symlink target must not contain whitespace: {source}")
        self._check_path(destination, "slink")
        self.add_parents(destination)
        self.entries[destination] = f"slink {destination} {target} 777 0 0"

    def add_mapping(self, mapping: FileMapping) -> None:
        source = mapping.source
        destination = mapping.destination
        if destination == PurePosixPath("/") and not source.is_dir():
            raise BuildError("only a directory can be mapped to the guest root")
        if source.is_symlink():
            self.add_symlink(source, destination)
            return
        if source.is_file():
            self.add_file(source, destination)
            return
        if not source.is_dir():
            raise BuildError(f"workload option file supports only files and directories: {source}")

        self.add_dir(destination, _mode(source, 0o755))
        for root, directories, files in os.walk(source, followlinks=False):
            root_path = Path(root)
            relative_root = root_path.relative_to(source)
            guest_root = destination / PurePosixPath(relative_root.as_posix())

            for name in list(directories):
                path = root_path / name
                guest = guest_root / name
                if path.is_symlink():
                    self.add_symlink(path, guest)
                    directories.remove(name)
                else:
                    self.add_dir(guest, _mode(path, 0o755))
            for name in files:
                path = root_path / name
                guest = guest_root / name
                if path.is_symlink():
                    self.add_symlink(path, guest)
                elif path.is_file():
                    self.add_file(path, guest)
                else:
                    raise BuildError(f"unsupported workload option file entry: {path}")

    def render(self) -> str:
        return "\n".join(
            self.entries[path]
            for path in sorted(self.entries, key=lambda item: (len(item.parts), str(item)))
        )


def build(ctx: BuildContext) -> Path:
    config = load_config(ctx)
    manifest = ManifestBuilder()
    for mapping in config.mappings:
        manifest.add_mapping(mapping)
    extra = manifest.render()

    initramfs = ctx.initramfs_list()
    manifest_text = f"""dir /dev 755 0 0

nod /dev/console 644 0 0 c 5 1
nod /dev/null 644 0 0 c 1 3

file /init {config.elf} 755 0 0
"""
    if extra:
        manifest_text += "\n" + extra + "\n"
    write_text(initramfs, manifest_text, ctx.args.dry_run)
    return initramfs
