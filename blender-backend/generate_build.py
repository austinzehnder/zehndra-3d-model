#!/usr/bin/env python3
"""Deterministic generator: dimensions table (JSON) -> Blender build.py.

Takes a dimensions table (see SCHEMA.md) and emits a Blender Python
script that builds the house part by part, using the same method as
the blueprint skill (Nyxera0x/blueprint): every part its own object,
tagged with its build stage (K.STAGE), so a film can fly them in.

Deterministic: the same table always produces the same script
(byte-identical output; no randomness, no timestamps, no dict-order
dependence beyond the table's own order). It is usable two ways:

  1. Unattended build: the job runner calls this instead of asking
     Claude to hand-write build.py (AUTOMATION.md, "Unattended build").
  2. Manual workflow: Claude Code calls this instead of hand-writing
     build.py, then refines the result.

Stdlib only. No Blender needed to run this script; the emitted
build.py needs Blender 4.2+ and the blueprint kit (bkit) on the GPU
machine. No Poly Haven assets are required by the emitted script:
materials are procedural and trees are built from cylinders and
spheres.

Usage:
  python3 generate_build.py <table.json> [-o <build.py>] [--slug NAME]

Exit codes: 0 on success; 2 on a validation failure (errors on
stderr, no output file); 1 on a usage error.
"""

import json
import math
import os
import sys

VERSION = 1
SQFT_PER_M2 = 10.7639
STAGES = ["foundation", "frame", "floors", "walls", "roof", "interior", "site", "lights"]

# ---------------------------------------------------------------- finishes
# Finish name -> linear RGB. Roles in the table map to these names;
# the look preset fills in roles the table omits.
FINISHES = {
    "warm_white": (0.88, 0.86, 0.80),
    "charcoal": (0.05, 0.05, 0.06),
    "oak": (0.55, 0.38, 0.22),
    "quartz": (0.90, 0.90, 0.88),
    "white": (0.93, 0.93, 0.92),
    "nickel": (0.75, 0.75, 0.78),
    "walnut": (0.25, 0.16, 0.10),
    "sage": (0.55, 0.60, 0.50),
    "navy": (0.10, 0.14, 0.22),
    "terracotta": (0.72, 0.36, 0.22),
    "concrete": (0.62, 0.62, 0.60),
    "glass": (0.95, 0.97, 0.97),
}

# Preset -> default finish per role. Table entries override these.
PRESETS = {
    "modern": {
        "exterior": "warm_white", "roof": "charcoal", "floor": "oak",
        "wall": "warm_white", "countertop": "quartz", "cabinet": "white",
        "fixture": "nickel", "trim": "white", "door": "walnut", "accent": "sage",
    },
    "farmhouse": {
        "exterior": "warm_white", "roof": "charcoal", "floor": "oak",
        "wall": "warm_white", "countertop": "quartz", "cabinet": "white",
        "fixture": "nickel", "trim": "white", "door": "walnut", "accent": "terracotta",
    },
    "craftsman": {
        "exterior": "sage", "roof": "charcoal", "floor": "walnut",
        "wall": "warm_white", "countertop": "quartz", "cabinet": "walnut",
        "fixture": "nickel", "trim": "white", "door": "walnut", "accent": "navy",
    },
}

ROLES = ["exterior", "roof", "floor", "wall", "countertop", "cabinet",
         "fixture", "trim", "door", "accent"]

ROOM_WATTS = {"kitchen": 190, "bathroom": 70, "bedroom": 120,
              "living": 170, "entry": 110, "hall": 90, "room": 110}

FURNITURE_KINDS = {"bed", "nightstand", "dresser", "sofa", "table",
                   "chair", "kitchen_run", "island", "fridge", "tub",
                   "vanity", "toilet", "counter", "shelf"}


class TableError(Exception):
    """A dimensions-table problem. The job is held, not guessed."""


# ---------------------------------------------------------------- validation
def _req(obj, field, where):
    if field not in obj:
        raise TableError(f"{where}: missing required field '{field}'")
    return obj[field]


def _num(obj, field, where):
    v = _req(obj, field, where)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TableError(f"{where}: '{field}' must be a number, got {v!r}")
    return float(v)


def _rect(obj, where):
    x0 = _num(obj, "x0", where)
    y0 = _num(obj, "y0", where)
    x1 = _num(obj, "x1", where)
    y1 = _num(obj, "y1", where)
    if not (x1 > x0 and y1 > y0):
        raise TableError(f"{where}: rect must have x1 > x0 and y1 > y0, got ({x0}, {y0}, {x1}, {y1})")
    return (x0, y0, x1, y1)


def _unique(ids, where):
    seen = set()
    for i in ids:
        if i in seen:
            raise TableError(f"{where}: duplicate id '{i}'")
        seen.add(i)


def validate(table):
    """Validate the dimensions table. Raises TableError on any problem.
    Returns a dict of lookups the generator uses."""
    if not isinstance(table, dict):
        raise TableError("table must be a JSON object")
    if table.get("version") != VERSION:
        raise TableError(f"version must be {VERSION}, got {table.get('version')!r}")
    if table.get("units") != "m":
        raise TableError(f"units must be 'm', got {table.get('units')!r}")
    project = _req(table, "project", "table")
    _req(project, "name", "project")
    lot = _rect(_req(table, "lot", "table"), "lot")

    volumes = _req(table, "volumes", "table")
    if not isinstance(volumes, list) or not volumes:
        raise TableError("volumes must be a non-empty array")
    _unique([v.get("id") for v in volumes], "volumes")
    vols = {}
    for v in volumes:
        where = f"volume '{v.get('id')}'"
        _req(v, "id", where)
        kind = _req(v, "kind", where)
        if kind not in ("house", "addition", "adu"):
            raise TableError(f"{where}: kind must be house/addition/adu, got {kind!r}")
        rect = _rect(v, where)
        if not (rect[0] >= lot[0] and rect[1] >= lot[1] and rect[2] <= lot[2] and rect[3] <= lot[3]):
            raise TableError(f"{where}: volume rect {rect} sits outside the lot {lot}")
        floors = _req(v, "floors", where)
        if isinstance(floors, bool) or not isinstance(floors, int) or floors < 1:
            raise TableError(f"{where}: floors must be a positive integer, got {floors!r}")
        _num(v, "floor_height", where)
        if v["floor_height"] <= 0:
            raise TableError(f"{where}: floor_height must be positive")
        _num(v, "wall_thickness", where)
        if v["wall_thickness"] <= 0:
            raise TableError(f"{where}: wall_thickness must be positive")
        roof = _req(v, "roof", where)
        if roof.get("type") not in ("gable", "flat"):
            raise TableError(f"{where}: roof.type must be gable/flat, got {roof.get('type')!r}")
        if roof["type"] == "gable":
            _num(roof, "pitch_deg", where + " roof")
            if not (5 <= roof["pitch_deg"] <= 60):
                raise TableError(f"{where}: roof.pitch_deg must be 5..60, got {roof['pitch_deg']}")
        _num(roof, "overhang", where + " roof")
        for w in v.get("shared_walls", []):
            if w not in ("south", "north", "east", "west"):
                raise TableError(f"{where}: bad shared wall {w!r}")
        vols[v["id"]] = v
    # no positive-area overlap between volumes
    for i, a in enumerate(volumes):
        for b in volumes[i + 1:]:
            ox = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
            oy = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
            if ox > 0 and oy > 0:
                raise TableError(
                    f"volumes '{a['id']}' and '{b['id']}' overlap by {ox:.2f} x {oy:.2f} m; "
                    "volumes may touch but not overlap")

    rooms = _req(table, "rooms", "table")
    if not isinstance(rooms, list) or not rooms:
        raise TableError("rooms must be a non-empty array")
    _unique([r.get("id") for r in rooms], "rooms")
    rms = {}
    for r in rooms:
        where = f"room '{r.get('id')}'"
        _req(r, "id", where)
        vol = vols.get(_req(r, "volume", where))
        if vol is None:
            raise TableError(f"{where}: unknown volume {r['volume']!r}")
        floor = _req(r, "floor", where)
        if isinstance(floor, bool) or not isinstance(floor, int) or not (0 <= floor < vol["floors"]):
            raise TableError(f"{where}: floor must be 0..{vol['floors'] - 1}, got {floor!r}")
        if r.get("kind", "room") not in ROOM_WATTS:
            raise TableError(f"{where}: unknown kind {r.get('kind')!r}")
        rect = _rect(r, where)
        if not (rect[0] >= vol["x0"] and rect[1] >= vol["y0"] and rect[2] <= vol["x1"] and rect[3] <= vol["y1"]):
            raise TableError(f"{where}: room rect {rect} sits outside volume '{vol['id']}'")
        if r.get("floor_finish", "boards") not in ("boards", "none"):
            raise TableError(f"{where}: floor_finish must be boards/none, got {r.get('floor_finish')!r}")
        rms[r["id"]] = r
    # room areas per floor must cover most of the volume floor
    for v in volumes:
        for f in range(v["floors"]):
            floor_area = (v["x1"] - v["x0"]) * (v["y1"] - v["y0"])
            covered = sum((r["x1"] - r["x0"]) * (r["y1"] - r["y0"])
                          for r in rooms if r["volume"] == v["id"] and r["floor"] == f)
            if covered < 0.85 * floor_area:
                raise TableError(
                    f"volume '{v['id']}' floor {f}: rooms cover {covered:.1f} of {floor_area:.1f} m2 "
                    "(rooms must cover at least 85% of the floor; the gap is walls and unassigned space)")
    totals = table.get("totals")
    if totals:
        total_m2 = sum((r["x1"] - r["x0"]) * (r["y1"] - r["y0"]) for r in rooms)
        total_sqft = total_m2 * SQFT_PER_M2
        for key, stated in (("total", total_sqft),):
            if key in totals and abs(totals[key] - stated) > 0.05 * totals[key]:
                raise TableError(
                    f"totals.{key}: rooms add up to {stated:.0f} sq ft but the table states "
                    f"{totals[key]:.0f} sq ft (tolerance 5%)")
        for key, vol_ids in (("existing", [v["id"] for v in volumes if v["kind"] == "house"]),
                             ("new", [v["id"] for v in volumes if v["kind"] in ("addition", "adu")])):
            if key in totals:
                area = sum((v["x1"] - v["x0"]) * (v["y1"] - v["y0"]) * v["floors"] for v in volumes
                           if v["id"] in vol_ids) * SQFT_PER_M2
                if abs(totals[key] - area) > 0.05 * totals[key]:
                    raise TableError(
                        f"totals.{key}: volumes add up to {area:.0f} sq ft but the table states "
                        f"{totals[key]:.0f} sq ft (tolerance 5%)")

    partitions = table.get("partitions", [])
    _unique([p.get("id") for p in partitions], "partitions")
    for p in partitions:
        where = f"partition '{p.get('id')}'"
        _req(p, "id", where)
        vol = vols.get(_req(p, "volume", where))
        if vol is None:
            raise TableError(f"{where}: unknown volume {p['volume']!r}")
        floor = _req(p, "floor", where)
        if isinstance(floor, bool) or not isinstance(floor, int) or not (0 <= floor < vol["floors"]):
            raise TableError(f"{where}: floor must be 0..{vol['floors'] - 1}, got {floor!r}")
        axis = _req(p, "axis", where)
        if axis not in ("x", "y"):
            raise TableError(f"{where}: axis must be x/y, got {axis!r}")
        at = _num(p, "at", where)
        frm = _num(p, "from", where)
        to = _num(p, "to", where)
        if not to > frm:
            raise TableError(f"{where}: 'to' must be greater than 'from'")
        if axis == "x":
            if not (vol["x0"] <= at <= vol["x1"] and frm >= vol["y0"] and to <= vol["y1"]):
                raise TableError(f"{where}: partition sits outside volume '{vol['id']}'")
        else:
            if not (vol["y0"] <= at <= vol["y1"] and frm >= vol["x0"] and to <= vol["x1"]):
                raise TableError(f"{where}: partition sits outside volume '{vol['id']}'")
        _check_openings(p.get("openings", []), to - frm, vol["floor_height"], where)

    openings = _req(table, "openings", "table")
    _unique([o.get("id") for o in openings], "openings")
    by_wall = {}
    for o in openings:
        where = f"opening '{o.get('id')}'"
        _req(o, "id", where)
        vol = vols.get(_req(o, "volume", where))
        if vol is None:
            raise TableError(f"{where}: unknown volume {o['volume']!r}")
        floor = _req(o, "floor", where)
        if isinstance(floor, bool) or not isinstance(floor, int) or not (0 <= floor < vol["floors"]):
            raise TableError(f"{where}: floor must be 0..{vol['floors'] - 1}, got {floor!r}")
        wall = _req(o, "wall", where)
        if wall not in ("south", "north", "east", "west"):
            raise TableError(f"{where}: wall must be south/north/east/west, got {wall!r}")
        if vol["id"] and wall in vol.get("shared_walls", []):
            raise TableError(f"{where}: wall '{wall}' of volume '{vol['id']}' is shared and not built")
        length = (vol["x1"] - vol["x0"]) if wall in ("south", "north") else (vol["y1"] - vol["y0"])
        at = _num(o, "at", where)
        width = _num(o, "width", where)
        z0 = _num(o, "z0", where)
        z1 = _num(o, "z1", where)
        if width <= 0 or at < 0 or at + width > length + 1e-9:
            raise TableError(f"{where}: opening at {at} width {width} does not fit wall length {length}")
        if not (0 <= z0 < z1 <= vol["floor_height"]):
            raise TableError(f"{where}: opening z0..z1 ({z0}..{z1}) must sit inside the floor height "
                             f"{vol['floor_height']}")
        if o.get("kind") not in ("door", "window"):
            raise TableError(f"{where}: kind must be door/window, got {o.get('kind')!r}")
        key = (vol["id"], floor, wall)
        by_wall.setdefault(key, []).append((at, width, o["id"]))
    for key, lst in by_wall.items():
        lst.sort()
        for (a0, w0, id0), (a1, w1, id1) in zip(lst, lst[1:]):
            if a1 < a0 + w0 - 1e-9:
                raise TableError(f"openings '{id0}' and '{id1}' overlap on wall {key}")

    furniture = table.get("furniture", [])
    _unique([f.get("id") for f in furniture], "furniture")
    for f in furniture:
        where = f"furniture '{f.get('id')}'"
        _req(f, "id", where)
        room = rms.get(_req(f, "room", where))
        if room is None:
            raise TableError(f"{where}: unknown room {f['room']!r}")
        if f.get("kind") not in FURNITURE_KINDS:
            raise TableError(f"{where}: unknown kind {f.get('kind')!r}")
        x = _num(f, "x", where)
        y = _num(f, "y", where)
        w = _num(f, "w", where)
        d = _num(f, "d", where)
        if w <= 0 or d <= 0:
            raise TableError(f"{where}: w and d must be positive")
        rot = f.get("rot", 0)
        if rot not in (0, 90):
            raise TableError(f"{where}: rot must be 0 or 90, got {rot!r}")
        fw, fd = (d, w) if rot == 90 else (w, d)
        if not (room["x0"] <= x - fw / 2 and x + fw / 2 <= room["x1"] and
                room["y0"] <= y - fd / 2 and y + fd / 2 <= room["y1"]):
            raise TableError(f"{where}: footprint {fw:.2f} x {fd:.2f} at ({x}, {y}) sits outside "
                             f"room '{room['id']}'")

    look = table.get("look", {})
    if look.get("preset", "modern") not in PRESETS:
        raise TableError(f"look.preset must be one of {sorted(PRESETS)}, got {look.get('preset')!r}")
    materials = table.get("materials", {})
    for role, name in materials.items():
        if role not in ROLES:
            raise TableError(f"materials: unknown role {role!r}")
        if name not in FINISHES:
            raise TableError(f"materials.{role}: unknown finish {name!r}")

    return {"volumes": vols, "rooms": rms, "lot": lot}


def _check_openings(openings, length, height, where):
    """Openings along one wall/partition: fit, no overlap, inside the height."""
    if not isinstance(openings, list):
        raise TableError(f"{where}: openings must be an array")
    lst = []
    for o in openings:
        at = _num(o, "at", where)
        width = _num(o, "width", where)
        z0 = _num(o, "z0", where)
        z1 = _num(o, "z1", where)
        if width <= 0 or at < 0 or at + width > length + 1e-9:
            raise TableError(f"{where}: opening at {at} width {width} does not fit length {length}")
        if not (0 <= z0 < z1 <= height):
            raise TableError(f"{where}: opening z0..z1 ({z0}..{z1}) must sit inside height {height}")
        if o.get("kind") not in ("door",):
            raise TableError(f"{where}: partition openings must be doors, got {o.get('kind')!r}")
        lst.append((at, width))
    lst.sort()
    for (a0, w0), (a1, _w1) in zip(lst, lst[1:]):
        if a1 < a0 + w0 - 1e-9:
            raise TableError(f"{where}: partition openings overlap")


# ---------------------------------------------------------------- emitter
def _f(x):
    """Deterministic float formatting for emitted code."""
    return f"{float(x):.4g}"


def _c(rgb):
    return "(%s, %s, %s)" % (_f(rgb[0]), _f(rgb[1]), _f(rgb[2]))


class Emit:
    """Collects the lines of the generated build.py and counts parts."""

    def __init__(self):
        self.lines = []
        self.counts = {s: 0 for s in STAGES}
        self.stage = "misc"

    def add(self, text=""):
        self.lines.append(text)

    def set_stage(self, s):
        self.stage = s
        self.add(f'stage("{s}")')

    def part(self, code, n=1):
        """One emitted part-creating line (or loop); n is how many parts it makes."""
        self.add(code)
        self.counts[self.stage] += n

    def text(self):
        return "\n".join(self.lines) + "\n"


def resolve_materials(table):
    """Preset defaults overridden by the table's materials."""
    preset = table.get("look", {}).get("preset", "modern")
    resolved = dict(PRESETS[preset])
    resolved.update(table.get("materials", {}))
    return {role: FINISHES[resolved[role]] for role in ROLES}


# ---------------------------------------------------------------- wall math
def wall_segments(length, z0, z1, openings):
    """Split a wall of `length` into solid boxes around its openings.

    openings: sorted list of (along, width, oz0, oz1), heights relative
    to the wall base z0. Returns a list of (a0, a1, oz0, oz1) boxes,
    each spanning `along` a0..a1 and height oz0..oz1 (absolute within
    the wall, i.e. z0/z1 are the wall's own base/top)."""
    segs = []
    cur = 0.0
    for (a, w, o0, o1) in sorted(openings):
        if a > cur + 1e-9:
            segs.append((cur, a, z0, z1))
        if o0 > z0 + 1e-9:
            segs.append((a, a + w, z0, o0))
        if o1 < z1 - 1e-9:
            segs.append((a, a + w, o1, z1))
        cur = a + w
    if cur < length - 1e-9:
        segs.append((cur, length, z0, z1))
    return segs


def wall_box_coords(vol, wall, a0, a1, zb, oz0, oz1):
    """Convert a wall segment (along a0..a1, height oz0..oz1 above the
    floor base zb) into absolute box coordinates (x0, x1, y0, y1, z0, z1)."""
    t = vol["wall_thickness"]
    x0, y0, x1, y1 = vol["x0"], vol["y0"], vol["x1"], vol["y1"]
    if wall == "south":
        return (x0 + a0, x0 + a1, y0 - t / 2, y0 + t / 2, zb + oz0, zb + oz1)
    if wall == "north":
        return (x0 + a0, x0 + a1, y1 - t / 2, y1 + t / 2, zb + oz0, zb + oz1)
    if wall == "west":
        return (x0 - t / 2, x0 + t / 2, y0 + a0, y0 + a1, zb + oz0, zb + oz1)
    return (x1 - t / 2, x1 + t / 2, y0 + a0, y0 + a1, zb + oz0, zb + oz1)


def wall_length(vol, wall):
    return (vol["x1"] - vol["x0"]) if wall in ("south", "north") else (vol["y1"] - vol["y0"])


# ---------------------------------------------------------------- stages
def emit_foundation(em, table):
    em.set_stage("foundation")
    for vol in table["volumes"]:
        vid = vol["id"]
        em.add(f"# foundation: {vol.get('label', vid)}")
        em.part(f'box("slab_{vid}", {_f(vol["x0"] - 0.1)}, {_f(vol["x1"] + 0.1)}, '
                f'{_f(vol["y0"] - 0.1)}, {_f(vol["y1"] + 0.1)}, -0.15, 0.0, M["concrete"], bevel=0)')
        for k, (cx, cy) in enumerate(((vol["x0"] + 0.3, vol["y0"] + 0.3), (vol["x1"] - 0.3, vol["y0"] + 0.3),
                                      (vol["x0"] + 0.3, vol["y1"] - 0.3), (vol["x1"] - 0.3, vol["y1"] - 0.3))):
            em.part(f'cyl("footing_{vid}_{k}", {_f(cx)}, {_f(cy)}, 0.22, -0.6, 0.0, M["concrete"], verts=20, bevel=0)')


def emit_frame(em, table):
    em.set_stage("frame")
    for vol in table["volumes"]:
        vid = vol["id"]
        t = vol["wall_thickness"]
        for f in range(vol["floors"]):
            zb = f * vol["floor_height"]
            zt = zb + vol["floor_height"]
            em.add(f"# frame: {vid} floor {f}")
            for k, (cx, cy) in enumerate(((vol["x0"] + t / 2, vol["y0"] + t / 2), (vol["x1"] - t / 2, vol["y0"] + t / 2),
                                          (vol["x0"] + t / 2, vol["y1"] - t / 2), (vol["x1"] - t / 2, vol["y1"] - t / 2))):
                em.part(f'beam("post_{vid}_{f}_{k}", ({_f(cx)}, {_f(cy)}, {_f(zb)}), '
                        f'({_f(cx)}, {_f(cy)}, {_f(zt)}), 0.09, 0.09, M["frame"])')
            for wname, ax, ay, bx, by in (("s", vol["x0"], vol["y0"], vol["x1"], vol["y0"]),
                                         ("n", vol["x0"], vol["y1"], vol["x1"], vol["y1"]),
                                         ("w", vol["x0"], vol["y0"], vol["x0"], vol["y1"]),
                                         ("e", vol["x1"], vol["y0"], vol["x1"], vol["y1"])):
                em.part(f'beam("sill_{vid}_{f}_{wname}", ({_f(ax)}, {_f(ay)}, {_f(zb + 0.05)}), '
                        f'({_f(bx)}, {_f(by)}, {_f(zb + 0.05)}), 0.1, 0.1, M["frame"])')
                em.part(f'beam("plate_{vid}_{f}_{wname}", ({_f(ax)}, {_f(ay)}, {_f(zt - 0.05)}), '
                        f'({_f(bx)}, {_f(by)}, {_f(zt - 0.05)}), 0.1, 0.1, M["frame"])')


def emit_floors(em, table):
    em.set_stage("floors")
    for vol in table["volumes"]:
        vid = vol["id"]
        for f in range(1, vol["floors"]):
            zb = f * vol["floor_height"]
            em.part(f'box("subfloor_{vid}_{f}", {_f(vol["x0"])}, {_f(vol["x1"])}, '
                    f'{_f(vol["y0"])}, {_f(vol["y1"])}, {_f(zb - 0.06)}, {_f(zb)}, M["floor"], bevel=0)')
    for room in table["rooms"]:
        if room.get("floor_finish", "boards") != "boards":
            continue
        vol = next(v for v in table["volumes"] if v["id"] == room["volume"])
        zb = room["floor"] * vol["floor_height"]
        dx = room["x1"] - room["x0"]
        dy = room["y1"] - room["y0"]
        rid = room["id"]
        if dx >= dy:
            n_strips = max(1, round(dy / 0.15))
            n_pieces = max(1, round(dx / 2.4))
            sh = dy / n_strips
            pl = dx / n_pieces
            em.add(f"# floor boards: {rid} ({n_strips} strips x {n_pieces} pieces)")
            em.add(f"for _i in range({n_strips}):")
            em.add(f"    for _j in range({n_pieces}):")
            em.part(f'        box("floor_{rid}_b%d_%d" % (_i, _j), '
                    f'{_f(room["x0"])} + _j * {_f(pl)}, {_f(room["x0"])} + (_j + 1) * {_f(pl)}, '
                    f'{_f(room["y0"])} + _i * {_f(sh)}, {_f(room["y0"])} + (_i + 1) * {_f(sh)}, '
                    f'{_f(zb)}, {_f(zb + 0.02)}, M["floor"], bevel=0.001)',
                    n=n_strips * n_pieces)
        else:
            n_strips = max(1, round(dx / 0.15))
            n_pieces = max(1, round(dy / 2.4))
            sh = dx / n_strips
            pl = dy / n_pieces
            em.add(f"# floor boards: {rid} ({n_strips} strips x {n_pieces} pieces)")
            em.add(f"for _i in range({n_strips}):")
            em.add(f"    for _j in range({n_pieces}):")
            em.part(f'        box("floor_{rid}_b%d_%d" % (_i, _j), '
                    f'{_f(room["x0"])} + _i * {_f(sh)}, {_f(room["x0"])} + (_i + 1) * {_f(sh)}, '
                    f'{_f(room["y0"])} + _j * {_f(pl)}, {_f(room["y0"])} + (_j + 1) * {_f(pl)}, '
                    f'{_f(zb)}, {_f(zb + 0.02)}, M["floor"], bevel=0.001)',
                    n=n_strips * n_pieces)


def emit_opening_hardware(em, vol, floor_base, wall, opening):
    """Door slab + jambs, or window glass + frame + sill, in the hole
    the wall segments left. All coordinates absolute."""
    oid = opening["id"]
    t = vol["wall_thickness"]
    along = opening["at"]
    w = opening["width"]
    z0 = floor_base + opening["z0"]
    z1 = floor_base + opening["z1"]
    horizontal = wall in ("south", "north")
    if wall == "south":
        c0, c1, fixed = vol["x0"] + along, vol["x0"] + along + w, vol["y0"]
    elif wall == "north":
        c0, c1, fixed = vol["x0"] + along, vol["x0"] + along + w, vol["y1"]
    elif wall == "west":
        c0, c1, fixed = vol["y0"] + along, vol["y0"] + along + w, vol["x0"]
    else:
        c0, c1, fixed = vol["y0"] + along, vol["y0"] + along + w, vol["x1"]

    def sbox(name, a0, a1, b0, b1, zz0, zz1, mat, bevel=0.002):
        if horizontal:
            return (f'box("{name}", {_f(a0)}, {_f(a1)}, {_f(fixed + b0)}, {_f(fixed + b1)}, '
                    f'{_f(zz0)}, {_f(zz1)}, M["{mat}"], bevel={bevel})')
        return (f'box("{name}", {_f(fixed + b0)}, {_f(fixed + b1)}, {_f(a0)}, {_f(a1)}, '
                f'{_f(zz0)}, {_f(zz1)}, M["{mat}"], bevel={bevel})')

    if opening["kind"] == "door":
        em.part(sbox(f"door_{oid}", c0 + 0.02, c1 - 0.02, -0.02, 0.02, z0, z1, "door"))
        em.part(sbox(f"jamb_{oid}_a", c0, c0 + 0.05, -t / 2, t / 2, z0, z1, "trim"))
        em.part(sbox(f"jamb_{oid}_b", c1 - 0.05, c1, -t / 2, t / 2, z0, z1, "trim"))
    else:
        em.part(sbox(f"glass_{oid}", c0 + 0.05, c1 - 0.05, -0.01, 0.01, z0 + 0.05, z1 - 0.05, "glass", bevel=0))
        em.part(sbox(f"frame_{oid}_a", c0, c0 + 0.05, -t / 2, t / 2, z0, z1, "trim"))
        em.part(sbox(f"frame_{oid}_b", c1 - 0.05, c1, -t / 2, t / 2, z0, z1, "trim"))
        em.part(sbox(f"frame_{oid}_top", c0, c1, -t / 2, t / 2, z1 - 0.05, z1, "trim"))
        em.part(sbox(f"frame_{oid}_bot", c0, c1, -t / 2, t / 2, z0, z0 + 0.05, "trim"))
        em.part(sbox(f"sill_{oid}", c0 - 0.05, c1 + 0.05, -t / 2 - 0.03, t / 2 + 0.03, z0 - 0.04, z0, "trim"))


def emit_walls(em, table):
    em.set_stage("walls")
    for vol in table["volumes"]:
        vid = vol["id"]
        for f in range(vol["floors"]):
            zb = f * vol["floor_height"]
            zt = zb + vol["floor_height"]
            for wall in ("south", "north", "east", "west"):
                if wall in vol.get("shared_walls", []):
                    continue
                length = wall_length(vol, wall)
                ops = [(o["at"], o["width"], o["z0"], o["z1"])
                       for o in table["openings"]
                       if o["volume"] == vid and o["floor"] == f and o["wall"] == wall]
                em.add(f"# wall: {vid} floor {f} {wall}")
                for j, (a0, a1, oz0, oz1) in enumerate(
                        wall_segments(length, 0.0, vol["floor_height"], ops)):
                    bx0, bx1, by0, by1, bz0, bz1 = wall_box_coords(vol, wall, a0, a1, zb, oz0, oz1)
                    em.part(f'box("wall_{vid}_{f}_{wall}_{j}", {_f(bx0)}, {_f(bx1)}, {_f(by0)}, {_f(by1)}, '
                            f'{_f(bz0)}, {_f(bz1)}, M["wall"], bevel=0.002)')
                for o in [o for o in table["openings"]
                          if o["volume"] == vid and o["floor"] == f and o["wall"] == wall]:
                    emit_opening_hardware(em, vol, zb, wall, o)
    for p in table.get("partitions", []):
        vol = next(v for v in table["volumes"] if v["id"] == p["volume"])
        t = p.get("thickness", 0.1)
        zb = p["floor"] * vol["floor_height"]
        zt = zb + vol["floor_height"]
        length = p["to"] - p["from"]
        ops = [(o["at"], o["width"], o["z0"], o["z1"]) for o in p.get("openings", [])]
        em.add(f"# partition: {p['id']}")
        for j, (a0, a1, oz0, oz1) in enumerate(wall_segments(length, 0.0, vol["floor_height"], ops)):
            if p["axis"] == "x":
                bx0, bx1 = p["at"] - t / 2, p["at"] + t / 2
                by0, by1 = p["from"] + a0, p["from"] + a1
            else:
                bx0, bx1 = p["from"] + a0, p["from"] + a1
                by0, by1 = p["at"] - t / 2, p["at"] + t / 2
            em.part(f'box("part_{p["id"]}_{j}", {_f(bx0)}, {_f(bx1)}, {_f(by0)}, {_f(by1)}, '
                    f'{_f(zb + oz0)}, {_f(zb + oz1)}, M["wall"], bevel=0.002)')


def emit_roof(em, table):
    em.set_stage("roof")
    for vol in table["volumes"]:
        vid = vol["id"]
        z_top = vol["floors"] * vol["floor_height"]
        x0, y0, x1, y1 = vol["x0"], vol["y0"], vol["x1"], vol["y1"]
        roof = vol["roof"]
        if roof["type"] == "flat":
            em.add(f"# flat roof: {vid}")
            em.part(f'box("roof_{vid}", {_f(x0 - roof["overhang"])}, {_f(x1 + roof["overhang"])}, '
                    f'{_f(y0 - roof["overhang"])}, {_f(y1 + roof["overhang"])}, '
                    f'{_f(z_top)}, {_f(z_top + 0.15)}, M["roof"], bevel=0)')
            for wall, (ax0, ay0, ax1, ay1) in (
                    ("s", (x0, y0 - 0.05, x1, y0 + 0.05)), ("n", (x0, y1 - 0.05, x1, y1 + 0.05)),
                    ("w", (x0 - 0.05, y0, x0 + 0.05, y1)), ("e", (x1 - 0.05, y0, x1 + 0.05, y1))):
                em.part(f'box("parapet_{vid}_{wall}", {_f(ax0)}, {_f(ax1)}, {_f(ay0)}, {_f(ay1)}, '
                        f'{_f(z_top + 0.15)}, {_f(z_top + 0.45)}, M["exterior"], bevel=0.002)')
            continue
        pitch = math.radians(roof["pitch_deg"])
        ov = roof["overhang"]
        w = x1 - x0
        d = y1 - y0
        em.add(f"# gable roof: {vid}")
        if w >= d:
            ridge_y = (y0 + y1) / 2
            run = d / 2 + ov
            rise = run * math.tan(pitch)
            z_ridge = z_top + rise
            slope = math.hypot(run, rise)
            theta = math.atan2(rise, run)
            em.part(f'beam("ridge_{vid}", ({_f(x0 - ov)}, {_f(ridge_y)}, {_f(z_ridge)}), '
                    f'({_f(x1 + ov)}, {_f(ridge_y)}, {_f(z_ridge)}), 0.12, 0.2, M["frame"])')
            n_raft = max(2, int(w / 0.6) + 1)
            for i in range(n_raft):
                rx = x0 + i * (w / (n_raft - 1))
                em.part(f'beam("rafter_{vid}_s{i}", ({_f(rx)}, {_f(y0 - ov)}, {_f(z_top)}), '
                        f'({_f(rx)}, {_f(ridge_y)}, {_f(z_ridge)}), 0.05, 0.12, M["frame"])')
                em.part(f'beam("rafter_{vid}_n{i}", ({_f(rx)}, {_f(y1 + ov)}, {_f(z_top)}), '
                        f'({_f(rx)}, {_f(ridge_y)}, {_f(z_ridge)}), 0.05, 0.12, M["frame"])')
            span = w + 2 * ov
            n_strips = max(1, math.ceil(span / 0.3))
            sw = span / n_strips
            for side, (yc, rot) in (("s", ((y0 - ov + ridge_y) / 2, theta)),
                                    ("n", ((ridge_y + y1 + ov) / 2, -theta))):
                em.add(f"for _i in range({n_strips}):")
                em.part(f'    obox("roof_{vid}_{side}%d" % _i, '
                        f'({_f(x0 - ov)} + (_i + 0.5) * {_f(sw)}, {_f(yc)}, {_f((z_top + z_ridge) / 2)}), '
                        f'({_f(sw)}, {_f(slope)}, 0.05), ({_f(rot)}, 0, 0), M["roof"], bevel=0.001)',
                        n=n_strips)
        else:
            ridge_x = (x0 + x1) / 2
            run = w / 2 + ov
            rise = run * math.tan(pitch)
            z_ridge = z_top + rise
            slope = math.hypot(run, rise)
            theta = math.atan2(rise, run)
            em.part(f'beam("ridge_{vid}", ({_f(ridge_x)}, {_f(y0 - ov)}, {_f(z_ridge)}), '
                    f'({_f(ridge_x)}, {_f(y1 + ov)}, {_f(z_ridge)}), 0.12, 0.2, M["frame"])')
            n_raft = max(2, int(d / 0.6) + 1)
            for i in range(n_raft):
                ry = y0 + i * (d / (n_raft - 1))
                em.part(f'beam("rafter_{vid}_w{i}", ({_f(x0 - ov)}, {_f(ry)}, {_f(z_top)}), '
                        f'({_f(ridge_x)}, {_f(ry)}, {_f(z_ridge)}), 0.05, 0.12, M["frame"])')
                em.part(f'beam("rafter_{vid}_e{i}", ({_f(x1 + ov)}, {_f(ry)}, {_f(z_top)}), '
                        f'({_f(ridge_x)}, {_f(ry)}, {_f(z_ridge)}), 0.05, 0.12, M["frame"])')
            span = d + 2 * ov
            n_strips = max(1, math.ceil(span / 0.3))
            sw = span / n_strips
            for side, (xc, rot) in (("w", ((x0 - ov + ridge_x) / 2, -theta)),
                                    ("e", ((ridge_x + x1 + ov) / 2, theta))):
                em.add(f"for _i in range({n_strips}):")
                em.part(f'    obox("roof_{vid}_{side}%d" % _i, '
                        f'({_f(xc)}, {_f(y0 - ov)} + (_i + 0.5) * {_f(sw)}, {_f((z_top + z_ridge) / 2)}), '
                        f'({_f(slope)}, {_f(sw)}, 0.05), (0, {_f(rot)}, 0), M["roof"], bevel=0.001)',
                        n=n_strips)


# ---------------------------------------------------------------- interior
def _rbox(item, u0, u1, v0, v1):
    """Local rect (u along w, v along d) -> absolute (x0, x1, y0, y1)."""
    x, y = item["x"], item["y"]
    if item.get("rot", 0) == 90:
        return (x - v1, x - v0, y + u0, y + u1)
    return (x + u0, x + u1, y + v0, y + v1)


def _rpoint(item, du, dv):
    x, y = item["x"], item["y"]
    if item.get("rot", 0) == 90:
        return (x - dv, y + du)
    return (x + du, y + dv)


def _box(em, name, x0, x1, y0, y1, z0, z1, mat, bevel=0.002):
    em.part(f'box("{name}", {_f(x0)}, {_f(x1)}, {_f(y0)}, {_f(y1)}, {_f(z0)}, {_f(z1)}, M["{mat}"], bevel={bevel})')


def _fbox(em, name, item, zb, u0, u1, v0, v1, z0, z1, mat, bevel=0.002):
    x0, x1, y0, y1 = _rbox(item, u0, u1, v0, v1)
    _box(em, name, x0, x1, y0, y1, zb + z0, zb + z1, mat, bevel)


def emit_furniture(em, item, room, vol):
    """One furniture piece, built from boxes/cylinders/tubes. All z are
    relative to the room's finished floor (zb)."""
    kind = item["kind"]
    fid = item["id"]
    zb = room["floor"] * vol["floor_height"]
    w, d = item["w"], item["d"]
    hw, hd = w / 2, d / 2
    if kind == "bed":
        _fbox(em, f"bed_{fid}_frame", item, zb, -hw, hw, -hd, hd, 0.0, 0.25, "frame")
        _fbox(em, f"bed_{fid}_mattress", item, zb, -hw + 0.05, hw - 0.05, -hd + 0.05, hd - 0.05, 0.25, 0.45, "fabric")
        _fbox(em, f"bed_{fid}_pillow_a", item, zb, -hw + 0.1, -0.05, -hd + 0.05, -hd + 0.4, 0.45, 0.58, "fabric")
        _fbox(em, f"bed_{fid}_pillow_b", item, zb, 0.05, hw - 0.1, -hd + 0.05, -hd + 0.4, 0.45, 0.58, "fabric")
        _fbox(em, f"bed_{fid}_head", item, zb, -hw, hw, -hd - 0.05, -hd, 0.0, 0.9, "frame")
    elif kind == "nightstand":
        _fbox(em, f"ns_{fid}", item, zb, -hw, hw, -hd, hd, 0.0, 0.5, "cabinet")
        _fbox(em, f"ns_{fid}_drawer", item, zb, -hw + 0.05, hw - 0.05, hd - 0.02, hd, 0.3, 0.45, "trim")
    elif kind == "dresser":
        _fbox(em, f"dresser_{fid}", item, zb, -hw, hw, -hd, hd, 0.0, 0.9, "cabinet")
        for i, zz in enumerate((0.15, 0.45, 0.7)):
            _fbox(em, f"dresser_{fid}_drawer{i}", item, zb, -hw + 0.05, hw - 0.05, hd - 0.02, hd, zz, zz + 0.12, "trim")
    elif kind == "sofa":
        _fbox(em, f"sofa_{fid}_base", item, zb, -hw, hw, -hd, hd, 0.0, 0.35, "fabric")
        _fbox(em, f"sofa_{fid}_back", item, zb, -hw, hw, -hd, -hd + 0.18, 0.35, 0.85, "fabric")
        _fbox(em, f"sofa_{fid}_arm_a", item, zb, -hw, -hw + 0.18, -hd, hd, 0.0, 0.6, "fabric")
        _fbox(em, f"sofa_{fid}_arm_b", item, zb, hw - 0.18, hw, -hd, hd, 0.0, 0.6, "fabric")
        _fbox(em, f"sofa_{fid}_cush_a", item, zb, -hw + 0.2, -0.02, -hd + 0.2, hd - 0.05, 0.35, 0.48, "fabric")
        _fbox(em, f"sofa_{fid}_cush_b", item, zb, 0.02, hw - 0.2, -hd + 0.2, hd - 0.05, 0.35, 0.48, "fabric")
    elif kind == "table":
        _fbox(em, f"table_{fid}_top", item, zb, -hw, hw, -hd, hd, 0.72, 0.76, "frame")
        for i, (du, dv) in enumerate(((-hw + 0.06, -hd + 0.06), (hw - 0.06, -hd + 0.06),
                                      (-hw + 0.06, hd - 0.06), (hw - 0.06, hd - 0.06))):
            px, py = _rpoint(item, du, dv)
            em.part(f'cyl("table_{fid}_leg{i}", {_f(px)}, {_f(py)}, 0.03, {_f(zb)}, {_f(zb + 0.72)}, M["frame"], verts=12, bevel=0)')
    elif kind == "chair":
        _fbox(em, f"chair_{fid}_seat", item, zb, -hw, hw, -hd, hd, 0.42, 0.47, "frame")
        _fbox(em, f"chair_{fid}_back", item, zb, -hw, hw, -hd, -hd + 0.06, 0.47, 0.9, "frame")
        for i, (du, dv) in enumerate(((-hw + 0.05, -hd + 0.05), (hw - 0.05, -hd + 0.05),
                                      (-hw + 0.05, hd - 0.05), (hw - 0.05, hd - 0.05))):
            px, py = _rpoint(item, du, dv)
            em.part(f'cyl("chair_{fid}_leg{i}", {_f(px)}, {_f(py)}, 0.025, {_f(zb)}, {_f(zb + 0.42)}, M["frame"], verts=12, bevel=0)')
    elif kind == "kitchen_run":
        n = max(1, round(w / 0.6))
        cw = w / n
        for i in range(n):
            _fbox(em, f"krun_{fid}_base{i}", item, zb, -hw + i * cw, -hw + (i + 1) * cw, -hd, hd, 0.0, 0.9, "cabinet")
        _fbox(em, f"krun_{fid}_top", item, zb, -hw, hw, -hd, hd, 0.9, 0.94, "countertop")
        for i in range(n):
            _fbox(em, f"krun_{fid}_up{i}", item, zb, -hw + i * cw, -hw + (i + 1) * cw, -hd, -hd + 0.35, 1.4, 2.1, "cabinet")
        mid = n // 2
        _fbox(em, f"krun_{fid}_range", item, zb, -hw + mid * cw, -hw + (mid + 1) * cw, -hd, hd, 0.0, 0.9, "dark")
        for i, (du, dv) in enumerate(((-0.12, 0.0), (0.12, 0.0), (-0.12, 0.0), (0.12, 0.0))):
            px, py = _rpoint(item, -hw + (mid + 0.5) * cw + du, dv)
            em.part(f'cyl("krun_{fid}_burner{i}", {_f(px)}, {_f(py)}, 0.08, {_f(zb + 0.94)}, {_f(zb + 0.95)}, M["dark"], verts=20, bevel=0)')
        sink_u = -hw + 0.5 * cw
        sx, sy = _rpoint(item, sink_u, 0.0)
        em.part(f'box("krun_{fid}_sink", {_f(sx - 0.25)}, {_f(sx + 0.25)}, {_f(sy - 0.2)}, {_f(sy + 0.2)}, '
                f'{_f(zb + 0.94)}, {_f(zb + 1.0)}, M["fixture"], bevel=0.002)')
        fx, fy = _rpoint(item, sink_u, -hd + 0.03)
        em.part(f'tube("krun_{fid}_faucet", ({_f(fx)}, {_f(fy)}, {_f(zb + 0.94)}), '
                f'({_f(fx)}, {_f(fy)}, {_f(zb + 1.3)}), 0.015, M["fixture"], 12)')
        em.part(f'tube("krun_{fid}_spout", ({_f(fx)}, {_f(fy)}, {_f(zb + 1.3)}), '
                f'({_f(fx)}, {_f(fy + 0.22)}, {_f(zb + 1.3)}), 0.012, M["fixture"], 12)')
    elif kind == "island":
        _fbox(em, f"island_{fid}_base", item, zb, -hw, hw, -hd, hd, 0.0, 0.9, "cabinet")
        _fbox(em, f"island_{fid}_top", item, zb, -hw - 0.05, hw + 0.05, -hd - 0.05, hd + 0.05, 0.9, 0.94, "countertop")
        for i, du in enumerate((-hw / 2, hw / 2)):
            sx, sy = _rpoint(item, du, hd + 0.3)
            em.part(f'cyl("island_{fid}_stool{i}", {_f(sx)}, {_f(sy)}, 0.18, {_f(zb + 0.6)}, {_f(zb + 0.64)}, M["frame"], verts=20, bevel=0)')
            em.part(f'tube("island_{fid}_stoolleg{i}", ({_f(sx)}, {_f(sy)}, {_f(zb)}), '
                    f'({_f(sx)}, {_f(sy)}, {_f(zb + 0.6)}), 0.02, M["frame"], 12)')
    elif kind == "fridge":
        _fbox(em, f"fridge_{fid}", item, zb, -hw, hw, -hd, hd, 0.0, 1.9, "fixture")
        _fbox(em, f"fridge_{fid}_door_a", item, zb, -hw + 0.03, -0.02, hd - 0.02, hd, 0.1, 1.8, "trim")
        _fbox(em, f"fridge_{fid}_door_b", item, zb, 0.02, hw - 0.03, hd - 0.02, hd, 0.1, 1.8, "trim")
    elif kind == "tub":
        _fbox(em, f"tub_{fid}", item, zb, -hw, hw, -hd, hd, 0.0, 0.55, "fixture")
        _fbox(em, f"tub_{fid}_water", item, zb, -hw + 0.08, hw - 0.08, -hd + 0.08, hd - 0.08, 0.45, 0.5, "water")
    elif kind == "vanity":
        _fbox(em, f"vanity_{fid}", item, zb, -hw, hw, -hd, hd, 0.0, 0.8, "cabinet")
        _fbox(em, f"vanity_{fid}_top", item, zb, -hw, hw, -hd, hd, 0.8, 0.84, "countertop")
        _fbox(em, f"vanity_{fid}_mirror", item, zb, -hw + 0.1, hw - 0.1, -hd - 0.02, -hd, 1.0, 1.6, "mirror")
        mx, my = _rpoint(item, 0.0, -hd + 0.03)
        em.part(f'tube("vanity_{fid}_faucet", ({_f(mx)}, {_f(my)}, {_f(zb + 0.84)}), '
                f'({_f(mx)}, {_f(my)}, {_f(zb + 1.05)}), 0.012, M["fixture"], 12)')
    elif kind == "toilet":
        _fbox(em, f"toilet_{fid}_tank", item, zb, -hw, hw, -hd, -hd + 0.15, 0.5, 0.95, "fixture")
        cx, cy = _rpoint(item, 0.0, 0.05)
        em.part(f'cyl("toilet_{fid}_bowl", {_f(cx)}, {_f(cy)}, 0.2, {_f(zb)}, {_f(zb + 0.4)}, M["fixture"], verts=24, bevel=0.01)')
        _fbox(em, f"toilet_{fid}_seat", item, zb, -0.22, 0.22, -0.05, 0.3, 0.4, 0.45, "trim")
    elif kind == "counter":
        _fbox(em, f"counter_{fid}", item, zb, -hw, hw, -hd, hd, 0.0, 0.9, "cabinet")
        _fbox(em, f"counter_{fid}_top", item, zb, -hw, hw, -hd, hd, 0.9, 0.94, "countertop")
    elif kind == "shelf":
        _fbox(em, f"shelf_{fid}_a", item, zb, -hw, hw, -hd, hd, 1.2, 1.24, "frame")
        _fbox(em, f"shelf_{fid}_b", item, zb, -hw, hw, -hd, hd, 1.7, 1.74, "frame")
    else:  # pragma: no cover - validation rejects unknown kinds first
        raise TableError(f"furniture '{fid}': unknown kind {kind!r}")


def emit_interior(em, table):
    em.set_stage("interior")
    vols = {v["id"]: v for v in table["volumes"]}
    rooms = {r["id"]: r for r in table["rooms"]}
    for item in table.get("furniture", []):
        room = rooms[item["room"]]
        vol = vols[room["volume"]]
        em.add(f"# furniture: {item['id']} ({item['kind']}) in {room['id']}")
        emit_furniture(em, item, room, vol)


# ---------------------------------------------------------------- site/lights
def emit_site(em, table):
    em.set_stage("site")
    lot = table["lot"]
    em.add("# site: lawn, driveway, trees")
    em.part(f'box("lawn", {_f(lot["x0"])}, {_f(lot["x1"])}, {_f(lot["y0"])}, {_f(lot["y1"])}, '
            '-0.05, 0.0, M["grass"], bevel=0)')
    house = next((v for v in table["volumes"] if v["kind"] == "house"), table["volumes"][0])
    door = next((o for o in table["openings"]
                 if o["volume"] == house["id"] and o["kind"] == "door" and o["wall"] == "south"), None)
    dx = (house["x0"] + door["at"] + door["width"] / 2) if door else (house["x0"] + house["x1"]) / 2
    em.part(f'box("driveway", {_f(dx - 1.0)}, {_f(dx + 1.0)}, {_f(lot["y0"])}, {_f(house["y0"])}, '
            '-0.04, 0.0, M["concrete"], bevel=0)')
    spots = [(lot["x0"] + 3, lot["y0"] + 3), (lot["x1"] - 3, lot["y0"] + 3),
             (lot["x0"] + 3, lot["y1"] - 3), (lot["x1"] - 3, lot["y1"] - 3),
             ((lot["x0"] + lot["x1"]) / 2, lot["y1"] - 3), (lot["x1"] - 3, (lot["y0"] + lot["y1"]) / 2),
             (lot["x0"] + 3, (lot["y0"] + lot["y1"]) / 2)]
    trees = []
    for (tx, ty) in spots:
        if len(trees) >= 4:
            break
        clear = True
        for v in table["volumes"]:
            if v["x0"] - 1 <= tx <= v["x1"] + 1 and v["y0"] - 1 <= ty <= v["y1"] + 1:
                clear = False
        if clear:
            trees.append((tx, ty))
    for i, (tx, ty) in enumerate(trees):
        em.part(f'cyl("tree_{i}_trunk", {_f(tx)}, {_f(ty)}, 0.09, 0.0, 1.8, M["trunk"], verts=12, bevel=0)')
        em.part(f'sphere("tree_{i}_canopy_a", {_f(tx)}, {_f(ty)}, 2.2, 0.9, M["leaves"], squash=0.9)')
        em.part(f'sphere("tree_{i}_canopy_b", {_f(tx + 0.4)}, {_f(ty + 0.2)}, 2.7, 0.65, M["leaves"], squash=0.9)')
        em.part(f'sphere("tree_{i}_canopy_c", {_f(tx - 0.35)}, {_f(ty - 0.15)}, 2.6, 0.6, M["leaves"], squash=0.9)')


def emit_lights(em, table):
    em.set_stage("lights")
    em.add('WARM = (1.0, 0.72, 0.45)')
    vols = {v["id"]: v for v in table["volumes"]}
    for room in table["rooms"]:
        vol = vols[room["volume"]]
        zb = room["floor"] * vol["floor_height"]
        zt = zb + vol["floor_height"]
        cx = (room["x0"] + room["x1"]) / 2
        cy = (room["y0"] + room["y1"]) / 2
        watts = ROOM_WATTS[room.get("kind", "room")]
        em.part(f'light("room_{room["id"]}", "AREA", ({_f(cx)}, {_f(cy)}, {_f(zt - 0.05)}), '
                f'{watts} * float(OPTS.get("room", 0.5 if DAY else 1.0)), WARM, '
                f'size={_f(room["x1"] - room["x0"])}, size_y={_f(room["y1"] - room["y0"])})')


# ---------------------------------------------------------------- assembly
def _slug(name):
    out = "".join(c.lower() if c.isalnum() else "-" for c in name)
    return "-".join(p for p in out.split("-") if p) or "house"


def generate(table, source_name, slug):
    """Build the emitted build.py text. Returns (text, counts)."""
    em = Emit()
    name = table["project"]["name"]
    mats = resolve_materials(table)

    em.add(f'"""{name} - generated by generate_build.py from {source_name}.')
    em.add("Deterministic: the same dimensions table always produces this script.")
    em.add("Do not edit by hand; edit the table and regenerate.")
    em.add("Method: blueprint (Nyxera0x/blueprint) - every part its own object,")
    em.add("tagged with its build stage (K.STAGE), so a film can fly them in.")
    em.add("Run:")
    em.add(f"  blender -b --factory-startup -P {slug}-build.py -- aerial street backyard interior --look day --samples 192 --res 1920x1080")
    em.add(f"Stills land in blueprint-out/{slug}/render_<shot><tag>.png.")
    em.add('"""')
    em.add("import math")
    em.add("import os")
    em.add("import sys")
    em.add("import time")
    em.add("")
    em.add('SKILL_DIR = os.environ.get("BLUEPRINT_SKILL_DIR", os.path.join(os.path.expanduser("~"), ".claude", "skills", "blueprint"))')
    em.add('sys.path.insert(0, os.path.join(SKILL_DIR, "kit"))')
    em.add("import bpy")
    em.add("from mathutils import Vector")
    em.add("import bkit as K")
    em.add("from bkit import beam, box, camera, cyl, light, obox, sphere, tube, vec")
    em.add("")
    em.add('OPTS, SHOTS = K.args(("aerial", "street", "backyard", "interior"))')
    em.add("scene = K.setup(OPTS)")
    em.add('LOOK = str(OPTS.get("look", "day"))')
    em.add('DAY = LOOK == "day"')
    em.add("FILM = K.FILM")
    em.add(f'OUT = os.path.join(os.environ.get("BLUEPRINT_OUT", "blueprint-out"), "{slug}")')
    em.add("os.makedirs(OUT, exist_ok=True)")
    em.add("t0 = time.time()")
    em.add("")
    em.add(f"TABLE = {json.dumps(table, indent=2, sort_keys=True)}")
    em.add("")
    em.add("def stage(s):")
    em.add("    K.STAGE[0] = s")
    em.add("")
    em.add("# ---------------------------------------------------------------- materials")
    em.add("M = {}")
    mat_specs = [
        ("exterior", mats["exterior"], 0.85, 0.0), ("roof", mats["roof"], 0.6, 0.4),
        ("floor", mats["floor"], 0.6, 0.0), ("wall", mats["wall"], 0.9, 0.0),
        ("countertop", mats["countertop"], 0.25, 0.0), ("cabinet", mats["cabinet"], 0.5, 0.0),
        ("fixture", mats["fixture"], 0.3, 0.8), ("trim", mats["trim"], 0.7, 0.0),
        ("door", mats["door"], 0.6, 0.0), ("accent", mats["accent"], 0.8, 0.0),
        ("frame", FINISHES["walnut"], 0.8, 0.0), ("fabric", mats["accent"], 0.95, 0.0),
    ]
    for key, rgb, rough, metal in mat_specs:
        em.add(f'M["{key}"] = K.principled("{key}", {_c(rgb)}, rough={rough}, metal={metal})')
    em.add('M["glass"] = K.glass("glass")')
    em.add('M["concrete"] = K.principled("concrete", (0.62, 0.62, 0.6), rough=0.95)')
    em.add('M["grass"] = K.principled("grass", (0.25, 0.4, 0.15), rough=1.0)')
    em.add('M["trunk"] = K.principled("trunk", (0.3, 0.2, 0.12), rough=0.95)')
    em.add('M["leaves"] = K.principled("leaves", (0.2, 0.35, 0.12), rough=1.0)')
    em.add('M["water"] = K.principled("water", (0.6, 0.75, 0.85), rough=0.1, metal=0.1)')
    em.add('M["mirror"] = K.principled("mirror", (0.85, 0.88, 0.9), rough=0.05, metal=1.0)')
    em.add('M["dark"] = K.principled("dark", (0.08, 0.08, 0.09), rough=0.5, metal=0.3)')
    em.add('K.boards(M["floor"], 0.15)')
    em.add("")

    emit_foundation(em, table)
    em.add("")
    emit_frame(em, table)
    em.add("")
    emit_floors(em, table)
    em.add("")
    emit_walls(em, table)
    em.add("")
    emit_roof(em, table)
    em.add("")
    emit_interior(em, table)
    em.add("")
    emit_site(em, table)
    em.add("")
    emit_lights(em, table)
    em.add("")

    total = sum(em.counts.values())
    em.add("# ---------------------------------------------------------------- sky and sun")
    em.add('world = bpy.data.worlds.new("sky")')
    em.add("scene.world = world")
    em.add("world.use_nodes = True")
    em.add("WN = world.node_tree.nodes")
    em.add('WN["Background"].inputs["Color"].default_value = (0.72, 0.8, 0.9, 1) if DAY else (0.32, 0.38, 0.5, 1)')
    em.add('WN["Background"].inputs["Strength"].default_value = float(OPTS.get("sky", 1.0 if DAY else 1.3))')
    em.add('SUN_AZ, SUN_EL = math.radians(float(OPTS.get("sun_az", 300))), math.radians(float(OPTS.get("sun_el", 30)))')
    em.add("SUN_DIR = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))")
    em.add('sun = bpy.data.lights.new("day_sun", "SUN")')
    em.add('sun.energy = float(OPTS.get("sun", 3.6))')
    em.add("sun.color = (1.0, 0.9, 0.76)")
    em.add("sun.angle = math.radians(1.5)")
    em.add('sun_ob = bpy.data.objects.new("day_sun", sun)')
    em.add("scene.collection.objects.link(sun_ob)")
    em.add('sun_ob.rotation_euler = SUN_DIR.to_track_quat("Z", "Y").to_euler()')
    em.add("")
    em.add("# ---------------------------------------------------------------- shots")
    lot = table["lot"]
    house = next((v for v in table["volumes"] if v["kind"] == "house"), table["volumes"][0])
    hcx = (house["x0"] + house["x1"]) / 2
    hcy = (house["y0"] + house["y1"]) / 2
    lcx = (lot["x0"] + lot["x1"]) / 2
    lcy = (lot["y0"] + lot["y1"]) / 2
    lot_w = lot["x1"] - lot["x0"]
    lot_h = lot["y1"] - lot["y0"]
    biggest = max(table["rooms"], key=lambda r: (r["x1"] - r["x0"]) * (r["y1"] - r["y0"]))
    kitchen = next((r for r in table["rooms"] if r.get("kind") == "kitchen"), None)
    bvol = next(v for v in table["volumes"] if v["id"] == biggest["volume"])
    ib = biggest["floor"] * bvol["floor_height"]
    if kitchen is not None:
        kvol = next(v for v in table["volumes"] if v["id"] == kitchen["volume"])
        kb = kitchen["floor"] * kvol["floor_height"]
        itarget = ((kitchen["x0"] + kitchen["x1"]) / 2, (kitchen["y0"] + kitchen["y1"]) / 2, kb + 1.2)
    else:
        itarget = (hcx, hcy, 1.2)
    shots = {
        "aerial": ((lcx - lot_w * 0.6, lcy - lot_h * 0.6, max(lot_w, lot_h) * 0.6), (hcx, hcy, 0.5), 19, -0.2),
        "street": ((hcx, lot["y0"] - 6.0, 3.2), (hcx, hcy, 1.6), 24, -0.2),
        "backyard": ((hcx, lot["y1"] + 5.0, 4.0), (hcx, hcy + 3.0, 1.2), 24, -0.2),
        "interior": (((biggest["x0"] + biggest["x1"]) / 2, (biggest["y0"] + biggest["y1"]) / 2, ib + 1.6),
                     itarget, 20, -0.3),
    }
    em.add("SHOT = {")
    for name, (loc, tgt, lens, ev) in shots.items():
        em.add(f'    "{name}": dict(loc=vec("{name}_loc", ({_f(loc[0])}, {_f(loc[1])}, {_f(loc[2])})), '
               f'target=vec("{name}_at", ({_f(tgt[0])}, {_f(tgt[1])}, {_f(tgt[2])})), lens={lens}, ev={ev}),')
    em.add("}")
    em.add(f"EXPECTED_PARTS = {total}")
    em.add('print(f"built in {time.time() - t0:.1f} s, {len(K.PARTS)} parts (expected {EXPECTED_PARTS})")')
    em.add('if OPTS.get("blend"):')
    em.add(f'    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "{slug}.blend"))')
    em.add("for s in ([] if FILM else SHOTS):")
    em.add('    c = SHOT[s]')
    em.add('    scene.camera = camera(s, c["loc"], c["target"], c["lens"])')
    em.add('    scene.view_settings.exposure = float(OPTS.get(f"{s}_ev", c.get("ev", 0.0)))')
    em.add('    scene.render.filepath = os.path.join(OUT, f"render_{s}{OPTS.get(\'tag\', \'\')}.png")')
    em.add("    t1 = time.time()")
    em.add("    bpy.ops.render.render(write_still=True)")
    em.add('    print(f"{s}: rendered in {time.time() - t1:.1f} s")')
    return em.text(), dict(em.counts)


# ---------------------------------------------------------------- main
def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Generate a Blender build.py from a dimensions table.")
    ap.add_argument("table", help="dimensions table JSON (see SCHEMA.md)")
    ap.add_argument("-o", "--output", default=None, help="output build.py (default: <table>-build.py)")
    ap.add_argument("--slug", default=None, help="output folder slug (default: from the project name)")
    args = ap.parse_args(argv)
    with open(args.table, "r", encoding="utf-8") as fh:
        table = json.load(fh)
    try:
        validate(table)
    except TableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    slug = args.slug or _slug(table["project"]["name"])
    out = args.output or (os.path.splitext(args.table)[0] + "-build.py")
    script, counts = generate(table, os.path.basename(args.table), slug)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(script)
    total = sum(counts.values())
    print(f"wrote {out}: {total} parts")
    for s in STAGES:
        print(f"  {s}: {counts[s]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
