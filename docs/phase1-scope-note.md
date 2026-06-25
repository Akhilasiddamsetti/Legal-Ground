# Phase 1 Scope Note

## Important note

This is a sample Phase 1 scope note.

We are using sample choices because right now we do not have:

- a real legal matter
- a real document source
- a real attorney group
- a real list of attorney questions

That is okay.

The purpose of this file is to help us move forward and learn the process.

## What we are doing in Phase 1

In Phase 1, we are not building the AI assistant yet.

We are deciding what the first version should be about.

We are answering these simple questions:

- What is the pilot matter?
- Where will the documents come from?
- Who will use the system first?
- What questions should the assistant answer?
- What will count as success?

## Sample pilot matter

We will use this sample matter:

`Acme Manufacturing v. North Ridge Inspections`

### Simple background

This is a made-up legal matter for learning.

The dispute is about a product inspection.

The legal team wants help preparing for a deposition by finding:

- key dates
- witness statements
- inconsistencies
- exhibit references
- topics that were not fully addressed before

## Sample document source

Since we do not have a real SharePoint site or document system yet, we will use a simple local sample document set.

The document source for version 1 will be:

`sample-docs/`

This means:

- all test documents will live in one local folder
- the first version will only search documents from that folder
- later, we can replace this with SharePoint or another real system

## Sample document pack

These are the sample documents we will pretend belong to the pilot matter:

1. Complaint
2. Written discovery responses
3. Witness deposition transcript excerpt
4. Exhibit 12 inspection report
5. Email chain about the inspection
6. Internal meeting notes

We do not need perfect or complete documents right now.

We only need enough sample material to test the assistant flow later.

## Sample first user group

Since we do not have real attorneys yet, we will use a small sample user group.

For learning and prototyping, the first users will be:

- 1 mock litigation associate
- 1 mock senior attorney reviewer
- 1 builder or tester acting as the pilot admin

In plain English:

this means we are designing version 1 for a very small legal team, not for a whole firm.

## Top 10 sample user questions

These are the first questions our assistant should be able to support:

1. Create a chronology of events related to the product inspection.
2. What happened before and after Exhibit 12 was created?
3. What did the witness say about the failed inspection?
4. Which statements in the deposition conflict with the written discovery responses?
5. List all references to Exhibit 12 across the sample documents.
6. What emails mention product defects or inspection failures?
7. Which people were involved in the inspection decision?
8. What topics have already been covered in prior testimony?
9. What important topics do not appear to be fully answered yet?
10. Show the source documents for each important factual answer.

## Version 1 scope

Version 1 should do only a small set of useful things.

Version 1 will:

- work on one sample matter only
- search one local sample document folder only
- answer a small set of deposition-prep questions
- return answers with citations
- point users back to the source document
- say when there is not enough evidence

## Out of scope for version 1

To keep the first version realistic, these things are out of scope:

- supporting multiple matters
- connecting to real SharePoint or a real DMS
- serving a full law firm
- giving final legal advice
- drafting final court filings
- automatic document filing
- advanced workflow automation
- production-grade firmwide deployment

## Sample success measures

We need simple success measures, even for a sample project.

For this sample Phase 1 plan, success means:

- we have one clear sample matter
- we have one clear sample document source
- we have one clear sample user group
- we have 10 realistic user questions
- we have a clear definition of version 1 scope
- we know what is out of scope

For the later prototype, success can mean:

- the assistant answers most sample questions using only the sample documents
- the assistant includes citations for factual answers
- the assistant does not answer from made-up information
- the assistant stays inside the sample matter only

## Why this is a good starting point

This sample setup is useful because it is:

- small
- easy to understand
- easy to test
- easy to replace later with real business inputs

If we tried to use real enterprise systems before we had a clear first scope, we would get stuck too early.

## Phase 1 result

With this file, Phase 1 now has a usable starting draft.

We now have:

- a sample matter
- a sample document source
- a sample user group
- a sample question list
- a sample version 1 scope
- a sample success definition

## What should happen next

The next practical step is to create the sample document pack in `sample-docs/`.

That will help us move into the next phases later.
