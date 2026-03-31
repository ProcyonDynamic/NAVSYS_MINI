# UCHM Reverse Engineering Ledger v1

## Status

**Current milestone:** successful manual patching of `.uchm` line objects confirmed.

Validated by successful JRC imports:

* Color patch ✅
* Width patch ✅
* Type patch ✅

---

## Canonical Base Fixture

Reference file: `L01_base.uchm`

Known base line style tuple:

```text
01 02 09 00
```

Meaning:

* `01` = solid
* `02` = width 2
* `09` = red
* `00` = reserved / pad

Known base tail:

```text
89 BB B3 4D
```

---

## Confirmed CSV ↔ UCHM Style Mapping

For line objects, `.uchm` uses the same JRC codes as CSV.

### Type

* `01` = solid
* `02` = dashed
* `03` = dotted

### Width

* `01` to `05` = increasing thickness

### Color

* `00` = white
* `01` = grey
* `02` = amber
* `03` = magenta
* `04` = blue
* `05` = cyan
* `06` = green
* `07` = yellow
* `08` = orange
* `09` = red

---

## Successful Patch Matrix

### P01 — Color Patch

Target: red → blue

Changed:

```text
payload: 02 09 00 60 -> 02 04 00 60
style : 01 02 09 00 -> 01 02 04 00
tail  : 89 BB B3 4D -> 98 F1 DE 00
```

Result:

* Imported successfully
* Blue line rendered

---

### P02 — Width Patch

Target: width 2 → width 5

Changed:

```text
style: 01 02 09 00 -> 01 05 09 00
tail : 89 BB B3 4D -> 0F AC D7 8C
```

Result:

* Imported successfully
* Thicker line rendered

---

### P03 — Type Patch

Target: solid → dotted

Changed:

```text
style: 01 02 09 00 -> 03 02 09 00
tail : 89 BB B3 4D -> D3 38 F4 C4
```

Result:

* Imported successfully
* Alternate line type rendered flawlessly

---

## Current Structural Model (Line Objects)

```text
[geometry / payload fields]
[payload-linked style byte(s)]
[type][width][color][00]
[tail checksum / derived field]
```

### High Confidence

* style tuple is authoritative
* tail field is required for import acceptance
* at least color also has payload-linked field(s)

### Medium Confidence

* tail field behaves like checksum / signature / derived integrity bytes

---

## Open Questions

1. Exact checksum algorithm for tail bytes
2. Full geometry block layout
3. Scale min / scale max bytes
4. North orientation bytes
5. Native symbol object schema
6. Text object schema
7. Multi-object record boundaries

---

## Next Recommended Experiments

1. Isolate checksum derivation
2. Patch scale min/max
3. Patch north orientation
4. Patch native symbol color
5. Patch text payload and position
