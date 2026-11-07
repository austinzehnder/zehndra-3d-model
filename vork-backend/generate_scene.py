#!/usr/bin/env python3
"""generate_scene.py - intake brief JSON -> vork scene JSON (v2).

No external dependencies; Python 3.9+ stdlib only.

Reads the house-scene-template.json in this directory, substitutes intake
values for the slots documented in the template's _slots object, strips
every key starting with '_' (template-only metadata), and writes a clean
vork scene JSON: {"version": 2, "nodes": [...], "render": {...}}.

Verified vork fields used here are exactly the ones in the README
first-scene example (examples/first-scene.json) and the glTF asset example:
  version, nodes[].type mesh/light/camera/asset, mesh.translation,
  mesh.geometry.std sphere/grid (+ radius/size),
  mesh.materials[].inputs.base_color / specular_roughness,
  light.shape rectangle, light.translation/target/energy/size/color,
  camera.translation/target, render.resolution, asset.file.

UNVERIFIED fields this script still emits (flagged on stderr every run,
and listed in house-scene-template.json _meta):
  geometry.std "box", "prism", "cylinder" - only "sphere" and "grid" are
    shown in the README. Confirm with `vork help field geometry` on a GPU
    machine before trusting a render; if "box" is unsupported the house
    must be supplied as a .glb asset instead (see README.md).
  geometry.size on box/prism nodes - "size" is verified for grid; its
    meaning on box/prism as [width, height, depth] is assumed.
  light.shape "sun" - only "rectangle" is shown in the README. The script
    always emits the verified rectangle light as well, so dropping the sun
    node still leaves a lit scene.

Usage:
  python3 generate_scene.py sample-brief.json -o sample-scene.json
  python3 generate_scene.py brief.json --camera aerial --lighting dusk
  python3 generate_scene.py brief.json --template house-scene-template.json

The script does NOT run vork (no GPU in this environment) and does NOT
claim a render succeeded. It only proves brief -> scene JSON.
"""

import argparse
import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FT_TO_M = 0.3048
GROUND_Y = -1.0  # README first scene: grid at y=-1 sits below origin sphere.
STOREY_HEIGHT_M = 3.0
ROOF_HEIGHT_M = 2.5

TIER_PRICES = {
    "Single Room / Space": 99,
    "Full Home": 179,
    "Addition / ADU": 249,
}

# Style presets: paint / roof / trim palettes as hex. These are house
# choices, not vork values; they only become base_color after hex_to_rgb().
STYLE_PRESETS = {
    "modern": {"paint_hex": "#D8D2C4", "roof_hex": "#404045",
               "trim_hex": "#FFFFFF"},
    "farmhouse": {"paint_hex": "#F2EFE6", "roof_hex": "#2E2A26",
                  "trim_hex": "#FFFFFF"},
    "craftsman": {"paint_hex": "#8A7B63", "roof_hex": "#4A3B2E",
                  "trim_hex": "#E8DCC8"},
}

# Lighting presets: verified rectangle-light fields only (energy, color).
# Sun node uses the same preset; its shape is UNVERIFIED, see module docstring.
LIGHTING_PRESETS = {
    "day": {"rect_energy": 700, "rect_color": [1, 0.92, 0.8],
            "sun_energy": 500, "sun_color": [1, 0.95, 0.85]},
    "dusk": {"rect_energy": 350, "rect_color": [1, 0.75, 0.55],
             "sun_energy": 250, "sun_color": [1, 0.6, 0.4]},
    "night": {"rect_energy": 150, "rect_color": [0.85, 0.9, 1.0],
              "sun_energy": 0, "sun_color": [0.4, 0.5, 0.8]},
}

CAMERA_PRESETS = {
    "orbit": {"translation": [14, 6, 16], "target": [0, 2, 0]},
    "aerial": {"translation": [0, 22, 6], "target": [0, 0, 0]},
    "street": {"translation": [10, 2, 18], "target": [0, 2, 0]},
    "backyard": {"translation": [-12, 4, -14], "target": [0, 2, 0]},
    # Interior framing is approximate until a real interior model exists.
    "interior": {"translation": [0, 2, 2], "target": [0, 2, -4]},
}

UNVERIFIED_WARNINGS = [
    "geometry.std 'box' (house, windows, door, addition, ADU) is UNVERIFIED "
    "in the README - only 'sphere' and 'grid' are shown. Confirm with "
    "`vork help field geometry` on a GPU machine.",
    "geometry.std 'prism' (gable roof) is UNVERIFIED. If unsupported, "
    "replace with a flat box slab or a .glb roof asset.",
    "geometry.std 'cylinder' (tree trunk) is UNVERIFIED. Omit the trunk "
    "node if unsupported; the sphere canopy alone still reads as a tree.",
    "geometry.size on box/prism as [width, height, depth] is assumed; "
    "'size' is only verified for grid.",
    "light.shape 'sun' is UNVERIFIED; only 'rectangle' is shown in the "
    "README. A verified rectangle light is always emitted as well.",
]


def hex_to_rgb(hex_str):
    """'#D8D2C4' -> [0.847, 0.824, 0.769] (0-1, rounded to 3 dp)."""
    h = hex_str.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"paint/roof hex must be #RRGGBB, got {hex_str!r}")
    return [round(int(h[i:i + 2], 16) / 255.0, 3) for i in (0, 2, 4)]


def strip_private(obj):
    """Remove every key starting with '_' (template-only metadata)."""
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items()
                if not k.startswith("_")}
    if isinstance(obj, list):
        return [strip_private(v) for v in obj]
    return obj


def find_node(nodes, slot_substring):
    for node in nodes:
        if slot_substring in node.get("_slot", ""):
            return node
    raise KeyError(f"template node not found for slot {slot_substring!r}")


def set_color(node, hex_str, roughness=None):
    inputs = node["materials"][0]["inputs"]
    inputs["base_color"] = hex_to_rgb(hex_str)
    if roughness is not None:
        inputs["specular_roughness"] = roughness


def generate(brief, template):
    scope = [s.lower() for s in brief.get("scope", [])]
    stories = int(brief.get("stories", 1))
    total_sq_ft = float(brief["total_sq_ft"])
    existing_sq_ft = float(brief.get("existing_sq_ft", total_sq_ft))
    added_sq_ft = float(brief.get("added_sq_ft", 0))

    # Style preset supplies defaults; explicit brief hex wins.
    style = STYLE_PRESETS.get(brief.get("style_preset", "modern"),
                              STYLE_PRESETS["modern"])
    paint_hex = brief.get("paint_hex") or style["paint_hex"]
    roof_hex = brief.get("roof_hex") or style["roof_hex"]
    roof_type = brief.get("roof_type", "gable").lower()
    lighting = LIGHTING_PRESETS[brief.get("lighting_preset", "day")]
    camera = CAMERA_PRESETS[brief.get("camera_preset", "orbit")]

    # Footprint: total sq ft spread over stories; house is a little
    # deeper than wide is wrong, so width is the long side.
    footprint_sq_ft = total_sq_ft / max(stories, 1)
    side_ft = math.sqrt(footprint_sq_ft)
    house_w = round(side_ft * FT_TO_M, 2)
    house_d = round(house_w * 0.85, 2)
    house_h = round(stories * STOREY_HEIGHT_M, 2)

    nodes = copy.deepcopy(template["nodes"])

    # House body.
    body = find_node(nodes, "house body")
    body["geometry"]["size"] = [house_w, house_h, house_d]
    body["translation"] = [0, round(GROUND_Y + house_h / 2, 2), 0]
    set_color(body, paint_hex, 0.7)

    # Roof: gable prism by default; flat replaces it with a slab.
    roof = find_node(nodes, "gable roof")
    roof_y = round(GROUND_Y + house_h + ROOF_HEIGHT_M / 2, 2)
    if roof_type == "flat":
        roof["geometry"] = {"std": "box",
                            "size": [round(house_w + 0.3, 2), 0.3,
                                     round(house_d + 0.3, 2)]}
        roof["translation"] = [0, round(GROUND_Y + house_h + 0.15, 2), 0]
    else:
        roof["geometry"]["size"] = [round(house_w + 0.6, 2), ROOF_HEIGHT_M,
                                    round(house_d + 0.6, 2)]
        roof["translation"] = [0, roof_y, 0]
    if roof_type == "hip":
        print("WARNING: 'hip' roof is approximated by the gable prism "
              "(UNVERIFIED); confirm roof geometry with `vork help`.",
              file=sys.stderr)
    set_color(roof, roof_hex, 0.5)

    # Windows and door, on the front face (z = depth/2).
    front_z = round(house_d / 2 + 0.05, 2)
    win_y = round(GROUND_Y + house_h * 0.45, 2)
    for slot, x in (("front window, left", -house_w * 0.25),
                    ("front window, right", house_w * 0.25)):
        win = find_node(nodes, slot)
        win["translation"] = [round(x, 2), win_y, front_z]
    door = find_node(nodes, "front door")
    door["translation"] = [0, round(GROUND_Y + 1.5, 2), front_z]

    # Addition: omit the node entirely when out of scope.
    if "addition" in scope and added_sq_ft > 0:
        add = find_node(nodes, "addition volume")
        add_side_ft = math.sqrt(added_sq_ft)
        add_w = round(add_side_ft * FT_TO_M, 2)
        add_d = round(add_w * 0.85, 2)
        add["geometry"]["size"] = [add_w, STOREY_HEIGHT_M, add_d]
        add["translation"] = [round(house_w / 2 + add_w / 2, 2),
                              round(GROUND_Y + STOREY_HEIGHT_M / 2, 2), 0]
        set_color(add, paint_hex, 0.7)
    else:
        nodes = [n for n in nodes
                 if "addition volume" not in n.get("_slot", "")]

    # ADU: omit the node entirely when out of scope.
    if "adu" not in scope:
        nodes = [n for n in nodes
                 if "detached ADU" not in n.get("_slot", "")]
    else:
        adu = find_node(nodes, "detached ADU")
        adu["translation"] = [-8, round(GROUND_Y + 1.5, 2), -7]

    # Trees: canopy sits on a 2 m trunk; trunk centre is ground + 1 m.
    for slot, x, z, r in (("tree canopy 1", -9, 6, 1.4),
                          ("tree canopy 2", 10, -6, 1.1)):
        canopy = find_node(nodes, slot)
        canopy["translation"] = [x, round(GROUND_Y + 2 + r * 0.7, 2), z]
    trunk = find_node(nodes, "tree trunk 1")
    trunk["translation"] = [-9, round(GROUND_Y + 1, 2), 6]

    # Lights: rectangle (VERIFIED) always; sun (UNVERIFIED) mirrors preset.
    rect = find_node(nodes, "key light")
    rect["energy"] = lighting["rect_energy"]
    rect["color"] = lighting["rect_color"]
    sun = find_node(nodes, "sun -")
    sun["energy"] = lighting["sun_energy"]
    sun["color"] = lighting["sun_color"]

    # Camera.
    cam = find_node(nodes, "camera -")
    cam["translation"] = camera["translation"]
    cam["target"] = camera["target"]

    scene = {
        "version": 2,
        "nodes": [strip_private(n) for n in nodes],
        "render": {"resolution": brief.get("render_resolution",
                                           template.get("render", {})
                                           .get("resolution", [1280, 720]))},
    }
    return scene, {
        "house_width_m": house_w, "house_depth_m": house_d,
        "house_height_m": house_h,
        "footprint_sq_ft": round(footprint_sq_ft, 1),
        "nodes": len(scene["nodes"]),
        "scope": scope,
    }


def expected_tier(scope):
    if "addition" in scope or "adu" in scope:
        return "Addition / ADU"
    if "kitchen_remodel" in scope or "bathroom_remodel" in scope \
            or "full_home" in scope:
        return "Full Home"
    return "Single Room / Space"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Intake brief JSON -> vork scene JSON (v2).")
    parser.add_argument("brief", type=Path, help="intake brief JSON file")
    parser.add_argument("-o", "--out", type=Path, default=None,
                        help="output scene JSON (default: <brief stem>-scene.json)")
    parser.add_argument("--template", type=Path,
                        default=HERE / "house-scene-template.json")
    parser.add_argument("--camera", choices=sorted(CAMERA_PRESETS))
    parser.add_argument("--lighting", choices=sorted(LIGHTING_PRESETS))
    args = parser.parse_args(argv)

    brief = json.loads(args.brief.read_text())
    if args.camera:
        brief["camera_preset"] = args.camera
    if args.lighting:
        brief["lighting_preset"] = args.lighting
    template = json.loads(args.template.read_text())

    for key in ("total_sq_ft", "address"):
        if key not in brief:
            parser.error(f"brief is missing required field {key!r}")

    scene, info = generate(brief, template)

    # Tier sanity check against the Gumroad tiers; warn, do not override.
    tier = brief.get("tier")
    price = brief.get("tier_price_usd")
    want = expected_tier(info["scope"])
    if tier and tier != want:
        print(f"WARNING: brief tier {tier!r} does not match scope-derived "
              f"tier {want!r}; check the Gumroad tier before rendering.",
              file=sys.stderr)
    if price is not None and tier in TIER_PRICES \
            and price != TIER_PRICES[tier]:
        print(f"WARNING: brief tier price ${price} does not match Gumroad "
              f"tier {tier!r} (${TIER_PRICES[tier]}).", file=sys.stderr)

    out = args.out or args.brief.with_name(
        args.brief.stem.replace("-brief", "") + "-scene.json")
    out.write_text(json.dumps(scene, indent=2) + "\n")

    for w in UNVERIFIED_WARNINGS:
        print("UNVERIFIED: " + w, file=sys.stderr)
    print(f"wrote {out} ({info['nodes']} nodes, "
          f"house {info['house_width_m']}x{info['house_depth_m']}x"
          f"{info['house_height_m']} m, "
          f"footprint {info['footprint_sq_ft']} sq ft/floor, "
          f"scope={','.join(info['scope']) or 'none'})")
    print("NOT a render: run `vork render` on a GPU machine to verify "
          "this scene (see README.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
