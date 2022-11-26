from dataclasses import dataclass

from . import bkmk_json, xbel, chrome_json, netscape_html
from .base import *

FORMAT_EXTS = {
    ".xbel": ["xbel"],
    ".html": ["netscape-html"],
    ".bkmk.json": ["bkmk-json"],
    ".json": ["chrome-json", "bkmk-json"],
}

FORMATS = {
    "bkmk-json": "bkmk JSON - own custom format, easiest for scripting with jq(1)",
    "xbel": "XML Bookmark Exchange Language 1.0",
    "netscape-html": "NETSCAPE Bookmark file 1 - supported by most browsers including Firefox and Chrome",
    "chrome-json": "Chrome Bookmarks JSON - used internally by Chrome",
}

def guess_format(name, verbose=False):
    fmt = None
    for ext, fmts in FORMAT_EXTS.items():
        if name.endswith(ext):
            fmt = fmts[0]
            if len(fmts) > 1 and verbose:
                log("note: guessing format %s for *%s; possible others are: %s" % (fmt, ext, ", ".join(fmts[1:])))
            break
    if fmt is not None:
        return fmt
    else:
        raise ValueError("could not guess format of %s" % name)

def _to_numid(i):
    if not i: return (0, i)
    try:
        return (int(i), i)
    except ValueError:
        return (10**len(i), i)

def _find_max_id(node):
    iid = _to_numid(node.id)
    if isinstance(node, Folder):
        return max([iid] + [_find_max_id(c) for c in node.children])
    else:
        return iid

def _fill_ids(ref, node):
    if node.id == "":
        node.id = str(ref[0])
        ref[0] += 1
    if isinstance(node, Folder):
        for c in node.children:
            _fill_ids(ref, c)

def _find_special_folders(rem, node):
    if isinstance(node, Folder):
        if node.special:
            rem.pop(node.special, None)
        for c in node.children:
            _find_special_folders(rem, c)

def _fill_timestamps(node, ts):
    if isinstance(node, Separator):
        if node.date_added is None:
            node.date_added = ts
    elif isinstance(node, Bookmark):
        if node.date_added is None:
            node.date_added = ts
        if node.date_modified is None:
            node.date_modified = ts
        if node.url_date_modified is None:
            node.url_date_modified = ts
        if node.url_date_visited is None:
            node.url_date_visited = ts
    elif isinstance(node, Folder):
        if node.date_added is None:
            node.date_added = ts
        if node.date_modified is None:
            node.date_modified = ts
        for c in node.children:
            _fill_timestamps(c, ts)
    else:
        assert False

@dataclass
class Bookmarks:
    root: Folder

    def _debug_eq(self, other, accept, xchildren):
        return self.root._debug_eq(other.root, accept, xchildren)

    def fill_special(self):
        """Fill in missing special folders, so every special folder exists"""
        rem = dict(FOLDER_DEFAULT_NAMES)
        _find_special_folders(rem, self.root)
        root_name = rem.pop(None)
        if not self.root.name:
            self.root.name = root_name
        extra_children = []
        for (special, name) in rem.items():
            extra_children.append(Folder("", None, name, "", None, [], special))
        self.root.children = extra_children + self.root.children

    def fill_ids(self):
        """Fill in missing ids, so every element has an id"""
        max_id = _find_max_id(self.root)
        _fill_ids([max_id[0] + 1], self.root)

    def fill_timestamps(self, ts=None):
        """Fill in missing timestamps, so every element has all timestamps"""
        if ts is None:
            import time
            ts = int(time.time() * 1000000)
        _fill_timestamps(self.root, ts)

    @classmethod
    def new(cls):
        return cls(Folder.new())

    @classmethod
    def read(cls, fp_in, fmt_in, fill_special=False, fill_ids=False, fill_timestamps=False):
        if fmt_in not in FORMATS:
            raise ValueError("not a valid format: %s" % fmt_in)
        bm = cls(globals()[fmt_in.replace("-", "_")].read(fp_in))
        if fill_special:
            bm.fill_special()
        if fill_ids:
            bm.fill_ids()
        if fill_timestamps:
            bm.fill_timestamps()
        return bm

    def write(self, fp_out, fmt_out, cull_special=False, cull_attr=False):
        if fmt_out not in FORMATS:
            raise ValueError("not a valid format: %s" % fmt_out)
        globals()[fmt_out.replace("-", "_")].write(self.root, fp_out, cull_special, cull_attr)

    @staticmethod
    def sanity_check_args(do_warn, **kwargs):
        ok = [True]
        def bad_args(s):
            if do_warn: log("warn:", s)
            ok[0] = False
        if not kwargs["cull_special"] and kwargs["fill_special"]:
            # in a round-trip test, more and more cruft folders will accumulate
            bad_args("cull_special=False may cause fill_special=True to write empty non-special cruft folders")
        if kwargs["cull_attr"] and kwargs["fill_ids"]:
            # in a round-trip test, ids will keep getting deleted and reassigned
            bad_args("cull_attr=True may undo some/all of the effects of fill_ids=True")
        if kwargs["cull_attr"] and kwargs["fill_timestamps"]:
            # in a round-trip test, timestamps will keep getting deleted and reassigned
            bad_args("cull_attr=True may undo some/all of the effects of fill_timestamps=True")
        return ok[0]
