# Build pipeline: blueprint (Blender + Claude Code)

Production build path for the Custom 3D Property Model, adopted 2026-11-24.
It replaces the vork backend prototype as the way a paying job is built.
The demo on austinzehnder.com stays real-time Three.js; this is the
offline path that produces the photoreal stills, the build film, and the
editable model a client pays for.

## What blueprint is

A free MIT Claude Code skill by Nyxera0x. One input (a pen sketch, a
floor plan, or 3-4 reference images) in, one Blender scene written as
Python code out, with every part its own object, stills judged against
the references, and a film of the house building itself.

- Repo: https://github.com/Nyxera0x/blueprint
- Install: `npx skills add Nyxera0x/blueprint -g -a claude-code`
- Installed copy: `~/.claude/skills/blueprint/` (see install note below)
- Three worked houses ship inside: courtyard (pen sketch, 2,444 parts),
  cliff villa (4 references), apartment (brochure floor plan).
- Each house has `build.py` (scene + stills), `film.py` (the film),
  `score.py` (action sounds), `music_plan.json` (ElevenLabs plan).
  Copy the closest one for a new house; never start from a blank file.

Install note: the install was started 2026-11-24 and was still running
after several minutes (slow network; the repo clone took 45s). The
method in this file is grounded in the skill as published
(`SKILL.md`, 94 lines, read from the repo). Confirm the skill dir
exists at `~/.claude/skills/blueprint/` before running a job, and
if the `npx skills add` run never landed, place the repo contents
there by hand and re-check.

## What you need on the build machine

- Blender 4.2 or newer on PATH as `blender` (tested on 5.2 with
  Cycles on an NVIDIA GPU; any OptiX or CUDA card works, 8 GB is
  enough with the fit-the-card steps below).
- Python 3 with `pillow` (the counter overlay) and, for reading a
  plan image, `opencv-python` and `numpy`.
- ffmpeg on PATH (or `FFMPEG=/path/to/ffmpeg`).
- Optional: `ELEVENLABS_API_KEY` for the music. Without it
  `tools/music.py` mixes the action sounds alone.
- Materials and plants are CC0 from Poly Haven. Each house fetches
  its own into `$BLUEPRINT_ASSETS` (default `~/.blueprint/polyhaven`)
  and skips what is already there:
  `python "$SKILL_DIR/houses/courtyard/fetch_assets.py"`

This workspace has ffmpeg and pillow but no Blender and no GPU.
Renders run on the GPU machine only. A consumer card is enough:
the author built everything on an RTX 2060 SUPER with 8 GB.

## The method (from SKILL.md, mapped to our pipeline)

### 1. Read the input into numbers, never into a mood

Before any geometry, write the rooms, walls, openings and furniture
down as numbers in metres. A sketch: trust its dimension labels over
its pixels (an image model draws a 14 m square 745 px wide and
670 px tall). A plan: find the scale bar, trace the wall fill, and
read doors and windows by hand on a metre grid (`grid_view.py`);
automatic opening detection puts doors across rooms.

This is the brief, extended. The intake brief gains a dimensions
table (rooms, walls, openings, furniture, in metres) and the build
is judged against that table, not against a description. Flag what
does not add up instead of guessing.

### 2. Pin the look with 3-4 references

Write image-model prompts for the views to render (one high view,
one room, one detail) and let the client generate them, or take
3-4 reference photos from the client. They decide the materials,
the light and the furniture. From then on the references decide
everything: a render is judged against them, not against taste.

Intake change this needs (not built yet): add a "3 reference
photos" upload to the intake site, alongside the plan files.

### 3. Build it the way a carpenter would

Footings, sills, joists, posts, plates, tie beams, rafters, roof
panels, cladding boards, floor boards, every tatami mat with its
edging, every shoji with every kumiko strip, the glass, the
furniture, the garden. Each one a separate object, tagged with its
stage (`K.STAGE[0] = "frame"`): the film flies them in by stage
and the counter counts them. Address repeated wings by a side and
(u, v) coordinates so one function builds all four and the hips
and valleys land on the diagonals.

This is why the delivered model is editable: move one wall and it
is still the same house, which is the thing an AI picture cannot
do. The part count is proof of craft; quote it on the product
page (the courtyard house is 2,444 parts).

### 4. Render stills next to the references and fix what differs

Low resolution first (960x540, 32 samples), the reference beside
the render, one list of differences, then fix and render again.
Stop when the list is empty. Look for things that poke through:
a beam end through a roof reads as a dot from above, a rock
through a pool floor as a stain.

This is the concrete form of the review gate's previs loop in
AUTOMATION.md Step 5/6: the difference list is the review, and
an empty list is the pass condition.

### 5. Pick the light last, and show both

Blue hour reads moody and can read gloomy; a bright day after rain
(a low sun, wet boards, a pale sky) reads open.
`build.py --look day|dusk` switches the whole scene. Deliver both
from the same camera.

### 6. Film it building itself

Open on the input: the sketch as a textured plane mapped so its
plan is the real size, a top-down camera with a long lens that
spirals down while the lens shortens (the plan keeps its size
while the perspective opens). Fly the parts in by stage in white
clay with a colour flash per system. Then one event that makes it
real (a wave of materials from the focal point, the lights coming
on), a slow hold, and a move inside. End on the reference room's
own framing.

Commands (from the courtyard example):

```
blender -b --factory-startup -P houses/courtyard/build.py -- tatami engawa corner --samples 192 --res 1920x1080
blender -b --factory-startup -P houses/courtyard/film.py -- --res 1920x1080 --samples 64
python houses/courtyard/hud.py --frames blueprint-out/courtyard/film --out blueprint-out/courtyard/silent.mp4
python tools/music.py --film blueprint-out/courtyard/silent.mp4 --score houses/courtyard/score.py --plan houses/courtyard/music_plan.json --out blueprint-out/courtyard/final.mp4
```

`film.py` resumes: frames already on disk are skipped, so a crashed
render picks up where it stopped (delete any empty placeholder
first). `--stills 0,6,13` renders single moments for checks,
`--step 3 --res 480x270 --samples 6` a quick preview of the whole
film. Check frames, not code: contact sheets every second of the
film at low resolution before the long render.

Two uses for us: a build film of the sample house as the demo
page's hero video (the conversion asset), and a build film of the
client's own house as a delivered asset. Films run a length that
is not round (18-25 s), and each house gets its own.

### 7. Fit the card

Motion blur on thousands of animated parts runs an 8 GB card out
of memory. Bake bevel modifiers into the meshes before keying
(Cycles treats a modified mesh as deforming), and use decimated
copies of heavy scanned plants (`make_tree_lod.py`: Poly Haven
conifers are 2-7 million polygons each). Full trees stay for
stills; decimated ones only for the film.

### 8. Score it on the film's clock

`film.py` writes `timeline.json` with every landing, the wave,
the lights and the dive; `score.py` puts a sound on each in its
own material (stone, hollow wood, paper, metal). Find the music
track's swell and pass `--offset` so it lands on the reveal.
Sound is polish, not core; a silent film still sells.

## Rules that cost a day each to learn

- Tone mapping: Khronos PBR Neutral. AgX turns a sunset orange
  into beige.
- Glass: thin, Transparent mixed with Glossy by Fresnel, no
  refraction. Smooth shading on an unbevelled box turns glazing
  into lenses; smooth only with a bevel and harden normals.
- Poly Haven "set" files (a row of shrubs, a heap of rocks) are
  split into single plants (`model_variants`).
- A Mix node clamps its factor by default: turn `clamp_factor`
  off for a sun disc or a halo added over a sky.
- Painted tile joints double up once a slab is cut into real
  tiles for the film: drop the painted joints there.
- The camera never faces a blank wall at close range. Coming in
  through an opening it turns round to the view in the opening,
  then pulls back into the room.
- Images in the repo: only what the person owns or CC0. A brochure
  plan stays with the person who brought it.

## Job folder (replaces the vork job folder)

- `brief.json` (the intake brief, with the dimensions table)
- `build.py` (the house, one script, every part its own object)
- `previs/*.png` (low-res stills next to references)
- `final/*.png` (full-res stills, `--look day` and `--look dusk`)
- `final/final.mp4` (the build film, where sold) and `timeline.json`
- `review.md` (the completed REVIEW-CHECKLIST.md for this job)
- `interactive-model-link.txt` (the delivered model link)
- `delivery-email.txt` (the exact email sent, for the record)

## Tier mapping (proposed, not a reprice)

The film is the pipeline's headline deliverable. Proposed home
for it is the $249 tier; prices do not change and nothing here
reprices a product. Austin decides before any tier page promises it.

- $99 Single Room / Space: interactive model link, one final still,
  brief text file.
- $179 Full Home: interactive model link, orbit plus aerial plus
  street stills (day and dusk), brief text file.
- $249 Addition / ADU / Full Home plus Addition: interactive model
  link, orbit plus aerial plus street plus backyard stills (day and
  dusk), before/after pair, build film (proposed), brief text file.

## What happened to vork

The vork backend prototype in `vork-backend/` is parked, not
deleted. No vork render has ever run anywhere; its scene fields
were never verified against a real vork install, and its prototype
scene is exterior-only. Blueprint (Blender + Cycles) is proven
photoreal, free, and ships three working houses. Do not sell a
vork render. If vork is ever revisited, it is a separate
experiment, not this pipeline.

## Claude Code vs the Claude Project

Blueprint is a Claude Code skill: the `/blueprint` command wires
into Claude Code, and the build runs there. The web Claude Project
does not run slash commands, so the prompts transfer but the
wiring does not. The build step runs in Claude Code, or the
prompts from this file are pasted into the project. This file is
the build spec Austin's project instructions can point at; the
standing "port the Claude Project instructions" item is answered
by pointing the project at this repo's pipeline docs, not by
pasting the skill in whole.

## What still needs a GPU machine

- Blender 4.2+ with Cycles on an OptiX or CUDA card (8 GB is
  enough with the fit-the-card steps). Run the courtyard example
  end to end first to prove the machine before any client job.
- `fetch_assets.py` downloads the Poly Haven CC0 assets once per
  house.
- No render has run anywhere yet. Do not sell a still or a film
  until one has rendered and passed the review gate.
