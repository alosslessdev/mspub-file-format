# Chunk type markers by version

Instance counts per corpus. Absence is a statement about the shipped corpora, NOT a rule:
the P98 corpus is two files, so "not present in P98" means "no P98 sample exists", and any
"98-only" marker rests on n=2.

| Marker | libmspub name | P95 | P97 | P97D | P98 | corpus observation |
|---|---|---|---|---|---|---|
| — | *files indexed* | 128 | 106 | 248 | 2 | |
| 0x0000 | SHAPE | 1092 | 1211 | 2735 | 0 | no P98 sample |
| 0x0001 | SHAPE1 | 218 | 157 | 360 | 2 | present in all four corpora |
| 0x0002 | IMAGE | 248 | 196 | 561 | 2 | present in all four corpora |
| 0x0003 | SHAPE3 | 617 | 479 | 1520 | 2 | present in all four corpora |
| 0x0004 | LINE | 696 | 665 | 1413 | 2 | present in all four corpora |
| 0x0005 | RECT | 1110 | 1062 | 2302 | 2 | present in all four corpora |
| 0x0006 | SHAPE_OBJECT | 1322 | 867 | 1850 | 2 | present in all four corpora |
| 0x0007 | SHAPE7 | 266 | 190 | 692 | 2 | present in all four corpora |
| 0x0008 | SHAPE8 | 0 | 0 | 0 | 2 | P98 sample only |
| 0x0009 | ? | 0 | 0 | 0 | 2 | P98 sample only |
| 0x000a | ? | 0 | 0 | 0 | 2 | P98 sample only |
| 0x000b | ? | 0 | 0 | 0 | 2 | P98 sample only |
| 0x000f | GROUP | 827 | 705 | 1394 | 0 | no P98 sample |
| 0x0014 | PAGE | 712 | 593 | 1423 | 12 | present in all four corpora |
| 0x0015 | DOCUMENT | 128 | 106 | 248 | 2 | present in all four corpora |
| 0x0016 | SHAPE16 | 128 | 106 | 248 | 0 | no P98 sample |
| 0x001a | ? | 128 | 106 | 248 | 0 | no P98 sample |
| 0x001c | ? | 128 | 106 | 248 | 0 | no P98 sample |
| 0x001e | ? | 128 | 106 | 248 | 2 | present in all four corpora |
| 0x001f | ? | 128 | 106 | 248 | 2 | present in all four corpora |
| 0x0021 | IMAGE_DATA | 129 | 88 | 310 | 0 | no P98 sample |
| 0x0022 | ? | 489 | 373 | 1272 | 0 | no P98 sample |
| 0x0023 | ? | 128 | 106 | 248 | 2 | present in all four corpora |
| 0x0026 | ? | 128 | 106 | 248 | 0 | no P98 sample |
| 0x0027 | ? | 14 | 4 | 4 | 0 | no P98 sample |
| 0x0028 | ? | 128 | 106 | 248 | 2 | present in all four corpora |
| 0x0029 | ? | 128 | 106 | 248 | 2 | present in all four corpora |
| 0x002a | ? | 128 | 106 | 248 | 0 | no P98 sample |
| 0x002b | ? | 30 | 14 | 27 | 0 | no P98 sample |
| 0x002c | ? | 137 | 115 | 275 | 2 | present in all four corpora |
| 0x002d | ? | 128 | 106 | 248 | 0 | no P98 sample |
| 0x002e | ? | 128 | 106 | 248 | 0 | no P98 sample |
| 0x002f | ? | 0 | 4 | 8 | 0 | no P98 sample |
| 0x0031 | LOGO | 384 | 413 | 991 | 6 | present in all four corpora |
| 0x0032 | ? | 384 | 318 | 744 | 6 | present in all four corpora |
| 0x0034 | ? | 68 | 72 | 191 | 0 | no P98 sample |
| 0x0035 | ? | 74 | 66 | 166 | 0 | no P98 sample |
| 0x0037 | ? | 16 | 36 | 126 | 2 | present in all four corpora |
| 0x0038 | ? | 15 | 18 | 94 | 0 | no P98 sample |
| 0x0039 | ? | 128 | 106 | 248 | 2 | present in all four corpora |
| 0x003a | ? | 0 | 95 | 247 | 0 | no P98 sample |
| 0x003b | ? | 0 | 4 | 8 | 0 | no P98 sample |
| 0x003f | ? | 0 | 13 | 22 | 0 | no P98 sample |
| 0x0040 | ? | 0 | 0 | 0 | 2 | P98 sample only |
| 0x0041 | ? | 0 | 0 | 0 | 2 | P98 sample only |
| 0x0043 | ? | 0 | 0 | 0 | 2 | P98 sample only |
| 0x0045 | ? | 0 | 0 | 0 | 2 | P98 sample only |
| 0x0047 | PALETTE | 0 | 0 | 0 | 2 | P98 sample only |
| 0x004c | ? | 0 | 0 | 0 | 2 | P98 sample only |
| 0x0052 | ? | 0 | 0 | 0 | 2 | P98 sample only |
