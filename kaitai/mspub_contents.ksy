meta:
  id: mspub_contents
  title: Microsoft Publisher 95 / 97 / 98 — Contents stream
  endian: le
  license: MPL-2.0
  xref:
    justsolve: Macintosh_Publisher
    wikidata: Q391865
doc: |
    Declarative grammar for the `Contents` stream of a Microsoft Publisher
    95 / 97 / 98 document, derived from the specification at
    https://github.com/alosslessdev/mspub-file-format

    The outer container is a standard OLE2 / CFB v3 compound file; use any CFB
    reader to obtain the `Contents` stream (and, in Publisher 98, the
    `Quill/QuillSub/CONTENTS` stream). This grammar starts at the first byte of
    `Contents`.

    Layout: 0x22-byte header, then the text section
    `[text_section_offset, directory_offset)`, then at `directory_offset` the
    chunk directory, then the chunks themselves. Chunk sizes are not stored: a
    chunk ends where the next one starts.

    Every field name is traceable to a chapter of the specification; the
    chapter is named in the doc string of each type.
seq:
    - id: magic
      type: u2
      doc: |
        0xACE8 in every shipped document; 0xACE7 is the legacy form (§02).
      valid:
        any-of: [0xACE8, 0xACE7]
    - id: version_byte
      type: u1
      doc: 0x22 for the 95/97/98 family, 0x2C for Publisher 2000+ (§02).
    - id: reserved_zero
      type: u1
    - id: format_version
      type: u2
      doc: 300 for this family; 200 and 710 are legacy forms (§02).
    - id: writer_stamp
      type: u2
      doc: Writing environment stamp, 0x0004 normally, 0x3303 in eight templates (§02 §2.3).
    - id: declared_length
      type: u4
      doc: Equals the length of this stream (§02).
    - id: header_tag
      type: u2
      doc: Writer-generation tag — 125 (95), 136 (97), 616 (98), 704 (legacy) (§02 §2.2.1).
    - id: document_chunk_id
      type: u2
    - id: page_index3_id
      type: u2
    - id: text_section_offset
      type: u4
      doc: Start of the text store (§13 §13.14).
    - id: directory_offset
      type: u4
      doc: Also the end of the text section (§03).
    - id: constant_34
      type: u4
      doc: 34 in every document; the size of the header the loader reads (§02).
instances:
    directory:
      pos: directory_offset
      type: directory
      doc: Chunk directory (§03).
    text_section:
      pos: text_section_offset
      size: directory_offset - text_section_offset
      type: text_store
      doc: Publisher 95/97 text store; empty in Publisher 98 (§13 §13.14).
types:
  directory:
    doc: |
      `u16 count`, `u16 idHighWaterMark`, then count 10-byte records, then ten
      zero bytes, then the first chunk (§03).
    seq:
      - id: count
        type: u2
      - id: id_high_water_mark
        type: u2
        doc: Equal to max(record.id) in every measured document.
      - id: records
        type: record
        repeat: expr
        repeat-expr: count
    types:
      record:
        seq:
          - id: id
            type: u2
          - id: parent_id
            type: u2
            doc: 0x00FE or 0x00FF on the document record.
          - id: offset
            type: u4
            doc: Absolute offset inside Contents.
          - id: flags
            type: u2
            doc: 13-value domain 0x1040|bits; bit meanings not established (§03 §3.6.3).
  text_store:
    doc: Publisher 95/97 text store (§13 §13.14). Present in every version; in
      Publisher 98 the character array is empty and text lives in Quill.
    seq:
      - id: magic_and_header_size
        type: u4
        doc: 0x002EF0DE — low word magic, high word = 46-byte header size.
      - id: format_version_echo
        type: u2
        doc: 0x012C (300).
      - id: constant_512
        type: u2
      - id: zero
        type: u2
      - id: directory_offset_echo
        type: u4
      - id: text_base
        type: u4
        doc: Start of the character array; equals store offset + 46.
      - id: text_end
        type: u4
      - id: zero2
        type: u4
      - id: zero3
        type: u4
      - id: story_pointers
        type: u4
        repeat: expr
        repeat-expr: 4
        doc: Up to four pointers; exactly three are non-zero in 95/97.
  chunk:
    doc: |
      One directory chunk. The payload is interpreted by its type marker
      (§06, §08, §09, §15).

      A chunk does not store its own length: it ends where the next directory
      record's `offset` begins, and the last chunk ends at `declared_length`.
      Kaitai Struct cannot size an array element from the *next* element, so the
      host builds the array by instantiating this type with the computed length:

          for i, rec in enumerate(directory.records):
              end = directory.records[i + 1].offset if i + 1 < directory.count else declared_length
              chunk = MspubContents.Chunk.from_bytes(contents[rec.offset:end], len=end - rec.offset)
    params:
      - id: len
        type: u4
        doc: Total chunk length, including the 2-byte type marker.
    seq:
      - id: type
        type: u2
      - id: body
        type:
          switch-on: type
          cases:
            '0x0015': document_record
            '0x0014': page
            '0x0041': page
            '0x000f': group
            '0x0021': image_data
            '0x0047': palette
            '0x0022': object_reference
            '0x0000': shape
            '0x0001': shape
            '0x0002': shape
            '0x0003': shape
            '0x0004': shape
            '0x0005': shape
            '0x0006': shape
            '0x0007': shape
            '0x0008': shape
            _: opaque
  document_record:
    doc: DOCUMENT chunk (§04). Page geometry is in EMU (914400 per inch).
    seq:
      - id: descriptor_a
        type: u1
      - id: descriptor_b
        type: u1
      - id: print_setup_id
        type: u2
      - id: paper_block_id
        type: u2
      - id: first_page_id
        type: u2
      - id: unknown_0a
        type: u2
      - id: padding
        type: u1
        repeat: expr
        repeat-expr: 6
      - id: coordinate_system
        type: u2
        doc: 0 in ordinary documents; other values unestablished (§17 §17.4).
      - id: width_emu
        type: u4
      - id: height_emu
        type: u4
  page:
    doc: |
      PAGE slot (§05). Publisher 98 shifts the record by +4 and writes
      descriptor 0x1E; the layout is selected by that byte.
    seq:
      - id: descriptor_a
        type: u1
      - id: descriptor_b
        type: u1
      - id: rest
        type:
          switch-on: descriptor_a
          cases:
            '0x1e': page98
            _: page95
  page95:
    doc: PAGE record, Publisher 95/97 layout (§05).
    seq:
      - id: settings_chunk_id
        type: u2
      - id: mode
        type: u2
        doc: 0 in the shipped documents.
      - id: padding
        type: u1
        repeat: expr
        repeat-expr: 0x10
      - id: kind
        type: u2
      - id: child_count
        type: u2
      - id: child_count_dup
        type: u2
      - id: element_size
        type: u2
      - id: zero1
        type: u2
      - id: zero2
        type: u2
      - id: children
        type: u2
        repeat: expr
        repeat-expr: child_count
      - id: tail
        size-eos: true
  page98:
    doc: PAGE record, Publisher 98 layout (§05 §5.3) — +4 shift, counts at +0x1E.
    seq:
      - id: settings_chunk_id
        type: u2
      - id: mode
        type: u2
      - id: padding
        type: u1
        repeat: expr
        repeat-expr: 0x14
      - id: kind
        type: u2
      - id: child_count
        type: u2
      - id: child_count_dup
        type: u2
      - id: element_size
        type: u2
      - id: zero1
        type: u2
      - id: zero2
        type: u2
      - id: children
        type: u2
        repeat: expr
        repeat-expr: child_count
      - id: tail
        size-eos: true
  shape:
    doc: Shape record (§06). Rotation is 1/10 degree, counter-clockwise, mod 3600.
    seq:
      - id: descriptor_a
        type: u1
      - id: descriptor_b
        type: u1
      - id: rotation_raw
        type: u2
      - id: left
        type: s4
      - id: top
        type: s4
      - id: right
        type: s4
      - id: bottom
        type: s4
      - id: tail
        size-eos: true
  group:
    doc: GROUP chunk (§07) — geometry plus a counted child id list; the child
      list moves +8 bytes in Publisher 98.
    seq:
      - id: descriptor_a
        type: u1
      - id: descriptor_b
        type: u1
      - id: rotation_raw
        type: u2
      - id: left
        type: s4
      - id: top
        type: s4
      - id: right
        type: s4
      - id: bottom
        type: s4
      - id: rest
        type:
          switch-on: descriptor_a
          cases:
            '0x20': group98
            _: group95
  group95:
    seq:
      - id: flags
        type: u2
      - id: child_count
        type: u2
      - id: child_count_dup
        type: u2
      - id: element_size
        type: u2
      - id: zero1
        type: u2
      - id: zero2
        type: u2
      - id: children
        type: u2
        repeat: expr
        repeat-expr: child_count
      - id: tail
        size-eos: true
  group98:
    seq:
      - id: flags
        type: u2
      - id: padding
        type: u1
        repeat: expr
        repeat-expr: 6
      - id: child_count
        type: u2
      - id: child_count_dup
        type: u2
      - id: element_size
        type: u2
      - id: zero1
        type: u2
      - id: zero2
        type: u2
      - id: children
        type: u2
        repeat: expr
        repeat-expr: child_count
      - id: tail
        size-eos: true
  image_data:
    doc: IMAGE_DATA (§08) — a WMF payload with a length prefix.
    seq:
      - id: record_class
        type: u2
        doc: 0x0800 in every document.
      - id: payload_length
        type: u4
        doc: Equals chunk size - 8 in 527/527 instances.
      - id: payload
        size: payload_length
  palette:
    doc: PALETTE (§09) — 192-byte record, Publisher 98 only.
    seq:
      - id: stamp
        type: u2
        doc: 0x9696.
      - id: flags
        type: u1
        repeat: expr
        repeat-expr: 0x0A
      - id: scheme_name_raw
        size: 0x82
        doc: NUL-terminated UTF-16LE scheme name, zero-padded.
      - id: padding
        type: u1
        repeat: expr
        repeat-expr: 16
      - id: color_refs
        type: u4
        repeat: expr
        repeat-expr: 8
        doc: Colour references; decode with §09 §9.1.
  object_reference:
    doc: Embedded-object reference (§15 §15.8) — "MO" plus the storage ordinal.
    seq:
      - id: tag
        type: u2
        doc: 0x0800.
      - id: payload_length
        type: u4
        doc: 10.
      - id: marker
        type: u2
        doc: ASCII "MO".
      - id: object_ordinal
        type: u2
        doc: Selects Objects/Object N.
      - id: padding
        type: u1
        repeat: expr
        repeat-expr: 3
      - id: flag
        type: u1
        doc: 0x00 or 0x80; per-reference state (§15 §15.8.1).
      - id: zero
        type: u2
  opaque:
    doc: A chunk whose layout the specification does not define; preserve verbatim.
    seq:
      - id: data
        size-eos: true
