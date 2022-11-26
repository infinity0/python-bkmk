from .base import *

from datetime import datetime
import xml.etree.ElementTree as ET

"""https://xbel.sourceforge.net/language/versions/1.0/xbel-1.0.xhtml"""
XBEL_VERSION = "1.0"

def from_fmt_time(iso):
    if iso is None: return None
    import sys
    if not (sys.version_info.major >= 3 and sys.version_info.minor >= 11):
        log("warn: parsing ISO 8601 dates properly requires Python >= 3.11")
    return int(datetime.fromisoformat(iso).timestamp() * 1000000)

def to_fmt_time(ue):
    if ue is None: return None
    # utcfromtimestap/isoformat are buggy, we have to add Z ourselves
    iso = datetime.utcfromtimestamp(ue / 1000000.0).isoformat()
    return iso if iso.endswith("Z") else iso + "Z"

# we don't support aliases, nor likely ever will, as it's hard to fit into the other formats
SUPPORTED_TAGS = ["xbel", "folder", "bookmark", "separator"]

SPECIAL_FOLDERS_BY_NAME = {
    "toolbar": SpecialFolder.TOOLBAR,
}

SPECIAL_FOLDERS_BY_ENUM = {v: k for (k, v) in SPECIAL_FOLDERS_BY_NAME.items()}

def from_ast(node):
    node_type = node.tag
    attrib = node.attrib
    id = attrib.get("id", "")
    date_added = from_fmt_time(attrib.get("added", None))
    title = node.find("title")
    name = title.text if title is not None and title.text is not None else ""
    icon = attrib.get("icon", "")
    date_modified = from_fmt_time(None) # TODO: not supported by format
    if node_type == "folder" or node_type == "xbel":
        children = [from_ast(c) for c in node if c.tag in SUPPORTED_TAGS]
        special = SpecialFolder.TOOLBAR if node_type == "folder" and node.get("toolbar", "") == "yes" else None
        return Folder(id, date_added, name, icon, date_modified, children, special)
    elif node_type == "bookmark":
        url = attrib["href"]
        url_date_modified = from_fmt_time(attrib.get("modified", None))
        url_date_visited = from_fmt_time(attrib.get("visited", None))
        if any(url.startswith(f) for f in FAKE_SEPARATOR_URLS):
            # floccus uses fake separators even though xbel supports real ones
            return Separator(id, date_added)
        else:
            return Bookmark(id, date_added, name, icon, date_modified, url, url_date_modified, url_date_visited)
    elif node_type == "separator":
        return Separator(id, date_added)
    else:
        raise ValueError("unrecognised node type: %s" % node_type)

def to_ast(node, cull_special, cull_attr, depth=0):
    if isinstance(node, Separator):
        w = ET.Element("separator")
        w.attrib = _d({
            "id": _oe(node.id),
            "added": _on(to_fmt_time(node.date_added)),
        })
        if cull_attr:
            w.attrib.pop("id", None)
            w.attrib.pop("added", None)
        return w
    elif isinstance(node, Bookmark):
        w = ET.Element("bookmark")
        t = ET.SubElement(w, "title")
        t.text = node.name
        w.attrib = _d({
            "id": _oe(node.id),
            "added": _on(to_fmt_time(node.date_added)),
            "icon": _oe(node.icon),
            # TODO: not supported by format
            #"": _on(to_fmt_time(node.date_modified)),
            "href": node.url,
            "modified": _on(to_fmt_time(node.url_date_modified)),
            "visited": _on(to_fmt_time(node.url_date_visited)),
        })
        return w
    elif isinstance(node, Folder):
        w = ET.Element("xbel" if depth == 0 else "folder")
        t = ET.SubElement(w, "title")
        t.text = node.name
        w.attrib = _d({
            "id": _oe(node.id),
            "added": _on(to_fmt_time(node.date_added)),
            "icon": _oe(node.icon),
            # TODO: not supported by format
            #"": _on(to_fmt_time(node.date_modified)),
            # TODO: other values not supported by format
            "toolbar": _o("yes" if node.special == SpecialFolder.TOOLBAR else None, None),
        })
        if depth == 0:
            w.attrib["version"] = XBEL_VERSION
        if cull_attr and depth == 0:
            w.attrib.pop("icon", None)
        w.extend([
            to_ast(c, cull_special, cull_attr, depth+1) for c in node.children
            if _keep_child(cull_special, SPECIAL_FOLDERS_BY_ENUM.keys(), c)
        ])
        return w
    else:
        assert False

def read(fp_in):
    x = ET.parse(fp_in)
    ver = x.getroot().attrib.get("version", None)
    if ver != XBEL_VERSION:
        raise ValueError("unsupported xbel version: %s" % ver)
    root = from_ast(x.getroot())
    assert isinstance(root, Folder)
    return root

def write(root, fp_out, cull_special, cull_attr):
    w = to_ast(root, cull_special, cull_attr)
    ET.indent(w)
    # we opened the file in string mode, so write in string mode
    ET.ElementTree(w).write(fp_out, encoding="unicode", xml_declaration=True, short_empty_elements=False)

def _roundtrip_acceptable_diff(cull_attr, depth, ty, attr, v_a, v_b):
    if attr == "id":
        if cull_attr and ty == Separator and v_a != "" and v_b == "":
            # separators don't have ids under cull_attr
            return True
    elif attr == "date_added":
        if cull_attr and ty == Separator and v_a is not None and v_b is None:
            # separators don't have date_added under cull_attr
            return True
    elif attr == "date_modified":
        # attribute unsupported by format
        # don't bother checking the value as fill_timestamps sets any value
        return True
    elif attr == "special":
        if v_a is not None and v_a not in SPECIAL_FOLDERS_BY_ENUM.keys() and v_b is None:
            # only some special folders are supported
            return True
    return False
