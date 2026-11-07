# Vork backend prototype — Custom 3D Property Model

Photoreal render backend for the Custom 3D Property Model. The intake
site already gives the customer an instant interactive Three.js preview.
This prototype adds the offline step that turns the same intake brief
into photoreal stills (and, later, a flythrough movie) with
[vork](https://github.com/voyager-so/vork), a headless 3D/VFX engine
built for agents.

**Status: prototype, render UNTESTED.** The scene JSON generation is
verified end to end on this machine (brief -> scene, parses as JSON,
mapping checked). No vork render has run anywhere yet, because vork
needs a GPU and this VM has none. Do not tell a client a render works
until it has run on a GPU machine (see "Verify on a GPU machine").

## Automation and review gate

This prototype is one step in an automated pipeline, not a delivery
tool on its own. See `../AUTOMATION.md` for the full pipeline:
Gumroad purchase, brief, scene generation, vork previs, auto-QA
checks, then a human review gate that blocks delivery until Austin
plus Claude approve using `../REVIEW-CHECKLIST.md`. No render is
delivered to a client without that Approve, and delivery itself is
human, by email. Automate the repetitive work, keep the judgment work
human.

## Files

| File | What it does |
|---|---|
| `house-scene-template.json` | Vork v2 scene template for a single-family house: lot grid, driveway, house body, gable roof, windows, door, addition volume, detached ADU, trees, driveway, rectangle + sun lights, camera. `_meta` lists every VERIFIED vs UNVERIFIED field; `_slots` maps each template value to an intake field. Template-only keys start with `_` and are stripped by the generator. |
| `generate_scene.py` | Stdlib-only Python. Loads the template, substitutes intake values (footprint from sq ft/stories, paint/roof hex to RGB, scope toggles nodes on/off, lighting + camera presets), strips `_` keys, writes a clean vork scene JSON. Prints UNVERIFIED-field warnings to stderr on every run and a tier sanity check against the $99/$179/$249 Gumroad tiers. |
| `sample-brief.json` | Sample intake brief: 1,840 sq ft existing + 800 sq ft addition = 2,640 sq ft total, 2 stories, 3 bed / 2 bath, Addition/ADU scope, $249 tier. Address is a SAMPLE, not a real client. |
| `sample-scene.json` | Generated from `sample-brief.json` by running the script (see "Verified mapping" below). The reference output; regenerate it after any template change. |
| `customization-matrix.md` | Full customization matrix: every dimension, its options, the intake field, the vork scene field it maps to, and what the Three.js preview vs the vork final does. |
| `README.md` | This file. |

## How the Claude project uses this

1. Customer buys on Gumroad (draft product: `zehndra.gumroad.com/l/rwmwcm`,
   $99 / $179 / $249) and submits the intake site with the same email.
2. You (or the Claude project) copy their intake into a brief JSON with
   the same fields as `sample-brief.json`: `address`, `beds`, `baths`,
   `existing_sq_ft`, `added_sq_ft`, `total_sq_ft`, `stories`, `scope`
   (list, e.g. `["addition", "adu", "kitchen_remodel"]`), `paint_hex`,
   `roof_type`, `roof_hex`, `style_preset`, `lighting_preset`,
   `camera_preset`, `tier`, `tier_price_usd`, plus the interior choices
   (`flooring`, `countertops`, `cabinets`) for the record — the current
   generator records them in the brief but does not render interiors yet.
3. Run the generator on the GPU machine:
   `python3 generate_scene.py <client>-brief.json -o <client>-scene.json`
   Read the stderr warnings. If a warning names a field `vork help`
   shows is wrong, fix the `std` / `shape` value in the template and
   generator, regenerate, and re-run.
4. Render previs, inspect, then final (below). Fix camera/light first;
   do not burn final renders on a bad camera.
5. Deliver the package (below) by email, as today.

## Install vork

From the vork repo README (release 0.1.0). Keep the whole install
folder together — Slang, OIDN, libraries, examples, SDKs and licence
texts are runtime companions to the binary.

### Mac (Apple Silicon)

- Apple Silicon with Metal; macOS 26 for the bundled Slang toolchain.
  Older macOS versions are unqualified; Intel Macs are unsupported.
- In Terminal:
  ```sh
  curl -fL https://github.com/voyager-so/vork/releases/latest/download/install.sh -o /tmp/vork-install.sh
  sh /tmp/vork-install.sh
  export PATH="$HOME/.local/bin:$PATH"
  vork --version
  vork help
  ```
- The installer verifies SHA256SUMS, installs under
  `$HOME/.local/lib/vork`, runs `vork setup`, and adds PATH to your
  shell startup files. MP4 uses VideoToolbox without ffmpeg.

### Linux (NVIDIA GPU)

- x64, Ubuntu 22.04+ (glibc 2.35+, libstdc++ with `GLIBCXX_3.4.30`), a
  recent NVIDIA GPU **with hardware ray-tracing Vulkan driver**. A100 /
  H100 / H200 / B200 / B300 lack the required hardware ray tracing;
  recency alone does not make a GPU suitable. Older GPUs and software
  Vulkan adapters are unsupported.
- Install the NVIDIA driver first, then on Ubuntu 22.04+:
  ```sh
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl tar libvulkan1 libgomp1 ffmpeg
  curl -fL https://github.com/voyager-so/vork/releases/latest/download/install.sh -o /tmp/vork-install.sh
  sh /tmp/vork-install.sh
  export PATH="$HOME/.local/bin:$PATH"
  vork --version
  vork help
  ```
- Linux MP4 needs ffmpeg even with NVENC, because ffmpeg muxes the stream.
- `vork setup` prints its report, then compiles for up to about
  3 minutes with no output until `Shader setup completed` — that is not
  a hang. Run `vork setup` again after upgrading or changing GPU drivers.

### First smoke test (do this before any client scene)

```sh
# from the README first-scene example
vork render shot.json --profile std/previs --out preview.png
```

Then run the field checks this prototype depends on, and record what
`vork help` actually says — this is the step that clears the UNVERIFIED
flags:

```sh
vork help field geometry
vork help field light.shape
vork help field material.inputs
vork help limits
```

If `box` / `prism` / `cylinder` / `sun` are not valid values, update
`house-scene-template.json` + `generate_scene.py` to the real values
(or swap the house nodes for a `.glb` asset — README asset example:
`{"type": "asset", "file": "model.glb"}`) and regenerate
`sample-scene.json`.

## Render: previs, then final

```sh
cd vork-backend
python3 generate_scene.py sample-brief.json -o sample-scene.json

# Previs: fast iteration. Refine camera and lighting here.
vork render sample-scene.json --profile std/previs --out preview.png

# Final: default delivery profile (8 samples, OIDN denoise).
vork render sample-scene.json --profile std/final --out final.png

# More cameras: regenerate per preset, or render the same scene with
# a different camera via --camera (generator flag) and re-render.
python3 generate_scene.py sample-brief.json --camera aerial -o scene-aerial.json
vork render scene-aerial.json --profile std/final --out final-aerial.png

# A movie (once animation tracks are worked out — see limits):
# vork render sample-scene.json --profile std/final --frame-start 0 --frame-end 47 --out clip.mp4
```

Profiles (README): `std/previs` to iterate, `std/draft` for 4 samples,
`std/final` for the default delivery profile, `std/path` for path
transport. Final approximates indirect lighting and can darken
interiors; more samples do not restore omitted transport — try `path`
and inspect. `--set samples=32` helps fine facades; `--set
denoise=false` turns OIDN off. The first render of a scene with new
programs can compile for several minutes with no output — do not kill
it or give it a short timeout.

## Verified mapping (sample brief -> sample scene)

Run on this machine, 2026-11-06. No GPU, no vork install, no render —
only the Python generation step:

- Brief: 2,640 total sq ft, 2 stories, +800 addition, scope
  addition/adu/kitchen_remodel, $249 tier.
- Footprint: 2,640 / 2 = 1,320 sq ft per floor; side sqrt(1,320) =
  36.33 ft = 11.07 m wide, 9.41 m deep, 6.0 m high. Scene shows exactly
  that on the house-body node.
- Addition: 800 sq ft -> 8.62 x 7.33 x 3.0 m, placed at x = 9.84
  (house half-width + addition half-width).
- ADU node present (6 x 3 x 5 m, detached at [-8, 0.5, -7]).
- Paint #D8D2C4 -> base_color [0.847, 0.824, 0.769]; roof #404045 ->
  [0.251, 0.251, 0.271]. Both verified in the output JSON.
- Output: `{"version": 2, "nodes": [...15 nodes...],
  "render": {"resolution": [1280, 720]}}`, parses as JSON, zero keys
  starting with `_` left in the scene.
- Edge cases run in /tmp and passed: a no-addition/no-ADU brief drops
  to 13 nodes; `--roof flat` replaces the prism with a 0.3 m box slab;
  `--lighting night` sets rectangle energy 150 and sun 0;
  `--camera aerial` sets camera translation [0, 22, 6].

## Delivery package to the client

- The interactive model link (existing Three.js delivery), unchanged.
- Vork stills: orbit + aerial + street + backyard at `std/final`
  (1920x1080), plus a before/after pair from identical camera presets.
- Optional: a 48-frame orbit movie (`--frame-start 0 --frame-end 47`)
  once animation is verified.
- The brief text file (the generator input) for the record.
- The existing disclaimer stays: a custom visualization based on the
  plans provided, not architectural drawings, an appraisal, or permit
  documents. Plans, measurements, and permits remain the client's
  responsibility.

## Honest limits

- **Research preview 0.1.0.** Created 2026-11-05, 4 commits, license
  "Other (NOASSERTION)". Source-available and free during the preview.
  No stability, pricing, or support promise. Read `LICENSE` in the repo
  before using renders commercially.
- **Fog and participating volumes are ignored with warnings.** Large
  scenes and dense transparency can fail, including on Mac; reducing
  resolution does not necessarily fix them. Some heavy interiors work
  with `std/path` when the default hybrid profile fails.
- **First-use shader compilation is slow.** `vork setup` and the first
  render of new programs can compile for minutes with no output.
- **At 4/8 samples, fine facades can lose detail** and defocus can show
  stepped/grainy edges. Try `--set samples=32` for those shots.
- **Interiors are not built in this prototype.** Flooring,
  countertops, cabinets, and fixtures are recorded in the brief and
  listed in the matrix, but the scene is exterior-only. Do not sell a
  vork interior render until an interior model (Blender/.glb import)
  exists and has rendered once.
- **No GPU here, render untested.** This VM has no NVIDIA GPU
  (`nvidia-smi` not found, no `/dev/dri`). Everything after
  `generate_scene.py` is untested until a Mac (Apple Silicon) or
  NVIDIA Linux GPU machine runs `vork render` and a human inspects
  the PNG.
