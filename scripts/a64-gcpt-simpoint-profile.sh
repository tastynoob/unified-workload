#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=scripts/a64-gcpt-simpoint-config.sh
source "$script_dir/a64-gcpt-simpoint-config.sh"

usage()
{
    printf 'Usage: %s <gcpt-path> <profile-dir>\n' "$(basename "$0")"
    printf '\nThe profile is written to <profile-dir>/simpoint_bbv.gz.\n'
}

die()
{
    printf 'error: %s\n' "$*" >&2
    exit 1
}

require_file()
{
    [[ -f "$1" ]] || die "missing file: $1"
}

resolve_executable()
{
    local requested=$1
    local resolved

    if [[ "$requested" == */* ]]; then
        [[ -x "$requested" ]] || die "not executable: $requested"
        printf '%s\n' "$requested"
        return
    fi

    resolved=$(command -v "$requested" || true)
    [[ -n "$resolved" && -x "$resolved" ]] ||
        die "cannot find executable '$requested'; set QEMU_SYSTEM_AARCH64"
    printf '%s\n' "$resolved"
}

resolve_plugin()
{
    local qemu=$1
    local requested=${SIMPOINT_PLUGIN:-}
    local qemu_dir
    local candidate

    if [[ -n "$requested" ]]; then
        [[ -f "$requested" ]] || die "missing SimPoint plugin: $requested"
        printf '%s\n' "$requested"
        return
    fi

    qemu_dir=$(cd -- "$(dirname -- "$qemu")" && pwd -P)
    for candidate in \
        "$qemu_dir/contrib/plugins/libsimpoint.so" \
        "$qemu_dir/../contrib/plugins/libsimpoint.so"
    do
        if [[ -f "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return
        fi
    done

    die "cannot find libsimpoint.so; set SIMPOINT_PLUGIN"
}

print_command()
{
    printf '+'
    printf ' %q' "$@"
    printf '\n'
}

if [[ $# -eq 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
    usage
    exit 0
fi
[[ $# -eq 2 ]] || {
    usage >&2
    exit 2
}

gcpt_path=$1
profile_dir=$2
require_file "$gcpt_path"

case "$profile_dir" in
    *,*)
        die "profile path must not contain commas"
        ;;
esac

qemu_request=${QEMU_SYSTEM_AARCH64:-qemu-system-aarch64}
qemu=$(resolve_executable "$qemu_request")
plugin=$(resolve_plugin "$qemu")
mkdir -p "$profile_dir"

machine="mini-virt,platform=fs,instruction-count=$INSTRUCTION_COUNT"
plugin_spec="$plugin,trigger=simtrap,interval=$INTERVAL"
plugin_spec+=",target=$profile_dir,dump-final=false"

qemu_args=(
    "$qemu"
    -icount shift=0,sleep=off
    -machine "$machine"
    -cpu "$CPU_MODEL"
    -smp "$HARTS"
    -m "$MEMORY"
    -nographic
    -kernel "$gcpt_path"
    -plugin "$plugin_spec"
)

print_command "${qemu_args[@]}"
exec "${qemu_args[@]}"
