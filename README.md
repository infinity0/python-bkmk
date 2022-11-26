# bkmk

`bkmk` is a Python library and command-line utility to convert between
different bookmarks formats.

It has been tested thoroughly on the following formats, and supports conversion
between any of them:

- XBEL - a standardised and precisely-defined XML-based format
- Netscape HTML - an imprecisely-defined ad-hoc external interchange format
  supported by most browsers including Firefox and Chrome, as well as being
  used internally by Firefox and Mozilla-based browsers
- Chrome JSON - an undocumented format, used internally by Chrome

We also have our own "`bkmk` JSON" format which expresses a superset of all the
features of all the above formats. The format is extremely simple and will
remain stable across many versions of this tool. Files written in this format
can easily be manipulated using common ecosystem tools such as `jq(1)`.

The Python library also offers a simple API:

```python
from bkmk import *

input_filenames = "a.xbel b.xbel".split()
output_filestem = "combined"
output_exts = ".json .html".split()

# combine several bookmark files into one
bk = Bookmarks.new()
for fn in input_filenames:
    with open(fn) as fp:
        bm = Bookmarks.read(fp, "xbel").root
        bm.name = fn
    bk.root.children.append(bm)
# fill in special top-level folders that browsers sometimes expect/require when importing
bk.fill_special()
# fill in timestamps for completeness
bk.fill_timestamps()

# output in several different formats
for o in output_exts:
    with open("%s%s" % (output_filestem, o), "w") as fp:
        bk.write(fp, FORMAT_EXTS[o][0], cull_special=True)
```

All the functionality of the CLI is mirrored in the API; see `--help` or
`pydoc` for details.
