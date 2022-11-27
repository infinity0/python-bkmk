# bkmk

`bkmk` is a Python library and command-line utility to convert between
different bookmarks formats. It has been tested thoroughly on the following
formats, and supports conversion between any of them:

- XBEL - a standardised and precisely-defined XML-based format
- Netscape HTML - an imprecisely-defined ad-hoc external interchange format
  supported by most browsers including Firefox and Chrome, as well as being
  used internally by Firefox and Mozilla-based browsers
- Chrome JSON - an undocumented format, used internally by Chrome
- `bkmk` JSON - our own format, which expresses a superset of all the features
  of all the above formats. The format is extremely simple and will remain
  stable across many versions of this tool, and files written in it can easily
  be manipulated using common ecosystem tools such as `jq(1)`. For a detailed
  specification, see [below](#bkmk-json-format-spec).

Install via pip:

~~~~
$ pip3 install -U bkmk
~~~~

All the functionality of the CLI is mirrored in the API; see `bkmk --help` or
`pydoc3 bkmk` for details.

## CLI examples

Convert to Netscape HTML format, which can be imported into most browsers:

~~~~
$ bkmk <input-file> backup.html
~~~~

Directly override Chrome's internal bookmarks JSON. (Do this only when Chrome is closed.)

~~~~
$ bkmk --fill-special --cull-special -t chrome-json <input-file> ~/.config/chrome/Default/Bookmarks
~~~~

Retrieve a remote XBEL backup, convert it into `bkmk` JSON, make sure all elements have IDs, then process it further with `jq`.

~~~~
$ curl https://backupserver/bk.xbel | bkmk --fill-ids -f xbel -t bkmk-json | jq <some-complex-script> > <output-file>
~~~~

## API examples

```python
from bkmk import Bookmarks, FORMAT_EXTS

input_filenames = "a.xbel b.xbel".split()
output_filestem = "combined"
output_exts = ".json .html".split()

# combine several bookmark files into one
bk = Bookmarks.new()
for fn in input_filenames:
    with open(fn) as fp:
        bm = Bookmarks.read(fp, "xbel")
        bm.root.name = fn
        bm.prefix_ids(fn.replace(".xbel", "-"))
    bk.root.children.append(bm.root)
# fill in special top-level folders that browsers sometimes expect/require when importing
bk.fill_special()
# fill in timestamps for completeness
bk.fill_timestamps()

# output in several different formats
for o in output_exts:
    with open("%s%s" % (output_filestem, o), "w") as fp:
        bk.write(fp, FORMAT_EXTS[o][0], cull_special=True)
```

## bkmk JSON format spec

The JSON format mirrors our AST type, which is exposed in the public API in the
top-level `bkmk` module, re-exported from `bkmk.base`.

**Meta-documentation**. In the below specification,

* `unix_micros` refers to a JSON integer that represents microseconds since the
  Unix epoch, ignoring leap seconds, and can be negative.
* `string` refers to a *non-empty* JSON string. Attributes that are empty JSON
  strings are effectively omitted.

Required attributes are in **bold**, all other attributes are optional.

**Specification**.

Every object supports the following attributes:

* **`type`**: string, possible values `separator`, `bookmark`, `folder`,
  indicates which further attributes the object may have as defined below.
* `id`: string, must be unique under the root object, for use as a unique
  reference by reading tools.
* `date_added`: unix_micros, when this object was added into the AST.

`bookmark`, `folder` additionally support the following attributes:

* `name`: string, title or short description of this folder or bookmark.
* `icon`: string, [Data URL](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs)
  of the icon for this folder or bookmark.
* `date_modified`: unix_micros, when this object's attributes were last
  modified, excluding remote-mirroring attributes such as `url_date_modified`.

`bookmark` additionally supports the following attributes:

* **`url`**: string, URL target of this bookmark.
* `url_date_modified`: unix_micros, when the URL target was last modified on the remote side.
* `url_date_visited`: unix_micros, when the URL target was last visited (retrieved) by the local side.

`folder` additionally supports the following attributes:

* **`children`**: list[object], contents of this folder.
* `special`: string, possible values `TOOLBAR`, `OTHER_UNFILED`, `SAVED_TABS`,
  indicates a special status of the folder. On conversion, this is mapped to
  the corresponding special values of the target format, and treated specially
  by the target browser.

For interoperability with other formats, we recommend that:

* the root object should have `"type": "folder"` and no `special` attribute.
* folders with `special` attributes should not be placed inside each other.
  For maximum interoperability they should be immediate children of the root
  folder - some formats require this, others don't.
