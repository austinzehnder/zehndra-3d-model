"""Recording stub of the blueprint kit (bkit) for testing generated
build.py scripts without Blender.

Every part-creating call records (name, stage) in PARTS; everything
else is a no-op. Signatures mirror the real kit/bkit.py so a script
that runs against this stub has the right call shapes for the real
kit. At exit it prints the per-stage part counts and flags duplicate
part names and degenerate (zero-size) parts.

This stub lives under tests/stubkit/kit/ so that a generated script
finds it when BLUEPRINT_SKILL_DIR points at tests/stubkit.
"""

import atexit
import sys
from collections import Counter

OPTS = {}
ROOT = None
STAGE = ["misc"]
PARTS = []
FILM = False
ASSETS = {}


def _summary():
    counts = Counter(stage for _, stage in PARTS)
    order = ["foundation", "frame", "floors", "walls", "roof",
             "interior", "site", "lights", "misc"]
    print("STUB PARTS BY STAGE: " + ", ".join(
        f"{s}={counts.get(s, 0)}" for s in order if counts.get(s, 0)))
    print(f"STUB TOTAL PARTS: {len(PARTS)}")
    names = [n for n, _ in PARTS]
    dupes = sorted(n for n, k in Counter(names).items() if k > 1)
    if dupes:
        print(f"STUB DUPLICATE NAMES ({len(dupes)}): {dupes[:10]}")


atexit.register(_summary)


class _Obj:
    def __init__(self, name):
        self.name = name
        self.location = (0, 0, 0)
        self.rotation_euler = (0, 0, 0)


class _Scene:
    def __init__(self):
        import types
        self.view_settings = types.SimpleNamespace(exposure=0.0)
        self.render = types.SimpleNamespace(filepath="")
        self.world = None
        self.camera = None
        self.collection = types.SimpleNamespace(
            objects=types.SimpleNamespace(link=lambda o: None))


class _Mat:
    def __init__(self, name):
        self.name = name


def _record(name):
    PARTS.append((name, STAGE[0]))


def _check_size(name, dims):
    if any(d <= 0 for d in dims):
        raise ValueError(f"stub bkit: part {name!r} has a non-positive dimension {dims}")


def args(default_shots=("hero",)):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    shots, opts = [], {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                opts[argv[i][2:]] = argv[i + 1]
                i += 2
            else:
                opts[argv[i][2:]] = True
                i += 1
        else:
            shots.append(argv[i])
            i += 1
    return opts, shots or list(default_shots)


def setup(opts, samples=256, res="1920x1080"):
    global OPTS, FILM
    OPTS = opts
    FILM = bool(opts.get("film"))
    return _Scene()


def vec(s, default):
    return tuple(map(float, str(OPTS[s]).split(","))) if s in OPTS else default


def new_mat(name):
    return _Mat(name), None, None, None


def principled(name, color, rough=0.5, metal=0.0, emission=None, estr=0.0):
    return _Mat(name)


def glass(name, tint=(0.95, 0.97, 0.97)):
    return _Mat(name)


def fabric(name, color, rough=0.92, bump=0.45, size=0.35, nmap="rough_linen"):
    return _Mat(name)


def emissive(name, color, strength):
    return _Mat(name)


def boards(m, width, length=2.4, offset=0.37, seam=(0.08, 0.05, 0.03), axis="x", shade=0.8):
    return m


def box(name, x0, x1, y0, y1, z0, z1, mat, bevel=0.004, seg=2, coll=None, mats=None):
    _check_size(name, (x1 - x0, y1 - y0, z1 - z0))
    _record(name)
    return _Obj(name)


def obox(name, c, size, rot, mat, bevel=0.004, seg=2):
    _check_size(name, size)
    _record(name)
    return _Obj(name)


def beam(name, a, b, w, h, mat, up=(0, 0, 1), bevel=0.004):
    if tuple(a) == tuple(b):
        raise ValueError(f"stub bkit: beam {name!r} has zero length")
    _check_size(name, (w, h))
    _record(name)
    return _Obj(name)


def cyl(name, x, y, r, z0, z1, mat, verts=48, bevel=0.004, seg=2, r2=None):
    _check_size(name, (r, z1 - z0))
    _record(name)
    return _Obj(name)


def tube(name, a, b, r, mat, verts=24):
    if tuple(a) == tuple(b):
        raise ValueError(f"stub bkit: tube {name!r} has zero length")
    _check_size(name, (r,))
    _record(name)
    return _Obj(name)


def sphere(name, x, y, z, r, mat, squash=1.0, seg=32):
    _check_size(name, (r,))
    _record(name)
    return _Obj(name)


def prism(name, poly, z_of, thick, mat, mats=None):
    _record(name)
    return _Obj(name)


def light(name, kind, loc, energy, color=(1.0, 0.72, 0.45), size=0.1,
          rot=(0, 0, 0), spot=None, size_y=None):
    _record(name)
    return _Obj(name)


def camera(name, loc, target, lens, shift_y=0.0, shift_x=0.0):
    return _Obj(name)


def aim(o, target):
    return o


def place(mid, x, y, z=0.0, yaw=0.0, scale=1.0, height=None, hook=None):
    return []


def place_variant(mid, x, y, z=0.0, yaw=0.0, height=None, k=None, scale=1.0, hook=None):
    return []


def sstep(a, b, x):
    return 0.0


def fbm(x, y, f, octaves=4, seed=0.0):
    return 0.0
