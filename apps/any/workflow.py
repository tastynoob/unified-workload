from __future__ import annotations

from lib.any_app import build, load_config
from lib.platform import validate_option_keys
from lib.context import BuildContext


def validate_options(ctx: BuildContext) -> None:
    validate_option_keys(
        ctx.workload_options,
        {"elf", "file"},
        option_name="workload",
    )


def doctor(ctx: BuildContext) -> None:
    load_config(ctx)


def build_workload(ctx: BuildContext):
    return build(ctx)
