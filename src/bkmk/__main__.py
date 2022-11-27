#!/usr/bin/python3

from bkmk import *

import argparse
import contextlib

import os.path
import sys


def file_or_std(stack, path, mode, fmt, flag, stdname, std):
    if path and path != '-':
        fp = stack.enter_context(open(path, mode))
        fmt = fmt if fmt else guess_format(path, verbose=True)
    else:
        fp = std
        if fmt is None:
            raise ValueError("must give explicit %s when using %s" % (flag, stdname))
    return (fp, fmt)

def _real_main(_prog, *argv):
    parser = argparse.ArgumentParser(
        prog = "bkmk",
        description = 'Convert between different bookmark formats')

    parser.add_argument(
        'input', nargs='?', default=None, help="Input path; omit or '-' for stdin.")
    parser.add_argument(
        'output', nargs='?', default=None, help="Output path; omit or '-' for stdout.")
    parser.add_argument(
        '-f', '--from', metavar='FMT', dest='fmt_in', default=None, choices=FORMATS.keys(),
        help="Input format, one of: %s. Omit to auto-detect from input path." % ", ".join(FORMATS.keys()))
    parser.add_argument(
        '-t', '--to', metavar='FMT', dest='fmt_out', default=None, choices=FORMATS.keys(),
        help="Output format, one of: %s. Omit to auto-detect from output path." % ", ".join(FORMATS.keys()))
    parser.add_argument(
        '--fill-special', default=False, action=argparse.BooleanOptionalAction,
        help="Fill in missing special folders after reading, so every special folder exists")
    parser.add_argument(
        '--fill-ids', default=False, action=argparse.BooleanOptionalAction,
        help="Fill in missing ids after reading, so every element has an id")
    parser.add_argument(
        '--fill-timestamps', default=False, action=argparse.BooleanOptionalAction,
        help="Fill in missing timestamps after reading, so every element has all timestamps")
    parser.add_argument(
        '--prefix-ids', default="", metavar="PREFIX",
        help="Add a prefix to all existing ids after reading, useful when combining several sources")
    parser.add_argument(
        '--cull-special', default=False, action=argparse.BooleanOptionalAction,
        help="Cull empty special folders that are not recognised by the output format")
    parser.add_argument(
        '--cull-attr', default=False, action=argparse.BooleanOptionalAction,
        help="""Cull attributes that are not recognised in-context by the output format. \
        That is, attributes that are supported by the format but are attached to an \
        inappropriate element. We never emit attributes if the format does not support \
        it for any element, since that requires making up an attribute name from thin air.
        """)
    args = parser.parse_args(argv)

    with contextlib.ExitStack() as stack:
        fp_in, fmt_in = file_or_std(stack, args.input, "r", args.fmt_in, "-f", "stdin", sys.stdin)
        fp_out, fmt_out = file_or_std(stack, args.output, "w", args.fmt_out, "-t", "stdout", sys.stdout)
        Bookmarks.sanity_check_args(True, **args.__dict__)
        Bookmarks.read(
            fp_in, fmt_in,
            **{k: getattr(args, k) for k in ("fill_special", "fill_ids", "fill_timestamps", "prefix_ids")}
        ).write(
            fp_out, fmt_out,
            **{k: getattr(args, k) for k in ("cull_special", "cull_attr")}
        )
    return 0

def main():
    return _real_main(*sys.argv)

if __name__ == "__main__":
    sys.exit(main())
