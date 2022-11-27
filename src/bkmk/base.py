from dataclasses import dataclass
from enum import Enum

FAKE_SEPARATOR_URLS = [
    "about:bookmark-separator",
    "https://separator.mayastudios.com/",
    "https://separator.floccus.org/",
]

FAKE_SEPARATOR_ICON = "data:image/svg+xml;charset=utf-8;base64,\
PHN2ZyB2ZXJzaW9uPSIxLjEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgdmll\
d0JveD0iMCAwIDE2IDE2Ij48c3R5bGU+bGluZSB7IHN0cm9rZTogI2E3YTA5ZjsgfTwvc3R5bGU+\
PGxpbmUgeDE9IjgiIHgyPSI4IiB5MT0iMCIgeTI9IjE2IiBmaWxsPSJub25lIi8+PC9zdmc+"

def _debug_eq_attr(self, other, accept, depth, attrs):
    r = []
    for attr in attrs.split():
        self_attr = getattr(self, attr)
        other_attr = getattr(other, attr)
        if self_attr != other_attr and not accept(depth, type(self), attr, self_attr, other_attr):
            log("err:", attr, "different:", str(self_attr), "vs", str(other_attr))
            r.append(False)
    return all(r)

@dataclass
class Base:
    id: str
    """When this entry was added."""
    date_added: int | None # unix epoch, micros

    def map_mut(self, mut):
        mut(self)

    def map_mut_share(self, mut, share):
        mut(self, share)

    def _debug_eq(self, other, accept, xchildren, depth):
        r = []
        r.append(_debug_eq_attr(self, other, accept, depth, "id date_added"))
        return all(r)

@dataclass
class Separator(Base):
    def _debug_eq(self, other, accept, xchildren, depth):
        if type(self) != type(other):
            log("err: type mismatch:", type(self).__name__, "vs", type(other).__name__)
            return False
        r = []
        r.append(super()._debug_eq(other, accept, xchildren, depth))
        return all(r)

@dataclass
class UserEntry(Base):
    name: str
    icon: str
    """When this entry was modified."""
    date_modified: int | None # unix epoch, micros

    def _debug_eq(self, other, accept, xchildren, depth):
        r = []
        r.append(super()._debug_eq(other, accept, xchildren, depth))
        r.append(_debug_eq_attr(self, other, accept, depth, "name icon date_modified"))
        return all(r)

@dataclass
class Bookmark(UserEntry):
    url: str
    """When the URL was modified."""
    url_date_modified: int | None # unix epoch, micros
    """When the URL was last visited."""
    url_date_visited: int | None # unix epoch, micros

    def _debug_eq(self, other, accept, xchildren, depth):
        if type(self) != type(other):
            log("err: type mismatch:", type(self).__name__, "vs", type(other).__name__)
            return False
        r = []
        r.append(super()._debug_eq(other, accept, xchildren, depth))
        r.append(_debug_eq_attr(self, other, accept, depth, "url url_date_modified url_date_visited"))
        return all(r)

SpecialFolder = Enum("SpecialFolder", "TOOLBAR OTHER_UNFILED SAVED_TABS".split())
FOLDER_DEFAULT_NAMES = {
    None: "Bookmarks",
    SpecialFolder.TOOLBAR: "Bookmarks Toolbar",
    SpecialFolder.OTHER_UNFILED: "Other Bookmarks",
    SpecialFolder.SAVED_TABS: "Tabs collection",
}

def _keep_child(cull_special, supported, node):
    if isinstance(node, Folder):
        # cull empty special folders if they are unsupported
        return not (cull_special and node.special is not None and not node.children and node.special not in supported)
    else:
        return True

@dataclass
class Folder(UserEntry):
    children: list['BookmarksTy']
    special: None | SpecialFolder

    def map_mut(self, mut):
        """Apply a mutation to every item in the folder and its subfolders."""
        mut(self)
        for c in self.children:
            c.map_mut(mut)

    def map_mut_share(self, mut, share):
        """Apply a mutation with access to shared state, to every item in the folder and its subfolders.

        The share should be a container, not a single value. To share a single
        variable, put it inside a list of length 1.
        """
        mut(self, share)
        for c in self.children:
            c.map_mut_share(mut, share)

    def _debug_eq(self, other, accept, xchildren, depth=0):
        if type(self) != type(other):
            log("err: type mismatch:", type(self).__name__, "vs", type(other).__name__)
            return False
        r = []
        r.append(super()._debug_eq(other, accept, xchildren, depth))
        r.append(_debug_eq_attr(self, other, accept, depth, "special"))
        for a, b in zip(xchildren(self.children, depth), xchildren(other.children, depth)):
            r.append(a._debug_eq(b, accept, xchildren, depth+1))
        return all(r)

    @classmethod
    def new(cls):
        return cls("", None, "", "", None, [], None)

BookmarksTy = Separator | Bookmark | Folder

"""
Utils for having optional keys in dictionary literals

Usage is like

_d({
  "key": _o(value, remove_if_equal_to_this_default)
})
"""
def _d(d):
    return {k: v for (k, v) in d.items() if v != _REMOVE_ME}

def _o(v, d):
    return _REMOVE_ME if v == d else v

def _oe(v):
    return _o(v, "")

def _on(v):
    return _o(v, None)

_REMOVE_ME = object()

def log(*args):
    import sys
    print("bkmk:", *args, file=sys.stderr)

__all__ = [
    "FAKE_SEPARATOR_URLS", "FAKE_SEPARATOR_ICON", "FOLDER_DEFAULT_NAMES",
    "Separator", "Bookmark", "SpecialFolder", "Folder", "_keep_child",
    "_d", "_o", "_oe", "_on",
    "log",
]
