# Acme Manufacturing Demo Matter

## Matter

`Acme Manufacturing v. North Ridge Inspections`

This case folder contains a richer, stakeholder-facing document set for the same sample matter used elsewhere in the repo.

The goal is to make the assistant feel much closer to a real matter file while keeping the older baseline corpus available separately for tests and learning.

## Design goals

- look closer to real legal and business records
- support chronology questions
- support contradiction analysis across witnesses and documents
- support exhibit tracing for Exhibit 12
- support unanswered-topic detection
- keep clean page or line citations for retrieval and answer grounding

## Main contradiction themes

- who first saw Exhibit 12
- whether Marcus Lee gave verbal clearance to release the shipment
- whether the shipment release form existed before the truck left
- whether the defects were cosmetic or serious
- whether dock staff were clearly told to hold the truck

## Main unanswered gaps

- who gave the final approval to release Truck 8841
- whether the Marcus Lee approval field on the release form was entered before or after departure
- what was said in the missing phone or voicemail exchanges on the morning of March 8

## Layout

- The 16 main documents live at the case root.
- `_meta/` holds `metadata.json`, this README, `reference-notes.md`, and `demo-questions.md`.
- `_retrieval/` holds generated `chunks.json` and `embeddings.npz`.

## Important note

Every document in this case folder is original and fictional.

The writing style was shaped by public legal and regulatory references, but the contents were generated for demo use only.
