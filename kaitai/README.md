# Declarative grammar (Kaitai Struct)

`mspub_contents.ksy` is a machine-readable form of the specification: the
container-independent structures of the `Contents` stream (chapters 02-09, 15).
It is documentation *and* working code — the Kaitai compiler generates parsers
for C++, Java, Python, Ruby, Go, Rust, C#, JavaScript, Swift, PHP, Lua, Nim and
Perl.

## Scope

| Covered | Not covered (why) |
|---|---|
| header fields, chunk directory and record layout | the CFB container itself — use any OLE2 reader to obtain `Contents` |
| the 95/97 text store header and story pointers | the `Quill/QuillSub/CONTENTS` stream — a separate stream, its framing is described in chapter 13 |
| chunk bodies for DOCUMENT, PAGE (95/97 and 98 layouts), GROUP (both), shape geometry, IMAGE_DATA, PALETTE, object reference | chunk types the specification leaves opaque — they surface as `opaque` byte blobs, which is the correct behaviour for a reader |

## The one construct Kaitai cannot express

A chunk does not store its own length: it ends where the next directory record's
`offset` begins (the last chunk ends at `declared_length`). Kaitai Struct has no
way to size an array element from the *next* element, so `chunk` takes its length
as a parameter and the host builds the array:

```python
from kaitaistruct import KaitaiStream
from io import BytesIO
import mspub_contents as K

doc = K.MspubContents.from_bytes(contents_stream)
recs = doc.directory.records
for i, rec in enumerate(recs):
    end = recs[i + 1].offset if i + 1 < len(recs) else doc.declared_length
    chunk = K.MspubContents.Chunk(
        end - rec.offset, KaitaiStream(BytesIO(contents_stream[rec.offset:end])))
    print(hex(chunk.type), chunk.body)
```

That is the whole contract; everything else is declarative.

## Compiling

```bash
curl -LO https://github.com/kaitai-io/kaitai_struct_compiler/releases/download/0.11/kaitai-struct-compiler-0.11.zip
unzip kaitai-struct-compiler-0.11.zip
kaitai-struct-compiler-0.11/bin/kaitai-struct-compiler \
    --target python -d out mspub_contents.ksy
```

## Verification performed

The grammar was compiled with `kaitai-struct-compiler` 0.11 and run against six
shipped documents spanning all three versions (Publisher 95, 97, 98 — including
two 98 `.JSP` publications). For every file the grammar reproduced:

* the complete chunk inventory by type marker,
* every PAGE record's `kind` and child id list in z-order (95/97 and 98 layouts),
* the IMAGE_DATA payload lengths and the PALETTE colour reference array.

The expected values for a wider set of samples are in [`../tests/`](../tests/).
