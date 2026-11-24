#!/usr/bin/env bash
#
# mayhem/test.sh — RUN upstream's own absltest suites (absl/flags, absl/logging converter,
# absl/testing parameterized + flagsaver, command_name) through the mayhem/out/absl_tests launcher
# that build.sh built. Each suite asserts values (parsed flag values, help/XML golden text, error
# cases), so a neutered absl fails it; a neutered launcher prints no results and fails too.
# Emits a CTRF (https://ctrf.io) summary. It never builds.
set -uo pipefail
[ -n "${SOURCE_DATE_EPOCH:-}" ] || unset SOURCE_DATE_EPOCH
: "${SRC:=/mayhem}"
cd "$SRC"
RUNNER="$SRC/mayhem/out/absl_tests"
EXPECTED_MODULES=14

emit_ctrf() {
  local tool="$1" passed="$2" failed="$3" skipped="${4:-0}" pending="${5:-0}" other="${6:-0}"
  local tests=$(( passed + failed + skipped + pending + other ))
  cat > "${CTRF_REPORT:-$SRC/ctrf-report.json}" <<JSON
{
  "results": {
    "tool": { "name": "$tool" },
    "summary": {
      "tests": $tests,
      "passed": $passed,
      "failed": $failed,
      "pending": $pending,
      "skipped": $skipped,
      "other": $other
    }
  }
}
JSON
  printf 'CTRF {"results":{"tool":{"name":"%s"},"summary":{"tests":%d,"passed":%d,"failed":%d,"pending":%d,"skipped":%d,"other":%d}}}\n' \
    "$tool" "$tests" "$passed" "$failed" "$pending" "$skipped" "$other"
  [ "$failed" -eq 0 ]
}

if [ ! -x "$RUNNER" ]; then
  echo "FAIL: $RUNNER missing — run mayhem/build.sh first" >&2
  emit_ctrf absltest 0 1
  exit 1
fi

out="$("$RUNNER" 2>&1)"; rc=$?
echo "$out"
passed=0; failed=0; skipped=0; modules=0
while read -r _ mod ran f e s; do
  ran=${ran#ran=}; f=${f#failed=}; e=${e#errors=}; s=${s#skipped=}
  modules=$((modules + 1))
  bad=$((f + e))
  failed=$((failed + bad)); skipped=$((skipped + s))
  passed=$((passed + ran - bad - s))
done < <(printf '%s\n' "$out" | grep '^RESULT ')

if [ "$rc" -ne 0 ] || ! printf '%s' "$out" | grep -q '^SUITE_DONE$' || [ "$modules" -ne "$EXPECTED_MODULES" ]; then
  echo "FAIL: suite runner rc=$rc, reported $modules/$EXPECTED_MODULES modules" >&2
  failed=$((failed + EXPECTED_MODULES - modules + 1))
fi
emit_ctrf absltest "$passed" "$failed" "$skipped"
