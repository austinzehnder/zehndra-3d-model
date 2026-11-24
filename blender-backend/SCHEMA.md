# Dimensions-table schema (v1)

The input to `generate_build.py`. One JSON file per job: the rooms,
walls, openings, and furniture in metres, plus materials and look.
This is the "numbers first" step of the blueprint method: the table
is the single source of truth, and the generator turns it into
`build.py` with no guessing. If a number does not add up, the
generator stops and says so; it never invents a dimension.

All lengths are metres, z up, y north, x east. The origin (0, 0) is
the south-west corner of the lot.

## Top level

| Field | Type | Notes |
| --- | --- | --- |
| `version` | int | Must be 1. |
| `project` | object | `name` (string), `address` (string). Used for the script header and the output folder name. |
| `units` | string | Must be `"m"`. |
| `lot` | rect | `{x0, y0, x1, y1}`. Every volume must sit inside it. |
| `volumes` | array | One per building mass (house, addition, ADU). See below. |
| `rooms` | array | One per room, inside a volume. See below. |
| `partitions` | array | Interior walls. Optional (empty array is fine). |
| `openings` | array | Doors and windows on exterior walls. |
| `furniture` | array | One per piece, inside a room. |
| `materials` | object | Role to finish name. See "Materials". |
| `look` | object | `preset`: `modern`, `farmhouse`, or `craftsman`. |
| `totals` | object | Optional. `total`, `existing`, `new` sq ft, checked against the geometry within 5%. |

A rect is `{x0, y0, x1, y1}` with `x1 > x0` and `y1 > y0`.

## Volumes

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique. Referenced by rooms, openings, partitions. |
| `kind` | string | `house`, `addition`, or `adu`. |
| `label` | string | Human label, e.g. "Existing house". |
| `x0, y0, x1, y1` | numbers | Plan rect, metres. |
| `floors` | int | 1 or more. |
| `floor_height` | number | Floor-to-floor height, e.g. 2.9. |
| `wall_thickness` | number | e.g. 0.15. |
| `roof` | object | `type`: `gable` or `flat`; `pitch_deg` (gable only); `overhang` in metres. |
| `shared_walls` | array | Wall names the volume does NOT build, because the neighbour already builds them: any of `south`, `north`, `east`, `west`. Used where an addition touches the house. |

Volumes must not overlap in plan (positive-area overlap is an
error). Touching edges are fine. Walls sit centred on the volume
rect edges.

Wall names for a volume rect: `south` is the y0 edge (runs along x
from x0), `north` is the y1 edge, `west` is the x0 edge (runs along
y from y0), `east` is the x1 edge.

## Rooms

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique. Referenced by furniture. |
| `volume` | string | Volume id. |
| `floor` | int | 0 is the ground floor. Must be below the volume's floor count. |
| `name` | string | e.g. "Kitchen". |
| `kind` | string | `kitchen`, `bedroom`, `bathroom`, `living`, `entry`, `hall`, `room`. Drives the room light wattage. |
| `x0, y0, x1, y1` | numbers | Rect inside the volume rect. |
| `floor_finish` | string | Optional. `boards` (default) or `none` (open well, no floor boards). |

Rooms on one floor of a volume should cover most of the floor:
their areas must sum to within 15% of the volume's floor area.
The gap is walls and unassigned space.

## Partitions

Interior walls, one per entry:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique. |
| `volume` | string | Volume id. |
| `floor` | int | Floor the partition stands on. |
| `axis` | string | `x`: the wall is a plane at x = `at`, running along y. `y`: a plane at y = `at`, running along x. |
| `at` | number | The plane position. |
| `from`, `to` | numbers | The wall runs from `from` to `to` along the other axis. |
| `thickness` | number | Optional, default 0.1. |
| `openings` | array | Door gaps in this partition. Each: `{at, width, z0, z1, kind}` with `at` measured along the partition from `from`, and `z0`/`z1` heights above the floor. `kind` is `door` (only doors are supported in partitions). |

## Openings (exterior walls)

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique. |
| `volume` | string | Volume id. |
| `floor` | int | Floor the opening is on. |
| `wall` | string | `south`, `north`, `east`, `west`. |
| `at` | number | Distance along the wall from its start corner (south/north start at x0, west/east start at y0). |
| `width` | number | Opening width along the wall. |
| `z0`, `z1` | numbers | Sill and head heights above the floor. Doors have `z0` 0. |
| `kind` | string | `door` or `window`. |

Openings on one wall and floor must not overlap, and must fit
inside the wall length. `z1` must not exceed the floor height.

## Furniture

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique. |
| `room` | string | Room id. |
| `kind` | string | See "Furniture kinds". |
| `x`, `y` | numbers | Centre of the piece, metres. |
| `w`, `d` | numbers | Footprint: width and depth. |
| `h` | number | Optional height override. |
| `rot` | int | Optional, 0 or 90. 90 turns the piece to run along y. Default 0. |

The footprint (after rotation) must sit inside the room rect.

### Furniture kinds

`bed`, `nightstand`, `dresser`, `sofa`, `table`, `chair`,
`kitchen_run`, `island`, `fridge`, `tub`, `vanity`, `toilet`,
`counter`, `shelf`. Each is built from boxes, cylinders, and tubes
as separate parts (a bed is a frame, mattress, two pillows, and a
headboard; a sofa is a base, back, two arms, and two cushions).

## Materials

`materials` maps a role to a finish name. Roles: `exterior`,
`roof`, `floor`, `wall`, `countertop`, `cabinet`, `fixture`,
`trim`, `door`, `accent`. Known finishes: `warm_white`,
`charcoal`, `oak`, `quartz`, `white`, `nickel`, `walnut`, `sage`,
`navy`, `terracotta`, `concrete`, `glass`. The `look.preset`
fills in any missing role with a preset default; a table may
omit roles it does not care about.

## Validation (the generator enforces all of these)

- Required fields present; `version` 1; `units` `"m"`.
- Ids unique per list; references (volume, room) exist.
- Volumes inside the lot; no positive-area overlap between volumes.
- Rooms inside their volume; floor in range.
- Room areas per floor within 15% of the volume floor area; total
  room area within 5% of `totals.total` when totals are given.
- Openings fit their wall, do not overlap each other, and sit
  below the floor height.
- Partitions inside their volume; partition openings fit and do
  not overlap.
- Furniture footprints inside their rooms.
- Material finish names known; `look.preset` known.

A failure prints every error to stderr and exits non-zero with no
output file. A held job is the system working, not stuck.

## Known limitations (v1)

- No stairs: the upper floor has no stair opening and no stair
  geometry. A two-story job still renders both floors; the stair
  is a manual refinement.
- Shared wall segments (addition against house) use the exterior
  material on the shared face.
- Floor boards run in aligned pieces, not staggered.
- No Poly Haven assets in the generated baseline: materials are
  procedural and trees are built from cylinders and spheres. Real
  trees and plants are a GPU-machine refinement.
- The sky is a flat background colour plus a sun, not the
  courtyard's gradient sky. The stills-against-references loop
  is where the look gets fixed.
