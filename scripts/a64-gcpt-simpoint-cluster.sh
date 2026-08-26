#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=scripts/a64-gcpt-simpoint-config.sh
source "$script_dir/a64-gcpt-simpoint-config.sh"

usage()
{
    printf 'Usage: %s <profile-dir> <cluster-dir>\n' "$(basename "$0")"
    printf '\nThe profile directory must contain simpoint_bbv.gz.\n'
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
        die "cannot find executable '$requested'; set SIMPOINT_BIN"
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
[[ $# -eq 2 ]] || {
    usage >&2
    exit 2
}

profile_dir=$1
cluster_dir=$2
bbv="$profile_dir/simpoint_bbv.gz"
require_file "$bbv"

case "$cluster_dir" in
    *,*)
        die "cluster path must not contain commas"
        ;;
esac

simpoint_request=${SIMPOINT_BIN:-simpoint}
simpoint=$(resolve_executable "$simpoint_request")
mkdir -p "$cluster_dir"

simpoint_args=(
    "$simpoint"
    -loadFVFile "$bbv"
    -saveSimpoints "$cluster_dir/simpoints0"
    -saveSimpointWeights "$cluster_dir/weights0"
    -inputVectorsGzipped
    -maxK "$MAX_K"
    -numInitSeeds "$NUM_INIT_SEEDS"
    -iters "$ITERS"
    -seedkm "$SEED_KM"
    -seedproj "$SEED_PROJ"
)

print_command "${simpoint_args[@]}"
"${simpoint_args[@]}"

require_file "$cluster_dir/simpoints0"
require_file "$cluster_dir/weights0"
[[ -s "$cluster_dir/simpoints0" ]] || die "empty SimPoint file: $cluster_dir/simpoints0"
[[ -s "$cluster_dir/weights0" ]] || die "empty SimPoint file: $cluster_dir/weights0"
