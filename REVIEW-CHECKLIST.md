# Human review checklist - Custom 3D Property Model

Use this checklist for every job before delivery. Austin plus Claude
review the final product together. No delivery moves without an
Approve recorded at the bottom of this file for that job.

Copy this file into the job folder as `review.md` and check each item
there. Do not reuse one review for another job. A check is either
done and correct, or it is not done. There is no "close enough" for a
paying client.

Job: ____________________
Client name: ____________________
Client email: ____________________
Property address: ____________________
Gumroad order email: ____________________
Tier: $99 Single Room / $179 Full Home / $249 Addition / ADU
Review date: ____________________
Reviewers: Austin plus Claude

## 1. Dimensions vs plans

- [ ] Total sq ft in the brief matches the plans.
- [ ] Existing sq ft and added sq ft add up to the total sq ft.
- [ ] Stories in the brief match the plans.
- [ ] Footprint in the scene matches the brief (total sq ft divided
      by stories, converted to meters, as in
      `vork-backend/README.md` "Verified mapping").
- [ ] Beds and baths in the brief match the plans.
- [ ] Addition or ADU size in the scene matches the plans. If the
      plans say 800 sq ft, the scene shows 800 sq ft, not a guess.

## 2. Scope completeness

- [ ] Every scope item the client paid for is in the model. Nothing
      paid for is missing.
- [ ] No scope item the client did not pay for is in the model.
- [ ] The tier matches the scope: $99 is one room or one space, $179
      is a full home, $249 is an addition, an ADU, or a full home plus
      an addition.
- [ ] If the scope does not fit the tier, the job was stopped and the
      client was contacted before any render ran.

## 3. Materials and finishes match

- [ ] Exterior paint or siding color in the renders matches the
      brief hex. The same hex reads warmer or cooler by lighting
      preset, but the color choice itself is correct.
- [ ] Roof type (gable, hip, flat) and roof color match the brief.
- [ ] Style preset (modern, farmhouse, craftsman) matches the brief
      palette.
- [ ] Flooring, countertops, cabinets, and fixtures in the brief are
      recorded correctly, even where the current prototype does not
      render interiors. Do not claim an interior render shows them
      until an interior model exists and has rendered once.
- [ ] No finish was swapped for a default without noting it in the
      review and telling the client.

## 4. Lighting and camera sanity

- [ ] Lighting preset (day, dusk, night) matches what was promised
      and looks right in the stills. Night stills show window glow
      only if window glow was actually rendered, not assumed.
- [ ] Every promised camera still exists: orbit, aerial, street,
      backyard, interior where promised.
- [ ] No still is black, blank, or washed out. No still is cropped
      so the house is cut off.
- [ ] The camera target is the house, not the lot edge or empty sky.

## 5. Before / after correctness (Addition / ADU tier, and any job that promises it)

- [ ] The before still and the after still use the same camera preset
      and show the same property, so the pair lines up.
- [ ] The before still shows the existing house only, with no
      addition or ADU volume in it.
- [ ] The after still shows the addition or ADU volume in the right
      place, at the right size, attached to the right side of the
      house.
- [ ] The addition or ADU fits the lot and does not overlap the
      existing house in a way the plans do not show.

## 6. No missing walls or rooms

- [ ] The house has no missing wall, missing roof, or floating
      volume in any delivered still.
- [ ] The addition and the ADU, where sold, are present in every
      after still. Nothing promised is missing from one angle and
      present in another.
- [ ] Windows and the door are present and in the right places. No
      window floats off a wall.
- [ ] Trees, driveway, and lot are present where promised, and do
      not block the house in the main orbit still.

## 7. File links work

- [ ] The interactive model link opens in a browser and shows the
      right property.
- [ ] Every final still in the delivery package opens and is the
      final render, not a previs file.
- [ ] Every file named in the delivery email exists in the job folder.
- [ ] The brief text file in the package matches the brief that was
      reviewed, not an earlier draft.

## 8. Client name, address, and email correct

- [ ] Client name in the delivery email is spelled correctly.
- [ ] Property address in the delivery email and in the brief matches
      the plans and the Gumroad order.
- [ ] Delivery email address matches the Gumroad checkout email and
      the intake email. If they differ, the difference was checked
      with the client and noted here.
- [ ] Tier and price in the delivery email match the Gumroad order.

## 9. Disclaimer present

- [ ] The delivery email contains the disclaimer: this is a custom
      visualization based on the plans provided, not architectural
      drawings, an appraisal, or permit documents, and plans,
      measurements, and permits remain the client's responsibility.
- [ ] No wording in the email promises an appraisal, a permit
      drawing, or a construction document.

## Decision

Check one. Record the decision, the reason, and the date in the job
folder as `review.md`.

### Approve

- [ ] Approve. All checks above pass. Delivery may proceed (final
      render, then human delivery by email, per `AUTOMATION.md`
      Step 7 and Step 8).

Approved by: ____________________ Date: ____________________

### Request changes

- [ ] Request changes. Delivery is blocked. List exactly what must
      change, who fixes it, and what must be re-checked:

  1. ____________________
  2. ____________________
  3. ____________________

  After the fix: re-run previs, re-run auto-QA, and complete a fresh
  review with this checklist. Do not reuse the old Approve. The job
  does not advance on a failed review.

### Reject

- [ ] Reject. Do not deliver. Reason (for example: plans unreadable,
      scope does not fit the lot, client asked for work outside what
      was sold):

  ____________________

  Next step: contact the client, explain what is needed, and agree on
  a fix, a different tier, or a refund before any further work. Do
  not deliver a partial model to clear the job.

## Notes

Use this space for anything the checklist did not cover: a plan detail
that was ambiguous, a finish that was swapped with the client's
agreement, a camera that was changed on purpose, or a warning from
`generate_scene.py` that was checked and cleared.

____________________
____________________
____________________
