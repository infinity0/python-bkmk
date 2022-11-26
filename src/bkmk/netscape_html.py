from .base import *

import sys

from html import escape
from html.parser import HTMLParser

DOCTYPE = "NETSCAPE-Bookmark-file-1"

def from_fmt_time(u):
    if u is None: return None
    return int(u) * 1000000

def to_fmt_time(ue):
    if ue is None: return None
    return str(int(ue / 1000000.0))

SPECIAL_FOLDERS_BY_NAME = {
    "personal_toolbar_folder": SpecialFolder.TOOLBAR,
    "unfiled_bookmarks_folder": SpecialFolder.OTHER_UNFILED,
}

SPECIAL_FOLDERS_BY_ENUM = {v: k for (k, v) in SPECIAL_FOLDERS_BY_NAME.items()}

def from_special_folder(attrs):
    for a, b in SPECIAL_FOLDERS_BY_NAME.items():
        if attrs.get(a, "") == "true":
            return b
    return None

def to_special_folder(folder):
    attr = SPECIAL_FOLDERS_BY_ENUM.get(folder.special, None)
    return {attr: "true"} if attr is not None else {}

# we write our own custom parser because these files don't have </dt> tags
# which really confuses beautifulsoup and makes it generate incorrect stuff
# like <dt><dt><dt></dt></dt></dt>
class NetscapeHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.started = False
        self.stack = []
        self.result = None

    def current(self):
        return self.stack[-1] if self.stack else None

    def append_child(self, elem):
        cur = self.current()
        assert isinstance(cur, Folder)
        cur.children.append(elem)
        self.stack.append(elem)

    def pop_any_child(self):
        cur = self.current()
        if not isinstance(cur, Folder):
            self.stack.pop()

    def handle_starttag(self, tag, attrs):
        if not self.started:
            raise ValueError("did not see expected DOCTYPE")
        attrs = dict(attrs)
        id = attrs.get("id", "")
        date_added = from_fmt_time(attrs.get("add_date", None))

        if tag in ("h1", "h3"):
            icon = attrs.get("icon", "")
            date_modified = from_fmt_time(attrs.get("last_modified", None))
            special = from_special_folder(attrs) if tag == "h3" else None
            folder = Folder(id, date_added, "", icon, date_modified, [], special)
            if tag == "h1":
                self.stack.append(folder)
            else:
                self.append_child(folder)
        elif tag == "a":
            icon = attrs.get("icon", "")
            date_modified = from_fmt_time(attrs.get("last_modified", None))
            url = attrs["href"]
            if any(url.startswith(f) for f in FAKE_SEPARATOR_URLS):
                # floccus uses fake separators even though netscape-html supports real ones
                b = Separator(id, date_added)
            else:
                url_date_modified = None # TODO: not supported by format
                url_date_visited = from_fmt_time(attrs.get("last_visit", None))
                b = Bookmark(id, date_added, "", icon, date_modified, url, url_date_modified, url_date_visited)
            self.append_child(b)
        elif tag == "hr":
            self.pop_any_child()
            self.append_child(Separator(id, date_added))
        elif tag == "dt":
            # there are no closing <dt> tags. this effectively closes off the previous Bookmark
            # it is a no-op if the current item is a Folder
            self.pop_any_child()
        elif tag == "dl":
            if not isinstance(self.current(), Folder):
                # hack around floccus and possibly other tools not writing <h1>
                assert not self.stack
                self.stack.append(Folder.new())

    def handle_endtag(self, tag):
        if tag == "dl":
            if not isinstance(self.current(), Folder):
                self.stack.pop()
            assert isinstance(self.current(), Folder)
            n = self.stack.pop()
            if not self.stack:
                assert not self.result
                self.result = n

    def handle_comment(self, data):
        pass

    def handle_decl(self, data):
        if data == "DOCTYPE " + DOCTYPE:
            self.started = True

    def handle_data(self, data):
        cur = self.current()
        if not cur: return
        data = data.strip()
        if not data: return
        if isinstance(cur, Separator): return # floccus and other fake separators
        # sometimes the data is split into multiple chunks
        cur.name += data

def read(fp_in):
    parser = NetscapeHTMLParser()
    parser.feed(fp_in.read())
    result = parser.result
    if result is None:
        raise ValueError("failed to parse anything out of the file")
    return result

def expand_attrs(attrs):
    return "".join(' %s="%s"' % (k.upper(), escape(v, quote=True)) for k, v in attrs.items())

def write_node(node, fp_out, cull_special, cull_attr, depth=0):
    indent = "    " * depth
    if isinstance(node, Separator):
        attrs = _d({
            "id": _oe(node.id),
            "add_date": _on(to_fmt_time(node.date_added)),
        })
        if cull_attr:
            attrs.pop("id", None)
            attrs.pop("add_date", None)
        print("%s<HR%s>" % (indent, expand_attrs(attrs)), file=fp_out)
    elif isinstance(node, Bookmark):
        attrs = _d({
            "id": _oe(node.id),
            "add_date": _on(to_fmt_time(node.date_added)),
            "icon": _oe(node.icon),
            "last_modified": _on(to_fmt_time(node.date_modified)),
            "href": node.url,
            # TODO: not supported by format
            #"": _on(to_fmt_time(node.url_date_modified)),
            "last_visit": _on(to_fmt_time(node.url_date_visited)),
        })
        if cull_attr:
            attrs.pop("id", None)
        print("%s<DT><A%s>%s</A>" % (indent, expand_attrs(attrs), escape(node.name)), file=fp_out)
    elif isinstance(node, Folder):
        attrs = _d({
            "id": _oe(node.id),
            "add_date": _on(to_fmt_time(node.date_added)),
            "icon": _oe(node.icon),
            "last_modified": _on(to_fmt_time(node.date_modified)),
            **to_special_folder(node),
        })
        if cull_attr:
            attrs.pop("id", None)
            attrs.pop("icon", None)
        if depth == 0:
            if cull_attr:
                attrs = {}
            print("<TITLE>%s</TITLE>" % escape(node.name), file=fp_out)
            print("<H1%s>%s</H1>" % (expand_attrs(attrs), escape(node.name)), file=fp_out)
        else:
            print("%s<DT><H3%s>%s</H3>" % (indent, expand_attrs(attrs), escape(node.name)), file=fp_out)
        print("%s<DL><p>" % indent, file=fp_out)
        for c in node.children:
            if _keep_child(cull_special, SPECIAL_FOLDERS_BY_ENUM.keys(), c):
                write_node(c, fp_out, cull_special, cull_attr, depth+1)
        print("%s</DL><p>" % indent, file=fp_out)
    else:
        assert False

def write(root, fp_out, cull_special, cull_attr):
    print("<!DOCTYPE %s>" % DOCTYPE, file=fp_out)
    print('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">', file=fp_out)
    write_node(root, fp_out, cull_special, cull_attr, 0)

def _roundtrip_acceptable_diff(cull_attr, depth, ty, attr, v_a, v_b):
    if attr == "id":
        if cull_attr and v_a != "" and v_b == "":
            # nothing has ids under cull_atr
            return True
    elif attr == "date_added":
        if cull_attr and ty == Separator and v_a is not None and v_b is None:
            # separators don't have date_added under cull_attr
            return True
    elif attr == "url_date_modified":
        # attribute unsupported by format
        # don't bother checking the value as fill_timestamps sets any value
        return True
    elif attr == "special":
        if v_a is not None and v_a not in SPECIAL_FOLDERS_BY_ENUM.keys() and v_b is None:
            # only some special folders are supported
            return True
    # special netscape quirks
    if attr.startswith("date_") or attr.startswith("url_date_"):
        if v_a is not None and v_b is not None:
            # lack of precision in format
            return to_fmt_time(v_a) == to_fmt_time(v_b)
        if cull_attr and depth == 0 and ty == Folder and v_a is not None and v_b is None:
            # top-level folder can't have any attributes under cull_attr
            return True
    return False
