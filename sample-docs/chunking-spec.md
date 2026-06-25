# Retrieval Chunking Spec

## Purpose

This file explains how the sample documents are prepared for retrieval.

The goal is simple:

- split documents into useful search units
- keep citation details attached to each unit
- make later retrieval and answer generation easier

## Output file

The retrieval-ready output is:

- `sample-docs/chunks.json`

## Chunking rules

### Standard page-based documents

These documents are chunked one page at a time:

- `complaint.md`
- `discovery-responses.md`
- `exhibit-12-inspection-report.md`
- `internal-meeting-notes.md`

Rule:

- one `## Page X` section becomes one chunk

### Deposition transcript

The deposition transcript is chunked by the explicit page-and-line block.

Rule:

- one `### Page X, Lines Y-Z` block becomes one chunk

This keeps transcript citations specific.

### Email chain

The email chain is chunked one email at a time.

Rule:

- one `### Email N` section becomes one chunk

This is better than page-based chunking because each email is its own retrieval unit.

## Metadata attached to each chunk

Each chunk carries:

- `chunk_id`
- `matter_id`
- `matter_name`
- `doc_id`
- `doc_title`
- `doc_type`
- `source_path`
- `source_kind`
- `created_date`
- `chunk_index`
- `chunk_type`
- `page_number`
- `page_marker`
- `line_range`
- `section_title`
- `citation_label`
- `citation`
- `participants`
- `tags`
- `access_scope`
- `related_docs`
- `exhibit_number`
- `text`
- `search_text`

Email chunks also carry:

- `email_number`
- `email_date`
- `email_from`
- `email_to`
- `email_cc`
- `email_subject`

## Citation rules

### Standard documents

Use:

- `Document Label, Page X`

Example:

- `Complaint, Page 2`

### Transcript

Use:

- `Document Label, Page X, Lines Y-Z`

Example:

- `Daniel Price Deposition, Page 13, Lines 1-17`

### Email chain

Use:

- `Document Label, Page X, Email N`

Example:

- `Inspection Email Chain, Page 3, Email 6`

## Why this shape is useful

This shape helps later steps because:

- retrieval can search smaller units instead of full files
- answers can cite exact pages or transcript lines
- comparison logic can detect contradictions across chunks
- access rules stay attached to the chunk data
