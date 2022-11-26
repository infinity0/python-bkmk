from bkmk import *
from bkmk.base import *

import functools
import itertools
import io
import sys
import traceback

def xchildren(cull_special, supported, sortkey, children, depth):
    children = [c for c in children if _keep_child(cull_special, supported, c)]
    return sorted(children, key=sortkey) if sortkey and depth == 0 else children

def test_roundtrip(arg):
    all_passing = True

    fmt_in = guess_format(arg)
    for (fill_special, fill_ids, fill_timestamps, cull_special, cull_attr) in itertools.product((False, True), repeat=5):
        d = locals()
        read_args = {k: d[k] for k in ("fill_special", "fill_ids", "fill_timestamps")}
        write_args = {k: d[k] for k in ("cull_attr", "cull_special")}
        if not Bookmarks.sanity_check_args(False, **read_args, **write_args):
            continue

        try:
            with open(arg) as fp_in:
                bm = Bookmarks.read(fp_in, fmt_in, **read_args)
        except:
            traceback.print_exc()
            print("FAILED:", arg, "could not read", read_args, write_args)
            all_passing = False
            continue

        for fmt in FORMATS.keys():
            try:
                fp1 = io.StringIO()
                bm.write(fp1, fmt, **write_args)
                fp1.flush()
                fp1.seek(0)
                bm1 = Bookmarks.read(fp1, fmt, **read_args)

                fp2 = io.StringIO()
                bm.write(fp2, fmt, **write_args)
                fp2.flush()
                fp2.seek(0)
                bm2 = Bookmarks.read(fp2, fmt, **read_args)

                fmt_module = globals()[fmt.replace("-", "_")]
                accept = fmt_module._roundtrip_acceptable_diff
                supported = list(getattr(fmt_module, "SPECIAL_FOLDERS_BY_ENUM", FOLDER_DEFAULT_NAMES).keys())
                sortkey = getattr(fmt_module, "_roundtrip_sortkey", None)
                ac = functools.partial(accept, cull_attr)
                xc = functools.partial(xchildren, cull_special, supported, sortkey)

                assert bm._debug_eq(bm1, ac, xc)
                assert bm._debug_eq(bm2, ac, xc)

                assert bm1._debug_eq(bm2, ac, xc)
                fp1.seek(0)
                fp2.seek(0)
                assert fp1.read() == fp2.read()
            except:
                traceback.print_exc()
                print("FAILED:", arg, "format:", fmt, read_args, write_args)
                all_passing = False

    if all_passing:
        print("PASSED:", arg)
    return all_passing

def main(_, *argv):
    r = []
    for arg in argv:
        r.append(test_roundtrip(arg))
    return 0 if all(r) else 1

if __name__ == "__main__":
    sys.exit(main(*sys.argv))
