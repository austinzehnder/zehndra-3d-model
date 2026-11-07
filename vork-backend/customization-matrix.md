# Customization matrix — Custom 3D Property Model

How each customer choice flows from the intake form to the two renders:
the instant **Three.js preview** on the intake site, and the photoreal
**vork final** rendered offline on a GPU machine.

Key to the "Vork field" column:
- **VERIFIED** — the field name appears in the vork README first-scene or
  glTF example (`version`, `nodes[].type`, `translation`, `geometry.std`
  sphere/grid, `geometry.radius`/`size`, `materials[].inputs.base_color` /
  `specular_roughness`, `light.shape` rectangle + `translation`/`target` /
  `energy`/`size`/`color`, `camera.translation`/`target`,
  `render.resolution`, `asset.file`).
- **UNVERIFIED** — not shown in the README excerpt. The prototype uses it
  anyway where there is no verified alternative, and flags it every run.
  Confirm with `vork help field <path>` on the GPU machine before
  promising it to a client.
- **FUTURE** — no vork field in this prototype; needs a real interior model,
  a .glb asset, or a `vork help` lookup first.

Interior dimensions (flooring, countertops, cabinets, fixtures) are
**exterior-scene only in this prototype**: the house is a solid volume
with windows and a door, not a walkable interior. An interior vork shot
needs an interior model (Blender/.glb import, README "Cozy Kitchen"
pattern) — see the "Interior" row and README.md.

| Dimension | Options (intake) | Intake field | Vork scene field it maps to | Three.js preview (today) | Vork final (this prototype) |
|---|---|---|---|---|---|
| Exterior paint / siding | Warm white, farmhouse white, craftsman brown, sage, slate, navy, custom hex | `paint_hex`, `paint_name` | `materials[].inputs.base_color` on house-body + addition nodes (VERIFIED); `specular_roughness` 0.7 | Live: paint swatches recolor the house body in the preview | Same color, but ray-traced: sun + rectangle light bounce off it, so the same hex reads warmer/cooler by lighting preset. No texture yet (siding profile is FUTURE — needs a material/texture input lookup) |
| Roofing material / color | Gable / hip / flat; charcoal, brown, slate, terracotta | `roof_type`, `roof_hex` | Roof node `base_color` (VERIFIED); `geometry.std` prism for gable, flat box slab for flat (both UNVERIFIED); hip is approximated by the gable prism and flagged | Roof control recolors / reshapes the preview roof | Photoreal roof planes with shadows; hip is NOT a true hip yet — confirm geometry before selling it |
| Flooring | White oak, walnut, tile, carpet, concrete | `flooring` | FUTURE: no interior geometry in this prototype. Planned: interior floor mesh `base_color` + `specular_roughness` (VERIFIED field names, unbuilt scene) | Not shown (exterior preview only) | Not rendered until an interior model exists. Do not sell a flooring render yet |
| Countertops | Quartz white, quartz grey, butcher block, marble | `countertops` | FUTURE: same as flooring — interior counter mesh `base_color` (VERIFIED field, unbuilt scene) | Not shown | Not rendered until an interior model exists |
| Cabinets | Flat-panel white oak, shaker white, dark walnut, sage | `cabinets` | FUTURE: interior cabinet mesh `base_color` (VERIFIED field, unbuilt scene) | Not shown | Not rendered until an interior model exists |
| Fixtures | Brushed nickel, matte black, brass, chrome | `fixtures` | FUTURE: fixture meshes need a .glb asset (`asset.file`, VERIFIED) or small `box`/`sphere` parts (box UNVERIFIED). Finish = `base_color` + low `specular_roughness` for metal | Not shown | Not rendered in this prototype |
| Lighting | Day / dusk / night + interior lamps on/off | `lighting_preset` | Rectangle light `energy` + `color` (VERIFIED): day 700 [1,0.92,0.8], dusk 350 [1,0.75,0.55], night 150 [0.85,0.9,1.0]; `sun` shape mirrors the preset (UNVERIFIED) | Preview has fixed lighting; preset does not change it today — planned | One render per preset (3 stills) or one movie with animated light; night shows window glow only if window emissive is added (UNVERIFIED — needs `material.inputs` lookup) |
| Cameras | Orbit / aerial / street / backyard / interior | `camera_preset` | `camera.translation` + `camera.target` (VERIFIED). Orbit [14,6,16], aerial [0,22,6], street [10,2,18], backyard [-12,4,-14], interior [0,2,2] target [0,2,-4] | Orbit / aerial / street / backyard views exist in the preview | One still per camera (5 stills), or a `--frame-start 0 --frame-end 47` orbit movie (animation tracks are UNVERIFIED here — see `vork help animation`) |
| Style presets | Modern / farmhouse / craftsman | `style_preset` | Palette only: modern = warm white + charcoal roof; farmhouse = white + dark brown roof; craftsman = brown siding + dark brown roof. Maps to the same `base_color` fields above (VERIFIED) | Preset recolors preview paint/roof | Same palette, photoreal; style does NOT change geometry (no porch columns, trim profiles, or window grids yet — FUTURE, needs geometry/assets) |
| Staging / furniture | None / light staging / full staging | `staging` (not in sample brief — add when the intake asks for it) | FUTURE: staged furniture as `.glb` assets (`asset.file`, VERIFIED) or simple `sphere`/`box` volumes; Cozy Kitchen is the README pattern for an imported staged scene | Not shown | Not rendered in this prototype; the cleanest next vork step after geometry is confirmed |
| Landscaping | Lawn / drought-tolerant / patio + planters | `landscaping` (not in sample brief) | Lot grid `base_color` (VERIFIED) for lawn tone; trees are `sphere` canopies (VERIFIED) + `cylinder` trunks (UNVERIFIED); patio = second grid slab (VERIFIED field, unbuilt) | Trees + lot are in the preview | Same trees, ray-traced; lawn tone shifts with lighting preset |
| Before / after | Before only / after only / side-by-side | `scope` (drives which nodes exist) | Two scene files from one brief: before = existing sq ft, no addition/ADU nodes; after = `generate_scene.py` output. Both use the same verified camera/light fields so the pair lines up | Before/after toggle exists in the preview | Before + after stills from identical camera presets, delivered as a pair; the generator omits out-of-scope nodes entirely, so "before" is a real scene, not a hidden layer |

## What the generator does per dimension

`generate_scene.py` only touches fields in the table above. It never
invents a vork field: every node it writes uses a field name from the
VERIFIED list, plus the flagged UNVERIFIED geometry/light shapes
(`box`, `prism`, `cylinder`, `sun`), which it prints to stderr on every
run. If `vork help` on the GPU machine shows a different geometry name,
change the `std` values in `house-scene-template.json` and
`generate_scene.py` in one place each — the slot names stay the same.

## Pricing tie-in

Scope drives the Gumroad tier, and the tier drives what gets rendered:

- Single Room / Space ($99) — one room; exterior scene is the house as-is,
  interior room is FUTURE work, so sell this tier on the interactive
  Three.js model + brief, not on a vork interior still, until the interior
  model exists.
- Full Home ($179) — whole-home exterior: orbit + aerial + street stills.
- Addition / ADU ($249) — exterior + addition/ADU volumes, before/after
  pair, plus a backyard camera still. This is the sample brief tier.

The generator warns (stderr, does not block) when the brief tier does not
match the scope-derived tier or the Gumroad price.
