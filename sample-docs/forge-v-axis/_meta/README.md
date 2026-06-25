# ForgeLine Components v. Axis Industrial Audits

This case folder contains a stakeholder-facing document set for a manufacturing inspection and shipment-release dispute.

## Design goals

- look closer to a real matter file
- support chronology questions
- support contradiction analysis across witnesses and documents
- support exhibit tracing for Exhibit 7
- support unanswered-topic detection
- keep clean page or line citations for retrieval and answer grounding

## Main contradiction themes

- who first saw Exhibit 7
- whether Grant Holcomb gave verbal clearance to release Truck 6614
- whether the shipment release form existed before the truck left
- whether the defects were cosmetic or serious
- whether dock staff were clearly told to hold the truck

## Main unanswered gaps

- who gave the final approval to release Truck 6614
- whether the Grant Holcomb approval field on the release form was entered before or after departure
- what was said in the missing phone or voicemail exchanges on the morning of 2025-05-21

## Layout

- The 16 main documents live at the case root.
- `_meta/` holds `metadata.json`, this README, `reference-notes.md`, and `demo-questions.md`.
- `_retrieval/` holds generated `chunks.json` and `embeddings.npz`.

## Important note

Every document in this case folder is original and fictional.

The writing style was shaped by public legal and regulatory references, but the contents were generated for demo use only.
