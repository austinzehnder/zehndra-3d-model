# Custom 3D Property Model

Turn a property address, scope of work, and project plans into an interactive 3D model.

By Austin Zehnder, San Francisco. Part of the Real Estate section on austinzehnder.com.

## What this is

- **Customer intake site:** a Muse web artifact (`3d-property-model-site`) with a live Three.js house preview. Customers enter address, scope, and plans, and get a structured brief to copy into the Claude project.
- **Checkout:** Gumroad product [Custom 3D Property Model](https://zehndra.gumroad.com/l/rwmwcm) — $99 Single Room / Space, $179 Full Home, $249 Addition / ADU / Full Home + Addition. Draft/unpublished as of 2026-11-05; delivery is manual by email within 3 business days where possible.
- **Render backend (vork):** `vork-backend/` — a prototype that turns an intake brief into a vork scene JSON for photorealistic stills and flythroughs. Vork is a headless GPU renderer for agents (https://github.com/voyager-so/vork), research preview 0.1.0. It needs a GPU machine to run; see `vork-backend/README.md`.
- **Site pages:** the Real Estate hub and 3D page live in `austinzehnder/austinzehnder.github.io` at `/real-estate/` and `/real-estate/3d-model/`, alongside the Home Value Estimator at `/analytics.html`.

## Workflow

1. Customer buys on Gumroad.
2. Customer submits address, scope, and plans on the intake site, using the same checkout email.
3. The brief is pulled into the Claude project, which builds the model (and, with vork, the photoreal renders).
4. The finished interactive model + renders are delivered manually by email.

## What it is not

A custom visualization based on the plans provided. Not an architectural drawing, appraisal, or permit document. Plans, measurements, and permits remain the customer's responsibility.

## Contents

- `gumroad-draft.md` — the Gumroad product copy, tiers, and placeholder order instructions.
- `vork-backend/` — house scene template, brief-to-scene generator, customization matrix, and run instructions.

## Status

- 2026-11-05: Gumroad draft created and verified (unpublished). Intake site built and verified. Real Estate section built locally.
- 2026-11-06: Vork backend prototype built (template + generator + matrix). No vork render has been run here — this environment has no GPU. Preview customizations on the intake site are being expanded.
