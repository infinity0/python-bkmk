from .base import *

import json

def from_ast(node):
    node_type = node["type"]
    id = node.get("id", "")
    date_added = node.get("date_added", None)
    name = node.get("name", "")
    icon = node.get("icon", "")
    date_modified = node.get("date_modified", None)
    if node_type == "folder":
        children = list(map(from_ast, node["children"]))
        special = SpecialFolder[node["special"]] if "special" in node else None
        return Folder(id, date_added, name, icon, date_modified, children, special)
    elif node_type == "bookmark":
        url = node["url"]
        url_date_modified = node.get("url_date_modified", None)
        url_date_visited = node.get("url_date_visited", None)
        return Bookmark(id, date_added, name, icon, date_modified, url, url_date_modified, url_date_visited)
    elif node_type == "separator":
        return Separator(id, date_added)
    else:
        raise ValueError("unrecognised node type: %s" % node_type)

def to_ast(node):
    if isinstance(node, Separator):
        return _d({
            "type": "separator",
            "id": _oe(node.id),
            "date_added": _on(node.date_added),
        })
    elif isinstance(node, Bookmark):
        return _d({
            "type": "bookmark",
            "id": _oe(node.id),
            "date_added": _on(node.date_added),
            "name": node.name,
            "icon": _oe(node.icon),
            "date_modified": _on(node.date_modified),
            "url": node.url,
            "url_date_modified": _on(node.url_date_modified),
            "url_date_visited": _on(node.url_date_visited),
        })
    elif isinstance(node, Folder):
        return _d({
            "type": "folder",
            "id": _oe(node.id),
            "date_added": _on(node.date_added),
            "name": node.name,
            "icon": _oe(node.icon),
            "date_modified": _on(node.date_modified),
            "children": list(map(to_ast, node.children)),
            "special": _o(node.special.name if node.special else None, None),
        })
    else:
        assert False

def read(fp_in):
    return from_ast(json.load(fp_in))

def write(root, fp_out, _cull_attr, _cull_special):
    json.dump(to_ast(root), fp_out, indent=2)

def _roundtrip_acceptable_diff(*args):
    # bkmk-json should support everything, no diff is acceptable
    return False
