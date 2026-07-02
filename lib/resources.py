from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path
from typing import Any

from lib.common import BuildError, log, run
from lib.context import BuildContext


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def resource_exists(path: Path) -> bool:
    return path.is_dir() or path.is_symlink()


def resource_table(ctx: BuildContext) -> dict[str, Any]:
    resources = dict(ctx.resource_config["resources"])
    resources.update(dict(ctx.platform_config.get("resources", {})))
    return resources


def resource_names(ctx: BuildContext) -> list[str]:
    return sorted(resource_table(ctx))


def resource_meta(ctx: BuildContext, name: str) -> dict[str, Any]:
    resources = resource_table(ctx)
    if name not in resources:
        names = ", ".join(sorted(resources))
        raise BuildError(f"Unknown resource '{name}'. Available resources: {names}")
    return dict(resources[name])


def resource_path(ctx: BuildContext, name: str) -> Path:
    meta = resource_meta(ctx, name)
    return ctx.args.external_dir / ctx.arch / meta.get("dest", name)


def ensure_resource(ctx: BuildContext, name: str) -> Path:
    path = resource_path(ctx, name)
    if resource_exists(path):
        return path
    if path.exists():
        raise BuildError(f"Resource '{name}' path exists but is not a directory or symlink: {path}")
    raise BuildError(
        f"Resource '{name}' is missing at {path}. "
        "Run 'python3 workload.py fetch' to download resources, "
        f"or create this path as a symlink to an existing local source tree: {path}"
    )


def download(url: str, dest: Path, dry_run: bool) -> None:
    log(f"download {url} -> {dest}")
    if dry_run:
        return
    tmp_dest = dest.with_name(f".{dest.name}.tmp")
    remove_path(tmp_dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, tmp_dest)
    tmp_dest.rename(dest)


def fetch_resource(ctx: BuildContext, name: str) -> None:
    meta = resource_meta(ctx, name)
    dest = resource_path(ctx, name)
    if resource_exists(dest):
        log(f"resource '{name}' already exists: {dest}")
        return
    if dest.exists():
        raise BuildError(f"Resource '{name}' path exists but is not a directory or symlink: {dest}")

    kind = meta.get("type")
    if kind == "git":
        tmp_dest = dest.with_name(f".{dest.name}.tmp")
        cmd = ["git", "clone", "--depth", "1"]
        if meta.get("branch"):
            cmd.extend(["--branch", str(meta["branch"])])
        cmd.extend([meta["url"], str(tmp_dest)])
        if not ctx.args.dry_run:
            remove_path(tmp_dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
        run(cmd, dry_run=ctx.args.dry_run)
        if meta.get("submodules"):
            run(
                ["git", "-C", str(tmp_dest), "submodule", "update", "--init", "--recursive"],
                dry_run=ctx.args.dry_run,
            )
        if not ctx.args.dry_run:
            tmp_dest.rename(dest)
        return

    if kind == "archive":
        url = meta["url"]
        archive_name = meta.get("archive_name") or Path(url).name
        archive_path = ctx.args.cache_dir / archive_name
        tmp_dest = dest.with_name(f".{dest.name}.tmp")
        if not archive_path.exists():
            download(url, archive_path, ctx.args.dry_run)
        if not ctx.args.dry_run:
            remove_path(tmp_dest)
            tmp_dest.mkdir(parents=True, exist_ok=True)
        run(
            [
                "tar",
                "-xf",
                str(archive_path),
                "--strip-components",
                str(meta.get("strip_components", 0)),
                "-C",
                str(tmp_dest),
            ],
            dry_run=ctx.args.dry_run,
        )
        if not ctx.args.dry_run:
            tmp_dest.rename(dest)
        return

    raise BuildError(f"Unsupported resource type for '{name}': {kind}")
