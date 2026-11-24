#!/usr/bin/python3
"""Atheris harness: absl.flags --flagfile reader (FlagValues.read_flags_from_files).

Input layout: byte 0 holds options (bit 0: GNU getopt, bit 1: also pass --flagfile=inc.cfg on the
command line); the rest is split at the first NUL byte into two flag files, main.cfg and inc.cfg, written into a private scratch
directory that is also the cwd (so `--flagfile=inc.cfg` / `--flagfile=main.cfg` inside a file
resolve to them: nesting and cycle detection are reachable). A fresh FlagValues with one flag of
each common kind parses ['prog', '--flagfile=main.cfg', ...] with GNU getopt on or off,
then serializes the result. Both files are rewritten on every input, so nothing carries over.

Expected rejections: flags.Error (bad/unknown flag, unreadable file, illegal value) and
UnicodeDecodeError (the reader opens the file as text; non-UTF-8 bytes are not a flag file).
"""
import os
import sys
import tempfile

import atheris

from absl import flags

_SCRATCH = tempfile.mkdtemp(prefix='absl-flagfile-')
os.chdir(_SCRATCH)
_MAIN = os.path.join(_SCRATCH, 'main.cfg')
_INC = os.path.join(_SCRATCH, 'inc.cfg')


def _define(fv):
  flags.DEFINE_string('name', 'default', 'a string', flag_values=fv)
  flags.DEFINE_integer('count', 0, 'an int', lower_bound=-1000, upper_bound=1000,
                       flag_values=fv)
  flags.DEFINE_boolean('verbose', False, 'a bool', flag_values=fv)
  flags.DEFINE_float('ratio', 0.5, 'a float', flag_values=fv)
  flags.DEFINE_list('items', [], 'a list', flag_values=fv)
  flags.DEFINE_multi_string('tag', [], 'a multi string', flag_values=fv)
  flags.DEFINE_enum('mode', 'a', ['a', 'b', 'c'], 'an enum', flag_values=fv)


def TestOneInput(data):
  if not data:
    return
  opts = data[0]
  main_bytes, _, inc_bytes = data[1:].partition(b'\0')
  with open(_MAIN, 'wb') as f:
    f.write(main_bytes)
  with open(_INC, 'wb') as f:
    f.write(inc_bytes)

  fv = flags.FlagValues()
  _define(fv)
  fv.set_gnu_getopt(bool(opts & 1))
  argv = ['prog', '--flagfile=main.cfg']
  if opts & 2:
    argv += ['--flagfile=inc.cfg', 'positional']
  try:
    fv(argv)
  except (flags.Error, UnicodeDecodeError):
    return
  fv.flags_into_string()
  fv.flag_values_dict()


def main():
  atheris.instrument_all()
  atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
  atheris.Fuzz()


if __name__ == '__main__':
  main()
