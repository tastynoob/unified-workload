#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildMetadata:
    flags: str = ""
    cflags: str = ""
    cxxflags: str = ""
    fflags: str = ""
    fppflags: str = "-DSPEC_CPU -DNDEBUG -DSPEC_CPU_LP64"
    ldflags: str = ""
    libs: str = ""


BENCHMARKS = {
    "400.perlbench": BuildMetadata(
        flags="-DPERL_CORE -DSPEC_CPU_LINUX_X64 -std=gnu89", libs="-lm"
    ),
    "401.bzip2": BuildMetadata(),
    "403.gcc": BuildMetadata(flags="-I./src -std=c11"),
    "410.bwaves": BuildMetadata(),
    "416.gamess": BuildMetadata(
        fflags="-std=legacy -funconstrained-commons -fno-strict-aliasing",
        fppflags=(
            "-DSPEC_CPU_NO_HOLLERITH -DSPEC_CPU -DNDEBUG -DSPEC_CPU_LP64"
        ),
    ),
    "429.mcf": BuildMetadata(flags="-DWANT_STDC_PROTO", libs="-lm"),
    "433.milc": BuildMetadata(
        flags=(
            "-I./src -DFN -DFAST -DCONGRAD_TMP_VECTORS "
            "-DDSLASH_TMP_LINKS"
        ),
        libs="-lm",
    ),
    "434.zeusmp": BuildMetadata(),
    "435.gromacs": BuildMetadata(flags="-I./src -DHAVE_CONFIG_H", libs="-lm"),
    "436.cactusADM": BuildMetadata(
        flags="-I./src/include -DCCODE -D__USE_BSD -std=gnu89"
    ),
    "437.leslie3d": BuildMetadata(),
    "444.namd": BuildMetadata(flags="-std=c++98", libs="-lm"),
    "445.gobmk": BuildMetadata(
        flags="-DHAVE_CONFIG_H -I./src/include", libs="-lm"
    ),
    "447.dealII": BuildMetadata(
        flags=(
            "-I./src/include -DBOOST_DISABLE_THREADS -Ddeal_II_dimension=3 "
            "-include cstring -fpermissive -std=c++98"
        )
    ),
    "450.soplex": BuildMetadata(flags="-std=c++98"),
    "453.povray": BuildMetadata(flags="-std=c++98", libs="-lm"),
    "454.calculix": BuildMetadata(
        flags="-I./src/SPOOLES -Wno-error",
        fflags="-I./src/SPOOLES -Wno-error",
        libs="-lm",
    ),
    "456.hmmer": BuildMetadata(flags="-std=c11", libs="-lm"),
    "458.sjeng": BuildMetadata(),
    "459.GemsFDTD": BuildMetadata(),
    "462.libquantum": BuildMetadata(flags="-DSPEC_CPU_LINUX", libs="-lm"),
    "464.h264ref": BuildMetadata(flags="-fsigned-char -std=c11", libs="-lm"),
    "465.tonto": BuildMetadata(
        fppflags=(
            "-w -DUSE_PRE_AND_POST_CONDITIONS -DUSE_ERROR_MANAGEMENT "
            "-m literal.pm -m tonto.pm -DSPEC_CPU -DNDEBUG -DSPEC_CPU_LP64"
        )
    ),
    "470.lbm": BuildMetadata(libs="-lm"),
    "471.omnetpp": BuildMetadata(
        flags="-I./src -I./src/omnet_include -I./src/libs/envir", libs="-lm"
    ),
    "473.astar": BuildMetadata(
        flags="-DSPEC_CPU_LITTLE_ENDIAN -std=c++98", libs="-lm"
    ),
    "481.wrf": BuildMetadata(
        flags=(
            "-I./src -I./src/netcdf/include -DSPEC_CPU_CASE_FLAG "
            "-DSPEC_CPU_LINUX -Wno-error"
        ),
        fflags=(
            "-I./src -I./src/netcdf/include -std=legacy "
            "-fallow-argument-mismatch"
        ),
        fppflags=(
            "-w -m literal.pm -I. -DINTIO -DIWORDSIZE=4 -DDWORDSIZE=8 "
            "-DRWORDSIZE=4 -DLWORDSIZE=4 -DNETCDF -DTRIEDNTRUE "
            "-DLIMIT_ARGS -DEM_CORE=1 -DNMM_CORE=0 -DNMM_MAX_DIM=1000 "
            "-DCOAMPS_CORE=0 -DEXP_CORE=0 -DF90_STANDALONE "
            "-DCONFIG_BUF_LEN=8192 -DMAX_DOMAINS_F=21 "
            "-DNO_NAMELIST_PRINT -DSPEC_CPU -DNDEBUG -DSPEC_CPU_LP64 "
            "-DSPEC_CPU_CASE_FLAG -DSPEC_CPU_LINUX"
        ),
    ),
    "482.sphinx3": BuildMetadata(
        flags="-I./src -I./src/libutil -DHAVE_CONFIG_H -fsigned-char", libs="-lm"
    ),
    "483.xalancbmk": BuildMetadata(
        flags=(
            "-I./src -I./src/xercesc -I./src/xercesc/dom "
            "-I./src/xercesc/dom/impl -I./src/xercesc/sax "
            "-I./src/xercesc/util/MsgLoaders/InMemory "
            "-I./src/xercesc/util/Transcoders/Iconv -I./src/xalanc/include "
            "-DPROJ_XMLPARSER -DPROJ_XMLUTIL -DPROJ_PARSERS -DPROJ_SAX4C "
            "-DPROJ_SAX2 -DPROJ_DOM -DPROJ_VALIDATORS "
            "-DXML_USE_NATIVE_TRANSCODER -DXML_USE_INMEM_MESSAGELOADER "
            "-DXML_USE_PTHREADS -DAPP_NO_THREADS -DXALAN_INMEM_MSG_LOADER "
            "-DSPEC_CPU_LINUX -include cstring -Wno-error -std=c++98"
        )
    ),
    "998.specrand": BuildMetadata(),
    "999.specrand": BuildMetadata(),
}


# CPU2017 object.pm files provide the source list and language, but the suite's
# build configuration normally supplies these benchmark-specific portability
# flags. This table contains only the C/C++ benchmarks present in SPECspeed.
CPU2017_BENCHMARKS = {
    "perlbench": BuildMetadata(
        flags=(
            "-DPERL_CORE -I. -Idist/IO -Icpan/Time-HiRes "
            "-Icpan/HTML-Parser -Iext/re -Ispecrand "
            "-DDOUBLE_SLASHES_SPECIAL=0 -D_LARGE_FILES "
            "-D_LARGEFILE_SOURCE -DSPEC_LINUX_AARCH64 -DSPEC_LINUX "
            "-D_DEFAULT_SOURCE"
        ),
        cflags="-fno-unsafe-math-optimizations -fno-finite-math-only",
        ldflags="-Wl,-z,muldefs",
        libs="-lm",
    ),
    "gcc": BuildMetadata(
        flags=(
            "-I. -Iinclude -Ispec_qsort -DSPEC_502 -DIN_GCC "
            "-DHAVE_CONFIG_H"
        ),
        ldflags="-Wl,-z,muldefs",
    ),
    "mcf": BuildMetadata(flags="-Ispec_qsort"),
    "lbm": BuildMetadata(libs="-lm"),
    "omnetpp": BuildMetadata(
        flags=(
            "-Isimulator/platdep -Isimulator -Imodel "
            "-DWITH_NETBUILDER -fpermissive"
        )
    ),
    "xalancbmk": BuildMetadata(
        flags=(
            "-DAPP_NO_THREADS -DXALAN_INMEM_MSG_LOADER -I. "
            "-Ixercesc -Ixercesc/dom -Ixercesc/dom/impl "
            "-Ixercesc/sax "
            "-Ixercesc/util/MsgLoaders/InMemory "
            "-Ixercesc/util/Transcoders/Iconv -Ixalanc/include "
            "-DPROJ_XMLPARSER -DPROJ_XMLUTIL -DPROJ_PARSERS "
            "-DPROJ_SAX4C -DPROJ_SAX2 -DPROJ_DOM -DPROJ_VALIDATORS "
            "-DXML_USE_INMEM_MESSAGELOADER -DSPEC_LINUX -fpermissive"
        )
    ),
    "x264": BuildMetadata(
        flags=(
            "-Ildecod_src/inc -Ix264_src -Ix264_src/extras "
            "-Ix264_src/common -DSPEC_AUTO_BYTEORDER=0x12345678 "
            "-fcommon"
        ),
        libs="-lm",
    ),
    "deepsjeng": BuildMetadata(flags="-DSMALL_MEMORY"),
    "imagick": BuildMetadata(flags="-I.", libs="-lm"),
    "leela": BuildMetadata(flags="-I."),
    "nab": BuildMetadata(
        flags=(
            "-Ispecrand -Iregex-alpha -DNOPERFLIB -DNOREDUCE"
        ),
        libs="-lm",
    ),
    "xz": BuildMetadata(
        flags=(
            "-DSPEC_AUTO_BYTEORDER=0x12345678 -DHAVE_CONFIG_H=1 "
            "-DSPEC_MEM_IO -DSPEC_XZ -I. -Ispec_mem_io "
            "-Isha-2 -Icommon -Iliblzma/api "
            "-Iliblzma/lzma -Iliblzma/common "
            "-Iliblzma/check -Iliblzma/simple "
            "-Iliblzma/delta -Iliblzma/lz "
            "-Iliblzma/rangecoder"
        )
    ),
}

CPU2017_SPEED_NAMES = frozenset(CPU2017_BENCHMARKS)


def parse_scalar(text: str, name: str) -> str:
    match = re.search(rf"\${name}\s*=\s*(['\"])(.*?)\1\s*;", text)
    if match is None:
        raise ValueError(f"object.pm does not define ${name}")
    return match.group(2)


def parse_perl_string_assignments(text: str, name: str) -> str:
    pattern = re.compile(
        rf"\${name}\s*(=|\.=)\s*(['\"])((?:\\.|(?!\2).)*)\2\s*;",
        re.DOTALL,
    )
    value = ""
    for match in pattern.finditer(text):
        fragment = match.group(3).replace("\\'", "'").replace('\\"', '"')
        fragment = fragment.replace("\\\\", "\\")
        if match.group(1) == "=":
            value = fragment
        else:
            value = " ".join(part for part in (value, fragment) if part)
    return " ".join(value.split())


def parse_sources(text: str, executable: str = "") -> list[str]:
    for variable in ("sources", "orig_sources"):
        match = re.search(
            rf"@{variable}\s*=\s*\(?\s*qw\s*\((.*?)\)\s*\)?\s*;",
            text,
            re.DOTALL,
        )
        if match is not None:
            block = re.sub(r"#.*", "", match.group(1))
            sources = block.split()
            if sources:
                return sources
        match = re.search(
            rf"@{variable}\s*=\s*\((.*?)\)\s*;", text, re.DOTALL
        )
        if match is not None:
            sources = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
            if sources:
                return sources
    if executable:
        match = re.search(
            rf"['\"]{re.escape(executable)}['\"]\s*=>\s*"
            r"\[\s*qw\s*\((.*?)\)\s*\]",
            text,
            re.DOTALL,
        )
        if match is not None:
            block = re.sub(r"#.*", "", match.group(1))
            sources = block.split()
            if sources:
                return sources
    raise ValueError("object.pm does not contain a supported source list")


def expand_source_patterns(source_dir: Path, sources: list[str]) -> list[str]:
    expanded: list[str] = []
    for source in sources:
        if not any(character in source for character in "*?["):
            expanded.append(source)
            continue
        matches = sorted(
            path.relative_to(source_dir).as_posix()
            for path in source_dir.glob(source)
            if path.is_file()
        )
        if not matches:
            raise ValueError(f"source pattern does not match any files: {source}")
        expanded.extend(matches)
    return expanded


def resolve_source_metadata(
    suite: str, benchmark_dir: Path, object_text: str, source_dir: Path
) -> tuple[Path, Path, str]:
    if suite != "2017":
        return benchmark_dir, source_dir, object_text

    match = re.search(r"\$sources\s*=\s*(['\"])(.*?)\1\s*;", object_text)
    if match is None:
        return benchmark_dir, source_dir, object_text

    source_benchmark_dir = benchmark_dir.parent / match.group(2)
    source_object_pm = source_benchmark_dir / "Spec" / "object.pm"
    resolved_source_dir = source_benchmark_dir / "src"
    if not source_object_pm.is_file() or not resolved_source_dir.is_dir():
        raise ValueError(
            f"inherited source benchmark is incomplete: {source_benchmark_dir}"
        )
    source_text = source_object_pm.read_text(encoding="utf-8", errors="replace")
    return source_benchmark_dir, resolved_source_dir, source_text


def has_fortran(language: str, sources: list[str]) -> bool:
    languages = set(re.findall(r"[A-Z0-9+]+", language.upper()))
    if languages.intersection({"F", "F77", "F90", "FORTRAN"}):
        return True
    return any(
        Path(source).suffix.lower() in {".f", ".f77", ".f90", ".for", ".ftn"}
        for source in sources
    )


def has_cxx(language: str, sources: list[str]) -> bool:
    if "CXX" in language.upper() or "C++" in language.upper():
        return True
    return any(
        Path(source).suffix in {".C", ".cc", ".cpp", ".cxx"}
        for source in sources
    )


def join_flags(*values: str) -> str:
    return " ".join(value for value in values if value)


def native_fpp_flags(value: str) -> str:
    tokens = shlex.split(value)
    result: list[str] = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token == "-m":
            skip = True
            continue
        result.append(token)
    return " ".join(result)


def cpu2017_metadata(text: str, benchmark: str) -> BuildMetadata:
    name = benchmark.split(".", 1)[-1].rsplit("_", 1)[0]
    defaults = (
        CPU2017_BENCHMARKS[name]
        if name in CPU2017_SPEED_NAMES
        else BuildMetadata(fppflags="")
    )
    need_math = re.search(
        r"\$need_math\s*=\s*(?:1|(['\"])yes\1)\s*;", text, re.IGNORECASE
    ) is not None
    libs = defaults.libs
    if need_math and "-lm" not in libs.split():
        libs = join_flags(libs, "-lm")
    bench_flags = parse_perl_string_assignments(text, "bench_flags")
    if name == "deepsjeng":
        bench_flags = " ".join(
            flag for flag in bench_flags.split() if flag != "-DBIG_MEMORY"
        )
    return BuildMetadata(
        flags=join_flags(defaults.flags, bench_flags),
        cflags=join_flags(
            defaults.cflags, parse_perl_string_assignments(text, "bench_cflags")
        ),
        cxxflags=join_flags(
            defaults.cxxflags,
            parse_perl_string_assignments(text, "bench_cxxflags"),
        ),
        fflags=parse_perl_string_assignments(text, "bench_fflags"),
        fppflags=native_fpp_flags(
            parse_perl_string_assignments(text, "bench_fppflags")
        ),
        ldflags=join_flags(
            defaults.ldflags,
            parse_perl_string_assignments(text, "bench_ldflags"),
        ),
        libs=libs,
    )


def make_list(name: str, values: list[str]) -> str:
    lines = [f"{name} := \\"]
    lines.extend(f"  {value} \\" for value in values[:-1])
    lines.append(f"  {values[-1]}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("2006", "2017"), required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--bench-dir", type=Path, required=True)
    parser.add_argument("--object-pm", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.suite == "2006" and args.benchmark not in BENCHMARKS:
        parser.error(f"unsupported CPU2006 benchmark: {args.benchmark}")

    text = args.object_pm.read_text(encoding="utf-8", errors="replace")
    language = parse_scalar(text, "benchlang")
    executable = parse_scalar(text, "exename")
    try:
        source_benchmark_dir, source_dir, source_text = resolve_source_metadata(
            args.suite, args.bench_dir, text, args.source_dir
        )
        source_executable = parse_scalar(source_text, "exename")
        sources = expand_source_patterns(
            source_dir, parse_sources(source_text, source_executable)
        )
    except ValueError as error:
        parser.error(str(error))

    missing = [source for source in sources if not (source_dir / source).is_file()]
    if missing:
        parser.error("source files missing from SPEC tree: " + ", ".join(missing))

    if has_fortran(language, sources):
        link_language = "FC"
    elif has_cxx(language, sources):
        link_language = "CXX"
    else:
        link_language = "CC"

    if args.suite == "2017":
        metadata = cpu2017_metadata(text, args.benchmark)
    else:
        metadata = BENCHMARKS[args.benchmark]
    needs_specpp = any(Path(source).suffix in (".F", ".F90") for source in sources)
    output = [
        f"# Generated from the read-only SPEC CPU{args.suite} tree.",
        f"SPEC_SUITE_METADATA := {args.suite}",
        f"SPEC_SOURCE_BENCH_DIR := {source_benchmark_dir.resolve()}",
        f"SPEC_SOURCE_DIR := {source_dir.resolve()}",
        f"SPEC_EXE_NAME := {executable}",
        f"SPEC_BENCH_LANGUAGE := {language}",
        f"SPEC_LINK_LANGUAGE := {link_language}",
        f"SPEC_NEEDS_SPECPP := {1 if needs_specpp else 0}",
        f"SPEC_BENCH_FLAGS := {metadata.flags}",
        f"SPEC_BENCH_CFLAGS := {metadata.cflags}",
        f"SPEC_BENCH_CXXFLAGS := {metadata.cxxflags}",
        f"SPEC_BENCH_FFLAGS := {metadata.fflags}",
        f"SPEC_BENCH_FPPFLAGS := {metadata.fppflags}",
        f"SPEC_BENCH_LDFLAGS := {metadata.ldflags}",
        f"SPEC_BENCH_LIBS := {metadata.libs}",
        make_list("SPEC_SOURCES", sources),
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(output), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
