#!/usr/bin/python3
"""Atheris harness: every typed absl flag parser, through FlagValues command-line parsing.

A fresh FlagValues per input defines one flag of each DEFINE_* kind (bounded integer/float,
boolean, enum, enum_class, list, spaceseplist with comma compat, multi_string/integer/float/enum/
enum_class, an alias) plus a validator, then parses an argv built from the input: each argument
is `--name=value`, `--name value`, `--noname`, `-name=value`, a positional, `--` or an
`--undefok=` list, with fuzzed values. On success it serializes the flags (flags_into_string,
flag_values_dict, per-flag serialize) and parses the serialized form again on a fresh FlagValues.

Expected rejections: flags.Error (IllegalFlagValueError, UnrecognizedFlagError,
ValidationError, ...). Anything else escaping absl is a finding.
"""
import enum
import sys

import atheris

from absl import flags


class Color(enum.Enum):
  RED = 1
  GREEN = 2
  BLUE = 3


NAMES = ['int', 'float', 'bool', 'enum', 'color', 'list', 'spaces', 'mstr', 'mint',
         'mfloat', 'menum', 'mcolor', 'str', 'alias_str', 'undefok', 'unknown']
# No 'flagfile' here: the flagfile reader has its own target (fuzz_flagfile.py), with files it controls.


def _define(fv):
  flags.DEFINE_integer('int', 1, 'h', lower_bound=-50, upper_bound=1 << 40, flag_values=fv)
  flags.DEFINE_float('float', 1.5, 'h', lower_bound=-1e9, upper_bound=1e9, flag_values=fv)
  flags.DEFINE_boolean('bool', False, 'h', flag_values=fv)
  flags.DEFINE_enum('enum', 'apple', ['apple', 'Orange', 'PEAR'], 'h', case_sensitive=False,
                    flag_values=fv)
  flags.DEFINE_enum_class('color', Color.RED, Color, 'h', flag_values=fv)
  flags.DEFINE_list('list', ['a', 'b'], 'h', flag_values=fv)
  flags.DEFINE_spaceseplist('spaces', 'x y', 'h', comma_compat=True, flag_values=fv)
  flags.DEFINE_multi_string('mstr', ['s'], 'h', flag_values=fv)
  flags.DEFINE_multi_integer('mint', [1], 'h', lower_bound=0, upper_bound=100, flag_values=fv)
  flags.DEFINE_multi_float('mfloat', [0.5], 'h', flag_values=fv)
  flags.DEFINE_multi_enum('menum', ['a'], ['a', 'b', 'c'], 'h', flag_values=fv)
  flags.DEFINE_multi_enum_class('mcolor', [Color.GREEN], Color, 'h', case_sensitive=False,
                                flag_values=fv)
  flags.DEFINE_string('str', 'hello', 'h', flag_values=fv)
  flags.DEFINE_alias('alias_str', 'str', flag_values=fv)
  flags.register_validator('int', lambda v: v is None or v % 7 != 3, message='int % 7 == 3',
                           flag_values=fv)
  flags.register_multi_flags_validator(
      ['float', 'mint'], lambda d: not (d['float'] == 0.0 and not d['mint']),
      message='float 0 needs mint', flag_values=fv)


def _arg(fdp):
  name = fdp.PickValueInList(NAMES)
  if fdp.ConsumeIntInRange(0, 15) == 0:
    name = fdp.ConsumeUnicodeNoSurrogates(16)
  value = fdp.ConsumeUnicodeNoSurrogates(48)
  form = fdp.ConsumeIntInRange(0, 7)
  if form == 0:
    return ['--%s=%s' % (name, value)]
  if form == 1:
    return ['--%s' % name, value]
  if form == 2:
    return ['--no%s' % name]
  if form == 3:
    return ['-%s=%s' % (name, value)]
  if form == 4:
    return ['--%s' % name]
  if form == 5:
    return [value]
  if form == 6:
    return ['--']
  return ['--undefok=%s' % value]


def TestOneInput(data):
  fdp = atheris.FuzzedDataProvider(data)
  gnu = fdp.ConsumeBool()
  argv = ['prog']
  for _ in range(fdp.ConsumeIntInRange(0, 12)):
    argv += _arg(fdp)

  fv = flags.FlagValues()
  _define(fv)
  fv.set_gnu_getopt(gnu)
  try:
    fv(argv)
  except flags.Error:
    return
  serialized = fv.flags_into_string()
  fv.flag_values_dict()
  for flag in fv._flags().values():
    flag.serialize()

  # flags_into_string() separates assignments with '\n' only (it is the flagfile format), so split
  # on exactly that: str.splitlines() would also cut a value at \r, \v, \f, \x1c-\x1e, \x85 or
  # \u2028/9 and hand absl argv elements its serializer never produced.
  fv2 = flags.FlagValues()
  _define(fv2)
  try:
    fv2(['prog'] + serialized.split('\n')[:-1])
  except flags.Error:
    pass


def main():
  atheris.instrument_all()
  atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
  atheris.Fuzz()


if __name__ == '__main__':
  main()
