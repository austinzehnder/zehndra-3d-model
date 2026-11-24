# Custom 3D Property Model

Turn a property address, scope of work, and project plans into an interactive 3D model.

By Austin Zehnder, San Francisco. Part of the Real Estate section on austinzehnder.com.

## What this is

- **Customer intake site:** a Muse web artifact (`3d-property-model-site`) with a live Three.js house preview. Customers enter address, scope, and plans, and get a structured brief to copy into the Claude project.
- **Checkout:** Gumroad product [Custom 3D Property Model](https://zehndra.gumroad.com/l/rwmwcm) — $99 Single Room / Space, $179 Full Home, $249 Addition / ADU / Full Home + Addition. Draft/unpublished as of 2026-11-05; delivery is manual by email within 3 business days where possible.
- **Build pipeline (blueprint):** `BLUEPRINT-PIPELINE.md` — the
  production build path. A free MIT Claude Code skill
  (https://github.com/Nyxera0x/blueprint) that turns a sketch, plan,
  or 3-4 reference images into a Blender scene written as code
  (every part its own object), photoreal stills judged against the
  references, and a build film. Runs in Claude Code on a GPU machine
  (Blender 4.2+, Cycles, 8 GB consumer card is enough). The vork
  prototype in `vork-backend/` is parked, not deleted; no vork
  render has ever run.
- **Site pages:** the Real Estate hub and 3D page live in `austinzehnder/austinzehnder.github.io` at `/real-estate/` and `/real-estate/3d-model/`, alongside the Home Value Estimator at `/analytics.html`.

## Workflow

1. Customer buys on Gumroad.
2. Customer submits address, scope, and plans on the intake site, using the same checkout email.
3. The brief is pulled into Claude Code, which builds the model with
   the blueprint skill (Blender stills, build film, editable model).
4. The finished interactive model + renders are delivered manually by email.

## What it is not

A custom visualization based on the plans provided. Not an architectural drawing, appraisal, or permit document. Plans, measurements, and permits remain the customer's responsibility.

## Contents

- `gumroad-draft.md` — the Gumroad product copy, tiers, and placeholder order instructions.
- `BLUEPRINT-PIPELINE.md` — the production build path (blueprint skill, Blender + Cycles).
- `blender-backend/` — deterministic generator (dimensions table to build.py), schema, sample demo-home table and build, stub test harness. See `blender-backend/README.md`.
- `AUTOMATION.md` — the pipeline (brief, build, previs, auto-QA, human review gate, final, delivery).
- `REVIEW-CHECKLIST.md` — the per-job review gate.
- `vork-backend/` — parked vork prototype (house scene template, brief-to-scene generator, customization matrix, run instructions). Do not sell a vork render.

## Status

- 2026-11-05: Gumroad draft created and verified (unpublished). Intake site built and verified. Real Estate section built locally.
- 2026-11-06: Vork backend prototype built (template + generator + matrix). No vork render has been run here — this environment has no GPU. Preview customizations on the intake site are being expanded.
- 2026-11-06: Automation-first with human review plus human delivery. See `AUTOMATION.md` for the pipeline and `REVIEW-CHECKLIST.md` for the review gate. Nothing is delivered to a paying client without an Approve from Austin plus Claude, and delivery is by email from Austin. FORMA branding is removed in favor of Zehndra.
- 2026-11-24: Blueprint adopted as the production build path (see `BLUEPRINT-PIPELINE.md`); vork parked. The build step runs in Claude Code, not the web Claude Project. Still to build: the 3-reference-photos upload on the intake, and a GPU machine to run the first render.
- 2026-11-24: Deterministic generator built (`blender-backend/generate_build.py`, local commit, not yet pushed): dimensions-table schema, sample demo-home build (1,342 parts), stub-executed without Blender. No render has run anywhere yet; the render check stays a GPU-machine step.
