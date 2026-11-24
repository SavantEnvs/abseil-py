"""Runs upstream's own absltest suites from the source tree and reports per-module counts.

Each module runs in its own interpreter (absltest parses the global FLAGS once per process).
Prints one `RESULT <module> ran=<n> failed=<f> errors=<e> skipped=<s>` line per module, then
`SUITE_DONE`; mayhem/test.sh sums them into CTRF. Tests that need Bazel-built helper binaries
(argparse_flags_test.ArgparseWithAppRunTest, app_test, logging_functional_test, the absltest
subprocess tests) are excluded: they cannot run from a plain source tree.
"""
import os
import re
import subprocess
import sys

MODULES = [
    ('absl.flags.tests.argparse_flags_test', ['ArgparseFlagsTest']),
    ('absl.flags.tests._argument_parser_test', []),
    ('absl.flags.tests.flags_formatting_test', []),
    ('absl.flags.tests.flags_helpxml_test', []),
    ('absl.flags.tests.flags_numeric_bounds_test', []),
    ('absl.flags.tests.flags_test', []),
    ('absl.flags.tests._flag_test', []),
    ('absl.flags.tests._flagvalues_test', []),
    ('absl.flags.tests._helpers_test', []),
    ('absl.flags.tests._validators_test', []),
    ('absl.logging.tests.converter_test', []),
    ('absl.testing.tests.parameterized_test', []),
    ('absl.testing.tests.flagsaver_test', []),
    ('absl.tests.command_name_test', []),
]

def main():
  env = dict(os.environ)
  for mod, selectors in MODULES:
    p = subprocess.run([sys.executable, '-s', '-m', mod] + selectors,
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = p.stdout
    m = re.search(r'^Ran (\d+) tests?', out, re.M)
    ran = int(m.group(1)) if m else 0
    def count(key):
      # `(failures=1, ...)` but not `(expected failures=1)` (an expected failure is a pass)
      mm = re.search(r'^(?:OK|FAILED) \((?:.*?, )?' + key + r'=(\d+)', out, re.M)
      return int(mm.group(1)) if mm else 0
    failed, errors, skipped = count('failures'), count('errors'), count('skipped')
    if (p.returncode != 0 or ran == 0) and failed + errors == 0:
      errors = 1  # crashed, ran nothing, or did not report: count it as a failure
      ran = max(ran, 1)
    if p.returncode != 0 or ran == 0:
      sys.stdout.write(out[-4000:])
    print(f'RESULT {mod} ran={ran} failed={failed} errors={errors} skipped={skipped}', flush=True)
  print('SUITE_DONE', flush=True)

if __name__ == '__main__':
  main()
