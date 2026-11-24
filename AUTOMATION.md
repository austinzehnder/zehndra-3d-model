# Automation pipeline - Custom 3D Property Model

Automate as much as possible. Never deliver to a paying client without
human review and human delivery.

Principle: the machines do the repetitive work (brief, scene, previs,
checks, renders). Austin plus Claude do the judgment work (review the
final product, fix what is wrong, send it to the client). No step in
this document sends anything to a client on its own.

Branding: Zehndra. The FORMA logo that appeared in the intake artifact
is removed in favor of the Zehndra logo. Do not use FORMA branding on
the site, the Gumroad product, or the delivery email.

Product: Custom 3D Property Model, Gumroad
https://zehndra.gumroad.com/l/rwmwcm (draft/unpublished). Tiers: $99
Single Room / Space, $179 Full Home, $249 Addition / ADU / Full Home
plus Addition. Delivery within 3 business days where possible. This is
a custom visualization based on the plans provided, not architectural
drawings, an appraisal, or permit documents.

Build engine (2026-11-24): the production build path is the
blueprint skill (Blender + Cycles), documented in
BLUEPRINT-PIPELINE.md. Steps 3, 4 and 7 below are written for that
engine. The vork prototype in `vork-backend/` is parked, not
deleted; do not sell a vork render.

## Pipeline, step by step

### Step 0. Gumroad purchase (automated)

Customer buys on Gumroad. Gumroad handles payment and captures the
checkout email. The product is a digital product with placeholder
order instructions, not an instant download. No model is delivered at
checkout.

### Step 1. Trigger and job folder (automated once the webhook exists, manual until then)

A sale creates a job. The job folder is named by Gumroad order email
and date, for example `jobs/2026-11-06-smith@example.com/`.

Trigger today: manual. Austin reads the Gumroad order email, creates
the job folder, and matches it to the intake submission by email.
Trigger to build next: a Gumroad webhook (or a Gumroad sales export
check) that creates the job folder automatically when a sale lands.
Do not claim the webhook exists until it is built and tested with a
real test purchase.

Job folder contents, once the job is complete:

- `brief.json` (the intake brief, with the dimensions table)
- `build.py` (the house, one Blender script, every part its own object)
- `previs/*.png` (low-res stills next to references)
- `final/*.png` (full-res stills, day and dusk) and `final/final.mp4`
  (the build film, where sold) and `timeline.json`
- `interactive-model-link.txt` (the delivered model link)
- `review.md` (the completed REVIEW-CHECKLIST.md for this job)
- `delivery-email.txt` (the exact email sent, for the record)

### Step 2. Intake brief JSON (automated)

Customer submits the intake site with the same email used at checkout.
The site builds the live brief.

Automated validation at intake, before any render starts:

- Required fields present: property address, property type, beds,
  baths, sq ft, stories, scope of work, project plans or plan links,
  3-4 reference photos (required by the build step; the intake upload
  for them is still to be added), contact name, contact email.
- Checkout email matches the Gumroad order email for the job. If the
  emails do not match, hold the job for review. Do not guess which
  order it belongs to.
- Tier and price match: the brief tier must match one of $99 / $179 /
  $249, and the scope must match the tier (see "Tier routing" below).
  If they do not match, hold the job for review.
- Plan files listed in the brief. The intake site lists uploads in
  memory only on a static page, so the plans themselves arrive by the
  intake submission or by email. Do not claim a plan was received
  until the file or link is in the job folder.

If validation fails, the job stops here. No render runs. The failure
and the missing field go in the job log, and the job waits for human
review.

### Step 3. Numbers and build script (Claude Code + blueprint)

In Claude Code with the blueprint skill installed (`/blueprint`):

1. Read the brief, plans, and reference photos into numbers first:
   rooms, walls, openings, furniture in metres. Trust dimension
   labels over pixels; trace plan wall fill at the scale bar and
   read doors and windows by hand on a metre grid. Write the
   dimensions table into `brief.json` and flag what does not add up.
   Do not guess a dimension.
2. Copy the closest of the three shipped houses (courtyard for a
   sketch, villa for references, apartment for a brochure plan) and
   write `build.py` for this house: every part its own object,
   tagged with its stage. The references decide the materials,
   the light, and the furniture.
3. Fetch the CC0 Poly Haven assets for this house
   (`fetch_assets.py`) and run a first low-res stills pass
   (960x540, 32 samples) so Step 4 has something to judge.

Interior finishes (flooring, countertops, cabinets, fixtures) are
recorded in the brief and built as real objects in the model, not
as a separate interior pass. Do not sell a still or a film until
one has rendered and passed review.

### Step 4. Previs: stills against references (automated, GPU machine only)

On a GPU machine (Blender 4.2+ with Cycles on an OptiX or CUDA card;
8 GB is enough with the fit-the-card steps in BLUEPRINT-PIPELINE.md),
render previs first: low resolution (960x540, 32 samples), the
reference beside the render, one list of differences, then fix and
render again. Stop when the list is empty. Look for things that poke
through. Run a quick film preview too
(`--step 3 --res 480x270 --samples 6`) and check its contact sheets
before any long render.

Previs is for iteration. Fix camera and lighting here. Do not burn
final renders on a bad camera. This step cannot run in this workspace
(no GPU here) and cannot run on the static intake site. It runs on
the GPU machine only.

### Step 5. Auto-QA checks (automated, must all pass)

Run these checks on the previs output before any human review. Every
check must pass. If any check fails, the job is held. Nothing is
delivered, and no final render runs until the failure is fixed and
previs passes again.

1. File exists: every expected previs file exists in the job folder and
   is larger than zero bytes.
2. Image is not black or blank: the image has real pixel variance
   across the frame. A solid black, solid white, or near-empty frame
   fails. A render that is all one color fails.
3. Dimensions match the brief: the house in `build.py` matches the
   dimensions table in `brief.json` (rooms, walls, openings, furniture
   in metres). If the brief says 2,640 sq ft over 2 stories, the build
   must show a 1,320 sq ft per floor footprint. If it does not, the
   numbers read was wrong. Fix the brief, rebuild, re-render.
4. Tier and price match: the brief tier and price match the Gumroad
   order ($99, $179, or $249) and the scope matches the tier. A $99
   Single Room brief must not contain an addition or ADU volume. A
   $249 brief must contain the addition or ADU volume.
5. Before/after pair present (where sold): the before scene and the
   after scene exist, were rendered from the same camera preset, and
   show the same property. A before that is just the after with a
   layer hidden fails. Before is a real scene built from existing sq
   ft only, with no addition or ADU nodes.
6. Camera and lighting sanity: at least one still exists per promised
   camera preset (orbit, aerial, street, backyard, interior where
   promised), and the lighting preset in the file name matches the
   brief (day or dusk).
7. File links resolve: the interactive model link in the job folder
   opens, and every file named in the delivery draft exists in the
   job folder. A broken link fails.
8. Disclaimer present: the delivery draft contains the disclaimer that
   this is a custom visualization based on the plans provided, not
   architectural drawings, an appraisal, or permit documents, and that
   plans, measurements, and permits remain the client's responsibility.

### Step 6. Human review gate (human only, BLOCKS delivery)

No delivery moves past this gate without an Approve from Austin plus
Claude, recorded in `review.md` using `REVIEW-CHECKLIST.md`.

The gate blocks: final renders, the interactive model export, the
delivery email, and any Gumroad fulfillment message. An auto-QA pass
does not approve a job. A previs that looks right to the machine can
still be wrong for the client (wrong room, wrong addition placement,
wrong finishes), and only the human review catches that.

If review finds a problem, follow the Request changes path in
`REVIEW-CHECKLIST.md`: fix the brief or the scene, re-run previs,
re-run auto-QA, and re-review. The job does not advance on a failed
review.

### Step 7. Final render and interactive model export (automated after Approve)

Only after Approve. Full-res stills first, day and dusk from the
same camera:

```sh
blender -b --factory-startup -P build.py -- <views> --look day --samples 192 --res 1920x1080
blender -b --factory-startup -P build.py -- <views> --look dusk --samples 192 --res 1920x1080
```

Then the film, where sold (it resumes, so a crashed render picks
up where it stopped):

```sh
blender -b --factory-startup -P film.py -- --res 1920x1080 --samples 64
python hud.py --frames blueprint-out/<job>/film --out blueprint-out/<job>/silent.mp4
python tools/music.py --film blueprint-out/<job>/silent.mp4 --score score.py --plan music_plan.json --out final/final.mp4
```

Render one final still per promised camera, plus the before/after pair
from identical camera presets. Render the build film only if it was
promised for the tier. Export the interactive model link and confirm
it opens. Re-run the auto-QA file and link checks on the final files.
If a final check fails, stop. Do not deliver a failed final. Return
the job to review.

### Step 8. Human delivery by email (human only)

Austin sends the delivery email by hand. The email contains the
interactive model link, the final stills (as links or attachments),
the before/after pair where sold, the brief text file for the record,
and the disclaimer from Step 5, check 8. Austin signs it. Claude
drafts it only if Austin asks for a draft for that job.

Delivery is within 3 business days where possible, counted from the
day the intake submission and the plans are both in the job folder,
not from the Gumroad purchase alone. If the plans arrive late, the
clock starts when they arrive. Tell the client that in the delivery
email if it applies.

After sending, save the exact email text as `delivery-email.txt` in
the job folder and mark the job delivered. Do not mark a job delivered
before the email is sent.

## What is automated vs what is human-only

| Work | Who does it |
|---|---|
| Gumroad checkout and email capture | Automated (Gumroad) |
| Intake form, live brief | Automated (intake site) |
| Brief validation (required fields, email match, tier match) | Automated |
| Build script (blueprint build.py, Claude Code) | Automated |
| Blender previs and final renders, build film | Automated (GPU machine) |
| Auto-QA checks (files, non-black image, dimensions, tier, pair, links, disclaimer) | Automated |
| Job folder creation from a sale | Manual today, automated once the Gumroad webhook is built |
| Plan reading (PDFs, images, hand sketches) | Human (Austin plus Claude) |
| Human review gate (Approve / Request changes / Reject) | Human only, blocks delivery |
| Fixing a wrong scope, wrong dimensions, or wrong finishes | Human only |
| Delivery email | Human only (Austin sends it) |
| Client questions, refunds, and changes after delivery | Human only |

## What happens on auto-QA failure

1. Hold the job. Do not deliver. Do not run a final render.
2. Write the failure in the job log: which check failed, which file,
   and the expected vs actual value.
3. Route the job to human review with the failure attached.
4. Fix the brief or the scene, re-run previs, re-run auto-QA.
5. Only a full auto-QA pass plus a human Approve moves the job on.

Never auto-retry a final render to get past a failure. Never auto-send
a delivery email to clear a queue. A held job is the system working,
not the system stuck.

## Tier routing

| Tier | Price | Automation | Human review | Delivery package |
|---|---|---|---|---|
| Single Room / Space | $99 one time | Mostly auto: brief, scene, previs, auto-QA | Light review: scope matches one room, finishes match the brief, one camera still is correct | Interactive model link, one final still, brief text file |
| Full Home | $179 one time | Auto: brief, scene, previs, auto-QA | Full review: the whole REVIEW-CHECKLIST.md, all promised cameras | Interactive model link, orbit plus aerial plus street stills, brief text file |
| Addition / ADU / Full Home plus Addition | $249 one time | Auto: brief, scene, previs, auto-QA | Full review plus lot fit: the whole checklist, before/after pair, and a check that the addition or ADU volume fits the lot and the existing house | Interactive model link, orbit plus aerial plus street plus backyard stills, before/after pair, build film (proposed), brief text file |

The $99 tier is sold on the interactive model plus the brief and one
still. The $249 tier always gets the before/after pair and the lot fit
check. If a job needs more than its tier promises, stop and contact
the client before rendering the extra work.

## What still needs to go live

- Gumroad webhook (or a tested sales-export check) to create job
  folders automatically. Until then, Step 1 is manual.
- A GPU machine with Blender 4.2+ and Cycles, with the courtyard
  example run end to end once to prove the machine. No render has
  run anywhere yet.
- The 3-reference-photos upload on the intake site (the build step
  needs it).
- The intake site public URL, so the Real Estate page intake button
  can point at the live site instead of a placeholder. The intake
  artifact is still unshared.
- The Gumroad product is still draft/unpublished. Publish it only
  when Austin says to, after the review gate and the delivery email
  have been used once end to end on a test job.
