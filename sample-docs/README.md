# Sample Document Index

This folder now has three purposes:

- a professional six-case demo library under `sample-docs/<matter-id>/`
- temporary root-level compatibility files for the older baseline corpus

## Professional Demo Library

Use these folders for demos:

- `sample-docs/acme-v-northridge/`
- `sample-docs/beacon-v-summit/`
- `sample-docs/forge-v-axis/`
- `sample-docs/harbor-v-ironcrest/`
- `sample-docs/redcliff-v-sterling/`
- `sample-docs/valewood-v-triton/`

Inside each case folder:

- the 16 main documents live at the case root
- `_meta/` contains `metadata.json`, `README.md`, `reference-notes.md`, and `demo-questions.md`
- `_retrieval/` contains `chunks.json` and `embeddings.npz`

The web app now treats these case folders as the normal professional demo runtime.

## Archived Baseline Pack

The original 6-document learning corpus is archived here:

- `sample-docs/_archive/acme-v-northridge-baseline/`

It is kept for:

- regression tests
- retrieval baseline continuity
- older learning steps in the repo

`_archive/` is excluded from the normal multi-case demo runtime.

## Temporary Compatibility Paths

The following root-level files still exist for backward compatibility:

- `sample-docs/metadata.json`
- `sample-docs/chunks.json`
- `sample-docs/embeddings.npz`

Those compatibility files still back the current default tests and evaluation harness.

## Shared Notes

- `chunking-spec.md` is still shared at the top level because it describes the general retrieval format, not one specific case.
- All content under `sample-docs/` is fictional and for demo or learning use only.
