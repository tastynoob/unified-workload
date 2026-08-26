#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=scripts/a64-gcpt-simpoint-config.sh
source "$script_dir/a64-gcpt-simpoint-config.sh"

usage()
{
    printf 'Usage: %s <gcpt-path> <cluster-dir> <slice-output-dir>\n' \
        "$(basename "$0")"
    printf '\nThe cluster directory must contain simpoints0 and weights0.\n'
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
[[ $# -eq 3 ]] || {
    usage >&2
    exit 2
}

gcpt_path=$1
cluster_dir=$2
slice_output_dir=$3

require_file "$gcpt_path"
require_file "$cluster_dir/simpoints0"
require_file "$cluster_dir/weights0"

case "$cluster_dir$slice_output_dir" in
    *,*)
        die "cluster and output paths must not contain commas"
        ;;
esac

qemu_request=${QEMU_SYSTEM_AARCH64:-qemu-system-aarch64}
qemu=$(resolve_executable "$qemu_request")
mkdir -p "$slice_output_dir"

machine="mini-virt,platform=fs,instruction-count=$INSTRUCTION_COUNT"
machine+=",checkpoint-mode=SimpointCheckpoint"
machine+=",simpoint-path=$cluster_dir,cpt-interval=$INTERVAL"
machine+=",warmup-interval=$WARMUP"
machine+=",checkpoint-dir=$slice_output_dir"
machine+=",checkpoint-exit-after-last=on"

qemu_args=(
    "$qemu"
    -icount shift=0,sleep=off
    -machine "$machine"
    -cpu "$CPU_MODEL"
    -smp "$HARTS"
    -m "$MEMORY"
    -nographic
    -kernel "$gcpt_path"
)

print_command "${qemu_args[@]}"
exec "${qemu_args[@]}"
