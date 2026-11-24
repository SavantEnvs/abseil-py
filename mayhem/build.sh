#!/usr/bin/env bash
#
# mayhem/build.sh — build the absl-py Atheris fuzz targets (pure Python).
#
# Runs in the commit image (mayhem/Dockerfile) as `mayhem` in /mayhem. absl-py has no runtime
# dependencies and no compiled code: the harnesses import absl straight from this source tree
# (PYTHONPATH=/mayhem, set by the launcher), so a patched tree is fuzzed/graded without any
# reinstall. Atheris (the coverage-guided Python fuzzer, libFuzzer CLI) instruments the Python
# bytecode at run time; SANITIZER_FLAGS has nothing native to instrument here.
#
# Mayhem needs an ELF `cmd`, so each harness gets a tiny clang-built launcher (mayhem/launcher.c,
# DWARF 3 via $DEBUG_FLAGS) that execs python3 on it. The launchers are built WITHOUT the sanitizer
# flags: an ASan runtime in a 30-line exec shim would only be dragged into the python child.
#
# Air-gapped (SPEC §6.5): the first (online) run downloads the pinned atheris wheel into a
# wheelhouse under /opt/toolchains/python and installs it from there with --no-index; the offline
# PATCH re-run finds it already installed (or re-installs from the wheelhouse) and never reaches PyPI.
set -euo pipefail

[ -n "${SOURCE_DATE_EPOCH:-}" ] || unset SOURCE_DATE_EPOCH
: "${SANITIZER_FLAGS=-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer}"
: "${DEBUG_FLAGS:=-g -gdwarf-3}"
: "${CC:=clang}"
: "${SRC:=/mayhem}"
: "${MAYHEM_JOBS:=$(nproc)}"
: "${PY_TOOLCHAIN:=/opt/toolchains/python}"
export SANITIZER_FLAGS DEBUG_FLAGS CC SRC MAYHEM_JOBS

ATHERIS_VERSION=3.1.0
WHEELHOUSE="$PY_TOOLCHAIN/wheelhouse"
SITE="$PY_TOOLCHAIN/site"
HARNESS_DIR="$SRC/mayhem"
OUT="$SRC/mayhem/out"
cd "$SRC"

# 1) atheris, offline-first.
if ! PYTHONPATH="$SITE" python3 -s -c "import atheris, importlib.metadata as m; assert m.version('atheris') == '$ATHERIS_VERSION'" 2>/dev/null; then
  if ! ls "$WHEELHOUSE"/atheris-"$ATHERIS_VERSION"-*.whl >/dev/null 2>&1; then
    mkdir -p "$WHEELHOUSE"
    python3 -m pip download --only-binary=:all: --no-deps --dest "$WHEELHOUSE" "atheris==$ATHERIS_VERSION"
  fi
  rm -rf "$SITE"
  python3 -m pip install --no-index --find-links "$WHEELHOUSE" --no-deps --target "$SITE" \
    "atheris==$ATHERIS_VERSION"
fi

# 2) ELF launchers — the Mayhem targets (each is also its own one-input reproducer).
mkdir -p "$OUT"
for h in fuzz_argparse fuzz_flagfile fuzz_flag_parsers fuzz_help_xml fuzz_argparse_flags; do
  $CC $DEBUG_FLAGS -O1 -DSCRIPT_PATH="\"$HARNESS_DIR/$h.py\"" -DSRC_ROOT="\"$SRC\"" \
      -DSITE_DIR="\"$SITE\"" "$HARNESS_DIR/launcher.c" -o "$OUT/$h"
  cp -f "$OUT/$h" "$OUT/$h-standalone"
done

# 3) Launcher for the functional suite (test.sh runs it; a non-system ELF so the sabotage check
#    can neuter it).
$CC $DEBUG_FLAGS -O1 -DORACLE_PATH="\"$HARNESS_DIR/run_tests.py\"" -DSRC_ROOT="\"$SRC\"" \
    "$HARNESS_DIR/oracle_launch.c" -o "$OUT/absl_tests"

# 4) Fail early if the harnessed API drifted.
PYTHONPATH="$SRC:$SITE" PYTHONDONTWRITEBYTECODE=1 python3 -s -c \
  "import atheris; from absl import flags; from absl.flags import argparse_flags, _helpers"

echo ">> build.sh done: launchers in $OUT"
