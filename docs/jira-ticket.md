Jira Ticket Example

Ticket Type: Epic / Proof of Concept
Title: Build a Secure Matter-Specific AI Assistant for Deposition Preparation
Priority: High
Assignee: AI Solutions Specialist
Stakeholders: Litigation Practice Group, AI Solutions Manager, Information Security, Knowledge Management, Litigation Support

User Story

As a litigation attorney, I want an AI assistant that searches approved matter documents and produces source-cited deposition preparation materials, so that I can identify key facts, inconsistencies, exhibits and unanswered issues more efficiently.

Business Problem

Attorneys currently review pleadings, discovery responses, prior depositions, exhibits and correspondence manually when preparing for a deposition. This process is time-consuming, and important facts or inconsistencies may be difficult to locate across a large document set.

Proposed Solution

Develop a secure RAG-based AI assistant that:

Retrieves information only from approved matter documents.
Respects matter-level permissions and ethical walls.
Generates answers grounded in source documents.
Provides document, page and transcript-line citations.
Helps attorneys create chronologies, identify inconsistent statements and organize deposition topics.
Functional Requirements
Users must authenticate using the firm’s Microsoft identity system.
The assistant must retrieve documents from an approved SharePoint, DMS or matter workspace.
Users must only access documents they are authorized to view.
The assistant must support questions such as:
“Create a chronology of events related to the product inspection.”
“Identify inconsistencies between the witness’s deposition and written discovery responses.”
“List statements related to Exhibit 12.”
“Which topics have not been addressed in previous testimony?”
Every factual answer must include a source citation.
The assistant must state when sufficient supporting information cannot be found.
Users must be able to open the original source document from the citation.
Prompts and responses must be logged according to firm security and retention policies.
Technical Approach
Model: Azure OpenAI or another approved enterprise model
Orchestration: Semantic Kernel or LangChain
Interface: Microsoft Copilot Studio, SharePoint or a lightweight web application
Authentication: Microsoft Entra ID
Data Access: Microsoft Graph, SharePoint API or approved DMS connector
Retrieval: Hybrid keyword and vector search
Automation: Power Automate where appropriate
Evaluation: Attorney-reviewed test dataset
Acceptance Criteria
 The assistant retrieves information only from the approved pilot matter.
 Unauthorized users cannot access the matter or its indexed content.
 At least 90% of factual test answers are supported by the cited source.
 At least 95% of generated citations point to the correct document and relevant passage.
 The assistant does not fabricate an answer when supporting information is unavailable.
 Personally identifiable and privileged information remains within approved systems.
 Prompt-injection tests do not allow documents or users to override system instructions.
 Five pilot attorneys complete user-acceptance testing.
 Pilot users rate the tool at least 4 out of 5 for usefulness.
 The pilot demonstrates a measurable reduction in deposition-preparation time.
 Technical documentation, a user guide and an operational runbook are completed.
 The AI Solutions Manager approves a productionization recommendation.
Subtasks
Conduct workflow discovery
Interview litigation attorneys.
Document the current deposition-preparation process.
Identify pain points and success metrics.
Complete security and governance review
Confirm client authorization for AI use.
Review matter permissions, retention rules and data restrictions.
Obtain approval for the selected model and hosting environment.
Prepare the document collection
Identify approved pleadings, transcripts, exhibits and discovery responses.
Extract text and metadata.
Remove duplicate or unsupported files.
Build the retrieval pipeline
Define chunking and metadata strategies.
Generate embeddings.
Configure vector and keyword search.
Apply matter-level access controls.
Develop the AI assistant
Create system instructions and prompts.
Implement retrieval and response generation.
Add citations and source-document links.
Add “insufficient evidence” behavior.
Create the evaluation dataset
Ask attorneys to prepare representative questions.
Document expected answers and supporting sources.
Include difficult, ambiguous and unanswerable questions.
Test the solution
Measure answer accuracy, citation correctness and completeness.
Test unauthorized access and information leakage.
Test prompt injection, PII handling and hallucinations.
Record failure cases and remediation steps.
Run the pilot
Deploy to a limited attorney group.
Provide training.
Collect usage data and qualitative feedback.
Document and report results
Create technical documentation, user instructions and support runbooks.
Report time saved, adoption, accuracy, risks and lessons learned.
Recommend productionization, revision or discontinuation.
Out of Scope
Providing final legal advice without attorney review
Automatically filing documents with a court
Accessing documents outside the approved pilot matter
Training a new foundation model
Deploying the solution firmwide during the initial proof of concept
Risks
Incorrect or unsupported answers
Inaccurate citations
Unauthorized access to client documents
Client restrictions on generative AI
Poor-quality OCR or document extraction
Low attorney adoption
Excessive model or search costs
Overreliance on AI output without human review
Definition of Done

The ticket is complete when the assistant has passed technical, security and attorney acceptance testing; pilot results and known limitations are documented; training and runbooks are delivered; and the AI Solutions Manager has received a supported recommendation on whether the solution should move into production.
