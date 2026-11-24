#!/usr/bin/python3
"""Atheris harness: absl.flags help / XML rendering and the _helpers text utilities.

A fresh FlagValues per input gets flags whose help text, defaults and enum values come from the
input, then renders get_help(), module_help(), main_module_help() and write_help_in_xml_format();
the XML output must re-parse with xml.dom.minidom (absl strips characters that are illegal in XML,
so malformed output is a finding). It also runs the string helpers absl uses to format help:
text_wrap, doc_to_help, trim_docstring, get_flag_suggestions and flag_dict_to_args.

Expected rejections: flags.Error from DEFINE_* (fuzzed defaults/values may be illegal), the
documented ValueErrors of text_wrap (indent longer than the line), and the ValueErrors DEFINE_enum
raises for empty enum values.
"""
import io
import sys
import xml.dom.minidom

import atheris

from absl import flags
from absl.flags import _helpers


def TestOneInput(data):
  fdp = atheris.FuzzedDataProvider(data)

  def rs(n=64):
    return fdp.ConsumeUnicodeNoSurrogates(n)

  fv = flags.FlagValues()
  defined = []
  for idx in range(fdp.ConsumeIntInRange(0, 6)):
    kind = fdp.ConsumeIntInRange(0, 5)
    name = 'f%d_%s' % (idx, ''.join(c for c in rs(8) if c.isalnum() or c == '_'))
    try:
      if kind == 0:
        flags.DEFINE_string(name, rs(), rs(200), flag_values=fv)
      elif kind == 1:
        flags.DEFINE_integer(name, rs(12), rs(200), flag_values=fv)
      elif kind == 2:
        flags.DEFINE_boolean(name, fdp.ConsumeBool(), rs(200), flag_values=fv)
      elif kind == 3:
        values = [v for v in (rs(16) for _ in range(fdp.ConsumeIntInRange(1, 4))) if v]
        if not values:
          continue  # DEFINE_enum's contract: enum_values must be a non-empty list
        flags.DEFINE_enum(name, fdp.PickValueInList(values), values, rs(200), flag_values=fv)
      elif kind == 4:
        flags.DEFINE_list(name, rs(), rs(200), flag_values=fv)
      else:
        flags.DEFINE_multi_string(name, [rs(), rs()], rs(200), flag_values=fv)
      defined.append(name)
    except flags.Error:
      pass

  prefix = rs(8)
  fv.get_help(prefix=prefix, include_special_flags=fdp.ConsumeBool())
  fv.main_module_help()
  for module in list(fv.flags_by_module_dict()):
    fv.module_help(module)
  out = io.StringIO()
  fv.write_help_in_xml_format(out)
  xml.dom.minidom.parseString(out.getvalue())

  text = rs(400)
  length = fdp.ConsumeIntInRange(1, 120)
  indent = rs(8)
  first = rs(8) if fdp.ConsumeBool() else None
  try:
    _helpers.text_wrap(text, length, indent, first)
  except ValueError:
    pass  # documented: indent / firstline_indent longer than length
  _helpers.doc_to_help(text)
  _helpers.trim_docstring(text)
  _helpers.get_flag_suggestions(rs(32), defined + ['alpha', 'beta', 'gamma'])
  _helpers.flag_dict_to_args({rs(8): rs(16), rs(8): None, rs(8): [rs(8), rs(8)]})


def main():
  atheris.instrument_all()
  atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
  atheris.Fuzz()


if __name__ == '__main__':
  main()
