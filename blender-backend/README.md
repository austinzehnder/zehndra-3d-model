# blender-backend: deterministic generator

Turns a dimensions table (JSON) into a Blender `build.py` that builds
the house part by part, using the same method as the blueprint skill:
every part its own object, tagged with its build stage, so a film
can fly them in. Stdlib only; no Blender needed to run the generator.

This is the generator from the unattended-build spec (AUTOMATION.md,
"Unattended build"): the job runner calls it instead of asking
Claude to hand-write `build.py`. It is also usable inside the manual
workflow: Claude Code can call it instead of hand-writing `build.py`,
then refine the result.

## Files

- `generate_build.py` — the generator. Input: dimensions-table JSON.
  Output: a Blender build script.
- `SCHEMA.md` — the dimensions-table schema (v1) and validation rules.
- `sample-demo-home.json` — the demo home as a dimensions table:
  2,640 sq ft total (1,840 existing + 800 addition), 2 stories,
  kitchen + 2 bedrooms + 1 full bathroom, addition + ADU.
- `sample-demo-home-build.py` — the build script the generator
  produces from the sample table (checked in for review; the GPU
  machine can run it directly).
- `tests/run_stub.py` + `tests/stubkit/` — runs a generated build
  script against stubbed `bpy`/`bkit`/`mathutils` (no Blender),
  prints the per-stage part counts, and flags duplicate part names
  and degenerate parts.

## Usage

```sh
python3 generate_build.py sample-demo-home.json
# writes sample-demo-home-build.py next to the table

python3 generate_build.py <table.json> -o <build.py> [--slug NAME]
```

Exit codes: 0 on success; 2 on a validation failure (errors on
stderr, no output file); 1 on a usage error.

## What the generated script does

- Imports the blueprint kit (`bkit`) from `$BLUEPRINT_SKILL_DIR`
  (default `~/.claude/skills/blueprint`), sets up a Cycles scene
  (Khronos PBR Neutral), and builds the house stage by stage:
  foundation, frame, floors, walls, roof, interior, site, lights.
- Materials are procedural (`K.principled`, `K.glass`, `K.boards`
  for floor-plank seams). No Poly Haven downloads are needed.
- `--look day|dusk` switches the light, like the blueprint houses.
- Shots are computed from the lot and the house: aerial, street,
  backyard, interior. Each can be overridden on the command line
  (`--aerial_loc x,y,z` etc., as in the blueprint houses).
- Prints `built in ... s, N parts (expected N)`; `EXPECTED_PARTS`
  is a literal in the script, so a mismatch on the GPU machine
  means the kit behaved differently and is worth investigating.

Run it on the GPU machine with:

```sh
blender -b --factory-startup -P sample-demo-home-build.py -- aerial street backyard interior --look day --samples 192 --res 1920x1080
```

## Tests (no Blender, no GPU)

```sh
python3 -m py_compile generate_build.py sample-demo-home-build.py
python3 tests/run_stub.py sample-demo-home-build.py aerial street backyard interior --look day --samples 32 --res 960x540
python3 tests/run_stub.py sample-demo-home-build.py aerial --look dusk --samples 32 --res 960x540
```

The stub run executes the generated script end to end (scene setup,
materials, all eight stages, sky/sun, shots, render loop mocked)
and checks: it runs without error, the stub's part count equals
`EXPECTED_PARTS`, part counts match per stage, and there are no
duplicate part names or zero-size parts. Determinism is checked by
generating twice and diffing the outputs (byte-identical).

Sample results (2026-11-24): 1,342 parts total — foundation 15,
frame 48, floors 646, walls 189, roof 301, interior 116, site 18,
lights 9. Day and dusk runs both pass; output is byte-identical
across runs; a bad table (room outside its volume) is rejected
with exit code 2 and no output file.

## What still needs a GPU machine

- A real render: no still has rendered anywhere yet. Run the
  sample build on a GPU machine (Blender 4.2+, Cycles) and check
  the four shots against the demo before any client job.
- Poly Haven assets (real trees, plants) and the gradient sky are
  refinements for the GPU machine; the generated baseline uses
  procedural trees and a flat sky.

## Known limitations (v1)

See SCHEMA.md: no stairs, shared wall segments use the exterior
material, floor boards run in aligned pieces (not staggered), no
Poly Haven assets, flat sky. Each is a refinement for the
stills-against-references loop, not a blocker for the generator.
