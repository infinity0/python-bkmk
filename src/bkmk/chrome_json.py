from .base import *

import json

SUPPORTED_VERSION = 1
WINDOWS_UNIX_DIFF = 11644473600000000

def from_fmt_time(cs):
    if cs is None: return None
    return int(cs) - WINDOWS_UNIX_DIFF

def to_fmt_time(ue):
    if ue is None: return None
    return str(ue + WINDOWS_UNIX_DIFF)

# chrome bookmarks have a bit of a customised root structure, deal with it here

SPECIAL_FOLDERS_BY_NAME = {
    "bookmark_bar": SpecialFolder.TOOLBAR,
    "other": SpecialFolder.OTHER_UNFILED,
    "tabs": SpecialFolder.SAVED_TABS,
    "synced": None,
}

SPECIAL_FOLDERS_BY_ENUM = {v: k for (k, v) in SPECIAL_FOLDERS_BY_NAME.items()}

def from_ast(node, special=None):
    node_type = node["type"]
    id = node.get("id", "")
    date_added = from_fmt_time(node.get("date_added", None))
    name = node.get("name", "")
    icon = "" # TODO: not supported by format
    date_modified = from_fmt_time(node.get("date_modified", None))
    if node_type == "folder":
        children = list(map(from_ast, node["children"]))
        return Folder(id, date_added, name, icon, date_modified, children, special)
    elif node_type == "url":
        url = node["url"]
        url_date_modified = None # TODO: not supported by format
        url_date_visited = from_fmt_time(node.get("date_last_used", None))
        if any(url.startswith(f) for f in FAKE_SEPARATOR_URLS):
            return Separator(id, date_added)
        else:
            return Bookmark(id, date_added, name, icon, date_modified, url, url_date_modified, url_date_visited)
    else:
        raise ValueError("unrecognised node type: %s" % node_type)

def to_ast(node, cull_special):
    if isinstance(node, Separator):
        return _d({
            "type": "url",
            "id": _oe(node.id),
            "date_added": _on(to_fmt_time(node.date_added)),
            "name": "|",
            "icon": FAKE_SEPARATOR_ICON,
            "date_modified": _on(to_fmt_time(node.date_added)),
            "url": FAKE_SEPARATOR_URLS[0],
            "date_last_used": _on(to_fmt_time(node.date_added)),
        })
    elif isinstance(node, Bookmark):
        return _d({
            "type": "url",
            "id": _oe(node.id),
            "date_added": _on(to_fmt_time(node.date_added)),
            "name": node.name,
            "icon": _oe(node.icon),
            "date_modified": _on(to_fmt_time(node.date_modified)),
            "url": node.url,
            # TODO: not supported by format
            #"": _on(to_fmt_time(node.url_date_modified)),
            "date_last_used": _on(to_fmt_time(node.url_date_visited)),
        })
    elif isinstance(node, Folder):
        return _d({
            "type": "folder",
            "id": _oe(node.id),
            "date_added": _on(to_fmt_time(node.date_added)),
            "name": node.name,
            "icon": _oe(node.icon),
            "date_modified": _on(to_fmt_time(node.date_modified)),
            "children": [
                to_ast(c, cull_special) for c in node.children
                if _keep_child(cull_special, SPECIAL_FOLDERS_BY_ENUM.keys(), c)
            ],
        })
    else:
        assert False

def read(fp_in):
    p = json.load(fp_in)
    if "version" not in p:
        ver = SUPPORTED_VERSION
        log("warn: no version found, assume we support it")
    else:
        ver = p["version"]
        if ver != SUPPORTED_VERSION:
            raise ValueError("unsupported chrome-json version: %s" % ver)

    w = from_ast(p["roots"][SPECIAL_FOLDERS_BY_ENUM[None]], None)
    assert isinstance(w, Folder)
    special_children = []
    for k, v in p["roots"].items():
        if k == SPECIAL_FOLDERS_BY_ENUM[None]: continue
        root = from_ast(v, SPECIAL_FOLDERS_BY_NAME[k])
        assert isinstance(root, Folder)
        special_children.append(root)
    w.children = special_children + w.children
    return w

def write(root, fp_out, cull_special, _cull_attr):
    w = {
        "version": SUPPORTED_VERSION,
        "roots": {},
    }
    is_special = lambda c: isinstance(c, Folder) and c.special is not None
    special_children = [c for c in root.children if is_special(c)]
    for r in special_children:
        w["roots"][SPECIAL_FOLDERS_BY_ENUM[r.special]] = to_ast(r, cull_special)
    # writing to root is pretty hacky, oh well
    orig_children = root.children
    root.children = [c for c in root.children if not is_special(c)]
    w["roots"][SPECIAL_FOLDERS_BY_ENUM[None]] = to_ast(root, cull_special)
    json.dump(w, fp_out, indent=2)
    root.children = orig_children

def _roundtrip_sortkey(node):
    if isinstance(node, Folder) and node.special:
        return node.special.value
    else:
        return 0

def _roundtrip_acceptable_diff(cull_attr, depth, ty, attr, v_a, v_b):
    if attr == "icon":
        if v_a != "" and v_b == "":
            # attribute unsupported by format
            return True
    elif attr == "url_date_modified":
        # attribute unsupported by format
        # don't bother checking the value as fill_timestamps sets any value
        return True
    elif attr == "special":
        if v_a is not None and v_a not in SPECIAL_FOLDERS_BY_ENUM.keys() and v_b is None:
            # only some special folders are supported
            return True
    return False
