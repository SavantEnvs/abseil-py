#!/usr/bin/python3
"""Atheris harness: absl.flags.argparse_flags.ArgumentParser (the argparse bridge).

A fresh FlagValues per input (string, integer, boolean, multi_string, enum flags) is inherited by
an argparse_flags.ArgumentParser that also has a native argparse option, a positional and a
subcommand; the parser then parses an argv list built from the input. This reaches _FlagAction,
_BooleanFlagAction, the --undefok stripping and the single-dash long-option rewrite, which feed
absl's Flag.parse.

argparse reports bad command lines by printing usage and raising SystemExit (exit_on_error=False
only covers some cases), and --help/--helpfull print and exit: SystemExit and
argparse.ArgumentError are expected, as is flags.Error. stdout/stderr go to a buffer. The cwd is
an empty scratch directory so a fuzzed --flagfile cannot pick up repository files. --flagfile is
not in the token list: the flagfile reader has its own target (fuzz_flagfile.py).
"""
import argparse
import contextlib
import io
import os
import sys
import tempfile

import atheris

from absl import flags
from absl.flags import argparse_flags

os.chdir(tempfile.mkdtemp(prefix='absl-argparse-'))

TOKENS = ['--absl_string', '--absl_integer', '--absl_bool', '--noabsl_bool', '--absl_multi',
          '--absl_enum', '-absl_string', '--native', '--undefok', '--', 'sub',
          '--sub_opt', '-h', '--helpshort']


def _build(fv):
  flags.DEFINE_string('absl_string', 'default', 'h', flag_values=fv)
  flags.DEFINE_integer('absl_integer', 1, 'h', lower_bound=0, flag_values=fv)
  flags.DEFINE_boolean('absl_bool', False, 'h', flag_values=fv)
  flags.DEFINE_multi_string('absl_multi', [], 'h', flag_values=fv)
  flags.DEFINE_enum('absl_enum', 'apple', ['apple', 'orange'], 'h', flag_values=fv)
  parser = argparse_flags.ArgumentParser(inherited_absl_flags=fv, exit_on_error=False,
                                         prog='prog')
  parser.add_argument('--native', type=int, default=0)
  parser.add_argument('pos', nargs='?')
  subs = parser.add_subparsers(dest='cmd')
  sub = subs.add_parser('sub')
  sub.add_argument('--sub_opt')
  return parser


def TestOneInput(data):
  fdp = atheris.FuzzedDataProvider(data)
  argv = []
  for _ in range(fdp.ConsumeIntInRange(0, 10)):
    choice = fdp.ConsumeIntInRange(0, 3)
    if choice == 0:
      argv.append(fdp.ConsumeUnicodeNoSurrogates(32))
    elif choice == 1:
      argv.append(fdp.PickValueInList(TOKENS))
    else:
      argv.append(fdp.PickValueInList(TOKENS) + '=' + fdp.ConsumeUnicodeNoSurrogates(24))
  fv = flags.FlagValues()
  parser = _build(fv)
  sink = io.StringIO()
  with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
    try:
      if fdp.ConsumeBool():
        parser.parse_known_args(argv)
      else:
        parser.parse_args(argv)
    except (SystemExit, argparse.ArgumentError, flags.Error):
      pass


def main():
  atheris.instrument_all()
  atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
  atheris.Fuzz()


if __name__ == '__main__':
  main()
