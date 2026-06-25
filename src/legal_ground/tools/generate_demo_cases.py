from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import numpy as np

from legal_ground import config
from legal_ground.retrieval.corpus_layout import case_chunks_path, case_embeddings_path
from legal_ground.retrieval.embeddings import SentenceTransformerEmbedder
from legal_ground.tools.build_chunks import build_chunks

ROOT = config.REPO_ROOT
SAMPLE_DOCS = config.DEFAULT_CORPUS_DIR
ROLES = ["pilot_user", "pilot_reviewer", "pilot_admin"]
REFERENCE_NOTES = dedent(
    """\
    # Reference Notes

    These demo documents are original. They were not copied from the sources below.

    The sources were used only to study tone, structure, and expected sections for pleadings, discovery, depositions, and inspection-style records.

    ## Core legal style references

    - SEC complaint format reference:
      `https://www.sec.gov/litigation/complaints/2018/comp-pr2018-41-theranos-holmes.pdf`
    - SEC press release style reference:
      `https://www.sec.gov/newsroom/press-releases/2018-41`
    - FRCP Rule 8 pleading structure:
      `https://www.law.cornell.edu/rules/frcp/rule_8`
    - FRCP Rule 30 deposition structure:
      `https://www.law.cornell.edu/rules/frcp/rule_30`
    - FRCP Rule 33 interrogatories:
      `https://www.law.cornell.edu/rules/frcp/rule_33`
    - FRCP Rule 34 production requests:
      `https://www.law.cornell.edu/rules/frcp/rule_34`

    ## Inspection and quality-record style references

    - Form FDA 483 overview:
      `https://en.wikipedia.org/wiki/Form_FDA_483`
    - FDA warning-letter overview:
      `https://en.wikipedia.org/wiki/FDA_warning_letter`

    ## How the references influenced this pack

    - `complaint.md` and `answer-and-affirmative-defenses.md`
      Formal caption, numbered allegations, and relief or defense sections were modeled after public pleading structure.
    - `interrogatories-and-responses.md` and `requests-for-production-and-responses.md`
      Numbered request-and-response formatting follows common federal discovery style.
    - `deposition-*.md`
      Page-and-line formatting follows public deposition transcript conventions.
    - inspection, nonconformance, and corrective-action records
      These use structured headers, findings, disposition, and corrective-action sections inspired by public inspection and compliance records.

    ## Reminder

    This folder is for demo and POC use only.
    """
)


@dataclass(frozen=True)
class CaseData:
    matter_id: str
    matter_name: str
    plaintiff: str
    defendant: str
    product: str
    lot_id: str
    truck_id: str
    customer: str
    plant: str
    exhibit_number: int
    inspect_date: str
    ship_date: str
    meeting_date: str
    reject_date: str
    report_number: str
    ncr_number: str
    form_id: str
    carrier: str
    driver: str
    plant_manager: str
    quality_director: str
    ops_vp: str
    dock_supervisor: str
    account_manager: str
    inspector: str
    compliance_manager: str
    defect_primary: str
    defect_secondary: str
    defect_tertiary: str
    defect_cosmetic: str
    customer_pressure: str
    screen_form_phrase: str

    @property
    def inspector_last_name(self) -> str:
        return self.inspector.split()[-1]

    @property
    def exhibit_doc_id(self) -> str:
        return f"exhibit-{self.exhibit_number}-inspection-report"

    @property
    def exhibit_filename(self) -> str:
        return f"exhibit-{self.exhibit_number}-inspection-report.md"

    @property
    def plaintiff_short(self) -> str:
        return self.plaintiff.split()[0]

    @property
    def defendant_short(self) -> str:
        return self.defendant.split()[0]

    @property
    def deposition_pm_doc_id(self) -> str:
        first, last = self.plant_manager.lower().split()
        return f"deposition-{first}-{last}"

    @property
    def deposition_quality_doc_id(self) -> str:
        first, last = self.quality_director.lower().split()
        return f"deposition-{first}-{last}"

    @property
    def deposition_dock_doc_id(self) -> str:
        first, last = self.dock_supervisor.lower().split()
        return f"deposition-{first}-{last}"


CASES = [
    CaseData(
        matter_id="beacon-v-summit",
        matter_name="Beacon Process Controls v. Summit Verification Services",
        plaintiff="Beacon Process Controls, Inc.",
        defendant="Summit Verification Services, LLC",
        product="hydraulic control valves",
        lot_id="BX-318",
        truck_id="7721",
        customer="Riverside Power Systems",
        plant="Beacon Plant 2",
        exhibit_number=18,
        inspect_date="2025-04-14",
        ship_date="2025-04-15",
        meeting_date="2025-04-17",
        reject_date="2025-04-18",
        report_number="SV-BX318-041425",
        ncr_number="NCR-25-0417",
        form_id="SRF-7721",
        carrier="Lakefront Freight",
        driver="Joel Sandoval",
        plant_manager="Lena Ortiz",
        quality_director="Priya Shah",
        ops_vp="Evan Brooks",
        dock_supervisor="Maya Chen",
        account_manager="Colin Reeves",
        inspector="Aaron Bell",
        compliance_manager="Tessa Monroe",
        defect_primary="damaged spool seals",
        defect_secondary="bronze particulate in the valve bodies",
        defect_tertiary="pressure-port bore drift outside customer tolerance",
        defect_cosmetic="light exterior scoring",
        customer_pressure="Riverside Power warned that a line start would slip if Truck 7721 missed the morning slot.",
        screen_form_phrase="a release screen showing Evan Brooks in the approver field",
    ),
    CaseData(
        matter_id="forge-v-axis",
        matter_name="ForgeLine Components v. Axis Industrial Audits",
        plaintiff="ForgeLine Components, Inc.",
        defendant="Axis Industrial Audits, LLC",
        product="industrial bearing cartridges",
        lot_id="FC-902",
        truck_id="6614",
        customer="Meridian Mining Equipment",
        plant="ForgeLine Plant 5",
        exhibit_number=7,
        inspect_date="2025-05-20",
        ship_date="2025-05-21",
        meeting_date="2025-05-23",
        reject_date="2025-05-26",
        report_number="AA-FC902-052025",
        ncr_number="NCR-25-0523",
        form_id="SRF-6614",
        carrier="High Plains Logistics",
        driver="Marco Silva",
        plant_manager="Kyle Mercer",
        quality_director="Anita Desai",
        ops_vp="Grant Holcomb",
        dock_supervisor="Sierra Vaughn",
        account_manager="Derek Cole",
        inspector="Lucia Ramos",
        compliance_manager="Naomi Price",
        defect_primary="race pitting on sampled bearing surfaces",
        defect_secondary="metallic debris in the grease pack",
        defect_tertiary="preload measurements outside specification",
        defect_cosmetic="surface discoloration on the outer housings",
        customer_pressure="Meridian Mining warned that an equipment build would stop without the scheduled delivery.",
        screen_form_phrase="a release printout listing Grant Holcomb as the operations approver",
    ),
    CaseData(
        matter_id="harbor-v-ironcrest",
        matter_name="Harbor Fluid Systems v. Ironcrest Inspection Group",
        plaintiff="Harbor Fluid Systems, Inc.",
        defendant="Ironcrest Inspection Group, LLC",
        product="duplex pump housings",
        lot_id="HF-144",
        truck_id="5932",
        customer="Delta Marine Equipment",
        plant="Harbor Fluid Plant 1",
        exhibit_number=21,
        inspect_date="2025-06-12",
        ship_date="2025-06-13",
        meeting_date="2025-06-16",
        reject_date="2025-06-17",
        report_number="IIG-HF144-061225",
        ncr_number="NCR-25-0616",
        form_id="SRF-5932",
        carrier="Gulf Route Freight",
        driver="Hector Ruiz",
        plant_manager="Nora Alvarez",
        quality_director="Simon Wu",
        ops_vp="Patrick Doyle",
        dock_supervisor="Janelle Brooks",
        account_manager="Victor Han",
        inspector="Elise Grant",
        compliance_manager="Monica Reed",
        defect_primary="casting voids near a mounting ear",
        defect_secondary="particulate trapped in coolant passages",
        defect_tertiary="gasket-face flatness outside tolerance",
        defect_cosmetic="paint blemishes on noncritical exterior areas",
        customer_pressure="Delta Marine told Harbor Fluid that a vessel retrofit would stall without the planned shipment.",
        screen_form_phrase="a shipment release screen bearing Patrick Doyle's name",
    ),
    CaseData(
        matter_id="redcliff-v-sterling",
        matter_name="Redcliff Motion Works v. Sterling Plant Assurance",
        plaintiff="Redcliff Motion Works, Inc.",
        defendant="Sterling Plant Assurance, LLC",
        product="actuator assemblies",
        lot_id="RM-511",
        truck_id="4807",
        customer="Alpine Robotics",
        plant="Redcliff Motion Plant 3",
        exhibit_number=9,
        inspect_date="2025-07-10",
        ship_date="2025-07-11",
        meeting_date="2025-07-14",
        reject_date="2025-07-15",
        report_number="SPA-RM511-071025",
        ncr_number="NCR-25-0714",
        form_id="SRF-4807",
        carrier="Northern Line Haul",
        driver="Tomas Vega",
        plant_manager="Owen Hartley",
        quality_director="Meera Nair",
        ops_vp="Blake Sutton",
        dock_supervisor="Cara Fields",
        account_manager="Jonah West",
        inspector="Isabel Torres",
        compliance_manager="Felicity Dean",
        defect_primary="a cracked actuator collar on sampled units",
        defect_secondary="grease contamination inside the assembly cavity",
        defect_tertiary="shaft runout exceeding tolerance",
        defect_cosmetic="minor surface scuffing on outer covers",
        customer_pressure="Alpine Robotics warned that a pilot-line build would pause if the shipment missed the dock window.",
        screen_form_phrase="an internal release page showing Blake Sutton in the approval field",
    ),
    CaseData(
        matter_id="valewood-v-triton",
        matter_name="Valewood Industrial Products v. Triton Field Inspections",
        plaintiff="Valewood Industrial Products, Inc.",
        defendant="Triton Field Inspections, LLC",
        product="pressure regulator components",
        lot_id="VI-267",
        truck_id="7055",
        customer="Keystone Energy Controls",
        plant="Valewood Plant 6",
        exhibit_number=14,
        inspect_date="2025-08-19",
        ship_date="2025-08-20",
        meeting_date="2025-08-22",
        reject_date="2025-08-25",
        report_number="TFI-VI267-081925",
        ncr_number="NCR-25-0822",
        form_id="SRF-7055",
        carrier="Midwest Relay Freight",
        driver="Daniel Ponce",
        plant_manager="Amelia Foster",
        quality_director="Rohan Iyer",
        ops_vp="Caleb Marsh",
        dock_supervisor="Nina Park",
        account_manager="Seth Dillon",
        inspector="Marisol Vega",
        compliance_manager="Paige Lambert",
        defect_primary="diaphragm cuts on sampled regulator assemblies",
        defect_secondary="brass particulate in the flow cavity",
        defect_tertiary="seat diameter drift beyond tolerance",
        defect_cosmetic="coating blemishes on exterior fittings",
        customer_pressure="Keystone Energy said a controls-panel shipment would miss final integration without the lot.",
        screen_form_phrase="a release printout with Caleb Marsh listed in the approver field",
    ),
]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).strip() + "\n", encoding="utf-8")


def doc_path(case: CaseData, filename: str) -> str:
    return f"sample-docs/{case.matter_id}/{filename}"


def build_case_metadata(case: CaseData) -> dict:
    exhibit_doc_id = case.exhibit_doc_id
    return {
        "matter_id": case.matter_id,
        "matter_name": case.matter_name,
        "documents": [
            {
                "doc_id": "complaint",
                "filename": "complaint.md",
                "title": "Complaint",
                "doc_type": "complaint",
                "source_path": doc_path(case, "complaint.md"),
                "source_kind": "local_demo_generated",
                "created_date": "2025-04-02",
                "participants": [case.plant_manager, case.quality_director, case.ops_vp, case.dock_supervisor, case.account_manager, case.inspector, case.compliance_manager],
                "tags": ["pleading", "timeline", "shipment", f"exhibit-{case.exhibit_number}", "customer-rejection"],
                "exhibit_number": None,
                "citation_label": "Complaint",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": [exhibit_doc_id, "inspection-email-chain", case.deposition_pm_doc_id, "customer-rejection-letter"],
                "summary": f"{case.plaintiff_short} alleges {case.defendant_short}'s inspection and communication failures allowed Lot {case.lot_id} to ship despite a hold recommendation.",
            },
            {
                "doc_id": "answer-and-affirmative-defenses",
                "filename": "answer-and-affirmative-defenses.md",
                "title": "Answer and Affirmative Defenses",
                "doc_type": "answer_pleading",
                "source_path": doc_path(case, "answer-and-affirmative-defenses.md"),
                "source_kind": "local_demo_generated",
                "created_date": "2025-05-01",
                "participants": [case.quality_director, case.ops_vp, case.inspector, case.plant_manager],
                "tags": ["pleading", "defenses", "knowledge", "causation"],
                "exhibit_number": None,
                "citation_label": "Answer and Affirmative Defenses",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["complaint", exhibit_doc_id, "inspection-email-chain", "shipment-release-form"],
                "summary": f"{case.defendant_short} denies liability and contends {case.plaintiff_short} knew of the hold before shipment but still prioritized customer delivery.",
            },
            {
                "doc_id": "interrogatories-and-responses",
                "filename": "interrogatories-and-responses.md",
                "title": "Supplemental Interrogatories and Responses",
                "doc_type": "written_discovery_responses",
                "source_path": doc_path(case, "interrogatories-and-responses.md"),
                "source_kind": "local_demo_generated",
                "created_date": "2025-09-15",
                "participants": [case.plant_manager, case.quality_director, case.ops_vp, case.dock_supervisor, case.account_manager],
                "tags": ["discovery", "interrogatories", "timeline", f"exhibit-{case.exhibit_number}", "contradiction"],
                "exhibit_number": None,
                "citation_label": "Supplemental Interrogatory Responses",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": [case.deposition_pm_doc_id, case.deposition_quality_doc_id, "inspection-email-chain", exhibit_doc_id],
                "summary": f"{case.plaintiff_short} states no management witness other than {case.quality_director} reviewed Exhibit {case.exhibit_number} before departure and says definitive fail notice did not reach operations until after the truck rolled.",
            },
            {
                "doc_id": "requests-for-production-and-responses",
                "filename": "requests-for-production-and-responses.md",
                "title": "Requests for Production and Responses",
                "doc_type": "written_discovery_responses",
                "source_path": doc_path(case, "requests-for-production-and-responses.md"),
                "source_kind": "local_demo_generated",
                "created_date": "2025-09-20",
                "participants": [case.quality_director, case.dock_supervisor, case.compliance_manager, case.account_manager],
                "tags": ["discovery", "document-production", "release-form", "emails", "root-cause"],
                "exhibit_number": None,
                "citation_label": "Requests for Production and Responses",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["shipment-release-form", "bill-of-lading", "root-cause-memo", "inspection-email-chain"],
                "summary": "The production responses identify the main operational documents and acknowledge gaps in preserved phone and system audit evidence.",
            },
            {
                "doc_id": case.deposition_pm_doc_id,
                "filename": f"{case.deposition_pm_doc_id}.md",
                "title": f"Deposition Transcript of {case.plant_manager}",
                "doc_type": "deposition_transcript_excerpt",
                "source_path": doc_path(case, f"{case.deposition_pm_doc_id}.md"),
                "source_kind": "local_demo_generated",
                "created_date": "2025-11-03",
                "participants": [case.plant_manager, case.quality_director, case.ops_vp, case.dock_supervisor, case.inspector],
                "tags": ["deposition", "witness-testimony", f"exhibit-{case.exhibit_number}", "hold-order", "shipment-release"],
                "exhibit_number": None,
                "citation_label": f"{case.plant_manager} Deposition",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["interrogatories-and-responses", "inspection-email-chain", "shipment-release-form", exhibit_doc_id],
                "summary": f"{case.plant_manager} says they knew of the hold on {case.inspect_date}, looked at the first page of Exhibit {case.exhibit_number}, and told dock staff not to release the truck without higher approval.",
            },
            {
                "doc_id": case.deposition_quality_doc_id,
                "filename": f"{case.deposition_quality_doc_id}.md",
                "title": f"Deposition Transcript of {case.quality_director}",
                "doc_type": "deposition_transcript_excerpt",
                "source_path": doc_path(case, f"{case.deposition_quality_doc_id}.md"),
                "source_kind": "local_demo_generated",
                "created_date": "2025-11-10",
                "participants": [case.quality_director, case.plant_manager, case.ops_vp, case.inspector, case.account_manager],
                "tags": ["deposition", "quality", f"exhibit-{case.exhibit_number}", "timeline", "customer-pressure"],
                "exhibit_number": None,
                "citation_label": f"{case.quality_director} Deposition",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": [case.deposition_pm_doc_id, "inspection-email-chain", "nonconformance-report", "internal-meeting-notes"],
                "summary": f"{case.quality_director} confirms a verbal hold on {case.inspect_date} but says the formal Exhibit {case.exhibit_number} PDF was forwarded after midnight and that they never gave final release authority.",
            },
            {
                "doc_id": case.deposition_dock_doc_id,
                "filename": f"{case.deposition_dock_doc_id}.md",
                "title": f"Deposition Transcript of {case.dock_supervisor}",
                "doc_type": "deposition_transcript_excerpt",
                "source_path": doc_path(case, f"{case.deposition_dock_doc_id}.md"),
                "source_kind": "local_demo_generated",
                "created_date": "2025-11-18",
                "participants": [case.dock_supervisor, case.plant_manager, case.ops_vp, case.quality_director],
                "tags": ["deposition", "warehouse", "shipment-release", "release-form", "dock-operations"],
                "exhibit_number": None,
                "citation_label": f"{case.dock_supervisor} Deposition",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["shipment-release-form", "bill-of-lading", "inspection-email-chain", case.deposition_pm_doc_id],
                "summary": f"{case.dock_supervisor} describes an unclear dock decision chain, remembers seeing {case.screen_form_phrase}, and says no one gave a clean documented release.",
            },
            {
                "doc_id": exhibit_doc_id,
                "filename": case.exhibit_filename,
                "title": f"Exhibit {case.exhibit_number} Inspection Report",
                "doc_type": "inspection_report",
                "source_path": doc_path(case, case.exhibit_filename),
                "source_kind": "local_demo_generated",
                "created_date": case.inspect_date,
                "participants": [case.inspector, case.quality_director, case.plant_manager],
                "tags": ["inspection", f"exhibit-{case.exhibit_number}", "fail-hold", "quality", "findings"],
                "exhibit_number": case.exhibit_number,
                "citation_label": f"Exhibit {case.exhibit_number} Inspection Report",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["nonconformance-report", "inspection-email-chain", case.deposition_pm_doc_id, "complaint"],
                "summary": f"{case.defendant_short}'s report states Lot {case.lot_id} failed inspection, should be held, and should not ship pending quality and operations review.",
            },
            {
                "doc_id": "nonconformance-report",
                "filename": "nonconformance-report.md",
                "title": f"Nonconformance Report {case.ncr_number}",
                "doc_type": "quality_nonconformance_report",
                "source_path": doc_path(case, "nonconformance-report.md"),
                "source_kind": "local_demo_generated",
                "created_date": case.ship_date,
                "participants": [case.quality_director, case.compliance_manager, case.plant_manager, case.dock_supervisor],
                "tags": ["quality", "ncr", "containment", "hold", "open-issues"],
                "exhibit_number": None,
                "citation_label": "Nonconformance Report",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": [exhibit_doc_id, "corrective-action-plan", "shipment-release-form", "internal-meeting-notes"],
                "summary": f"The NCR records the failed lot, notes that Truck {case.truck_id} left despite a hold, and lists unresolved questions about the release path.",
            },
            {
                "doc_id": "corrective-action-plan",
                "filename": "corrective-action-plan.md",
                "title": "Corrective Action Plan",
                "doc_type": "corrective_action_plan",
                "source_path": doc_path(case, "corrective-action-plan.md"),
                "source_kind": "local_demo_generated",
                "created_date": case.meeting_date,
                "participants": [case.compliance_manager, case.quality_director, case.ops_vp, case.dock_supervisor],
                "tags": ["capa", "process-controls", "audit-log", "release-form"],
                "exhibit_number": None,
                "citation_label": "Corrective Action Plan",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["nonconformance-report", "root-cause-memo", "shipment-release-form"],
                "summary": "The CAPA proposes system and training fixes and notes that the audit trail suggests release-form edits after truck departure.",
            },
            {
                "doc_id": "shipment-release-form",
                "filename": "shipment-release-form.md",
                "title": f"Shipment Release Form {case.form_id}",
                "doc_type": "shipment_release_form",
                "source_path": doc_path(case, "shipment-release-form.md"),
                "source_kind": "local_demo_generated",
                "created_date": case.ship_date,
                "participants": [case.dock_supervisor, case.ops_vp, case.plant_manager],
                "tags": ["operations", "release-form", f"truck-{case.truck_id}", "approval"],
                "exhibit_number": None,
                "citation_label": "Shipment Release Form",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["bill-of-lading", case.deposition_dock_doc_id, "corrective-action-plan", "root-cause-memo"],
                "summary": f"The release form shows a verbal operations release tied to {case.ops_vp}, but its timing and audit history are disputed.",
            },
            {
                "doc_id": "bill-of-lading",
                "filename": "bill-of-lading.md",
                "title": f"Bill of Lading for Truck {case.truck_id}",
                "doc_type": "bill_of_lading",
                "source_path": doc_path(case, "bill-of-lading.md"),
                "source_kind": "local_demo_generated",
                "created_date": case.ship_date,
                "participants": [case.dock_supervisor, case.account_manager],
                "tags": ["shipping", "bill-of-lading", f"truck-{case.truck_id}", "departure-time"],
                "exhibit_number": None,
                "citation_label": "Bill of Lading",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["shipment-release-form", "customer-rejection-letter", "inspection-email-chain"],
                "summary": f"The bill of lading fixes the departure time of Truck {case.truck_id} and shows the shipment proceeded under expedite instructions.",
            },
            {
                "doc_id": "customer-rejection-letter",
                "filename": "customer-rejection-letter.md",
                "title": f"{case.customer} Rejection Letter",
                "doc_type": "customer_letter",
                "source_path": doc_path(case, "customer-rejection-letter.md"),
                "source_kind": "local_demo_generated",
                "created_date": case.reject_date,
                "participants": [case.account_manager, case.compliance_manager],
                "tags": ["customer", "rejection", "damages", "defects"],
                "exhibit_number": None,
                "citation_label": f"{case.customer} Rejection Letter",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["complaint", exhibit_doc_id, "bill-of-lading"],
                "summary": f"{case.customer} reports field failures tied to Lot {case.lot_id} and rejects the shipment.",
            },
            {
                "doc_id": "inspection-email-chain",
                "filename": "inspection-email-chain.md",
                "title": "Inspection Email Chain",
                "doc_type": "email_chain",
                "source_path": doc_path(case, "inspection-email-chain.md"),
                "source_kind": "local_demo_generated",
                "created_date": case.ship_date,
                "participants": [case.account_manager, case.inspector, case.quality_director, case.plant_manager, case.ops_vp, case.dock_supervisor],
                "tags": ["email", "shipment", "hold-notice", "timeline", "customer-pressure"],
                "exhibit_number": None,
                "citation_label": "Inspection Email Chain",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": [exhibit_doc_id, case.deposition_pm_doc_id, case.deposition_quality_doc_id, "internal-meeting-notes"],
                "summary": f"The email chain captures customer pressure, verbal and written hold notices, and a disputed early-morning decision path for Truck {case.truck_id}.",
            },
            {
                "doc_id": "internal-meeting-notes",
                "filename": "internal-meeting-notes.md",
                "title": "Internal Meeting Notes",
                "doc_type": "internal_meeting_notes",
                "source_path": doc_path(case, "internal-meeting-notes.md"),
                "source_kind": "local_demo_generated",
                "created_date": case.meeting_date,
                "participants": [case.quality_director, case.plant_manager, case.ops_vp, case.dock_supervisor, case.compliance_manager, case.account_manager],
                "tags": ["internal-notes", "root-cause", "open-issues", "shipment-release"],
                "exhibit_number": None,
                "citation_label": "Internal Meeting Notes",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["inspection-email-chain", case.deposition_dock_doc_id, "nonconformance-report", "root-cause-memo"],
                "summary": "Internal follow-up notes capture conflicting witness recollections and leave the final release decision unresolved.",
            },
            {
                "doc_id": "root-cause-memo",
                "filename": "root-cause-memo.md",
                "title": "Root Cause Memo",
                "doc_type": "internal_root_cause_memo",
                "source_path": doc_path(case, "root-cause-memo.md"),
                "source_kind": "local_demo_generated",
                "created_date": case.reject_date,
                "participants": [case.compliance_manager, case.quality_director, case.ops_vp, case.plant_manager, case.dock_supervisor],
                "tags": ["root-cause", "analysis", "timeline", "approval-gap", "deposition-topics"],
                "exhibit_number": None,
                "citation_label": "Root Cause Memo",
                "page_markers": True,
                "access_scope": {"matter_id": case.matter_id, "allowed_roles": ROLES},
                "related_docs": ["internal-meeting-notes", "corrective-action-plan", "shipment-release-form", "inspection-email-chain"],
                "summary": "The memo synthesizes the evidence, flags contradictions, and identifies unresolved approval and system-audit questions for deposition prep.",
            },
        ],
    }


def build_case_readme(case: CaseData) -> str:
    return f"""
    # {case.matter_name}

    This case folder contains a stakeholder-facing document set for a manufacturing inspection and shipment-release dispute.

    ## Design goals

    - look closer to a real matter file
    - support chronology questions
    - support contradiction analysis across witnesses and documents
    - support exhibit tracing for Exhibit {case.exhibit_number}
    - support unanswered-topic detection
    - keep clean page or line citations for retrieval and answer grounding

    ## Main contradiction themes

    - who first saw Exhibit {case.exhibit_number}
    - whether {case.ops_vp} gave verbal clearance to release Truck {case.truck_id}
    - whether the shipment release form existed before the truck left
    - whether the defects were cosmetic or serious
    - whether dock staff were clearly told to hold the truck

    ## Main unanswered gaps

    - who gave the final approval to release Truck {case.truck_id}
    - whether the {case.ops_vp} approval field on the release form was entered before or after departure
    - what was said in the missing phone or voicemail exchanges on the morning of {case.ship_date}

    ## Layout

    - The 16 main documents live at the case root.
    - `_meta/` holds `metadata.json`, this README, `reference-notes.md`, and `demo-questions.md`.
    - `_retrieval/` holds generated `chunks.json` and `embeddings.npz`.

    ## Important note

    Every document in this case folder is original and fictional.

    The writing style was shaped by public legal and regulatory references, but the contents were generated for demo use only.
    """


def build_demo_questions(case: CaseData) -> str:
    return f"""
    # Demo Questions

    Use these questions when you want the corpus to show multi-document reasoning, contradictions, and gaps.

    ## Multi-document questions

    1. Create a chronology from the {case.inspect_date} inspection through the customer rejection.
    2. Who saw Exhibit {case.exhibit_number} before Truck {case.truck_id} departed, and what evidence supports that?
    3. What evidence suggests {case.ops_vp} may have approved shipment, and what evidence cuts the other way?
    4. Was the shipment release form created before the truck left, or was it updated afterward?
    5. Were the inspection issues cosmetic, or were they serious defects that justified a hold?
    6. What do {case.plant_manager} and {case.dock_supervisor} say about whether the dock was told to hold the truck?
    7. Which documents show customer pressure affecting the shipment decision?
    8. Which people were in the decision chain for releasing Lot {case.lot_id}?

    ## Gap and contradiction questions

    9. What are the biggest contradictions between the interrogatory responses and later deposition testimony?
    10. What key facts remain unresolved even after reviewing the full file?
    11. Who gave the final approval to release the shipment?
    12. What evidence exists about when the {case.ops_vp} approval entry was added to the release form?
    """


def complaint_md(case: CaseData) -> str:
    return f"""
    # Complaint

    ## Matter Name

    {case.matter_name}

    ## Document Date

    2025-04-02

    ## Document Type

    Complaint

    ## Page 1

    ### Caption

    IN THE CIRCUIT COURT OF COOK COUNTY, ILLINOIS  
    LAW DIVISION

    {case.plaintiff.upper()}  
    Plaintiff,  
    v.  
    {case.defendant.upper()}  
    Defendant.

    ### Parties and Nature of Action

    1. Plaintiff {case.plaintiff} manufactures {case.product} for industrial customers.
    2. Defendant {case.defendant} provides third-party inspection and shipment-release services for industrial components.
    3. This action arises from {case.defendant_short}'s inspection of Lot {case.lot_id}, a shipment of {case.product} prepared for delivery to {case.customer}.
    4. {case.plaintiff_short} retained {case.defendant_short} because {case.customer} required independent inspection before release.
    5. {case.plaintiff_short} alleges that {case.defendant_short} identified serious defects, prepared the report later marked as Exhibit {case.exhibit_number}, and failed to communicate the hold recommendation in a clear and timely manner to the people controlling shipment.

    ### Core Event

    6. On {case.inspect_date}, {case.inspector} inspected Lot {case.lot_id} at {case.plant}.
    7. The inspection identified {case.defect_primary}, {case.defect_secondary}, and {case.defect_tertiary}.
    8. Truck {case.truck_id} nevertheless departed {case.plaintiff_short}'s dock on {case.ship_date} with the inspected lot.

    ## Page 2

    ### Factual Allegations

    9. {case.plant_manager} was Plant Manager for {case.plant} and oversaw production and outbound staging for Lot {case.lot_id}.
    10. {case.quality_director} was {case.plaintiff_short}'s Director of Quality and {case.defendant_short}'s main quality contact.
    11. {case.ops_vp} was {case.plaintiff_short}'s Vice President of Operations and had authority over shipment scheduling and customer escalation issues.
    12. {case.dock_supervisor} supervised the warehouse dock where Truck {case.truck_id} was loaded.
    13. {case.account_manager} managed the {case.customer} account and relayed urgent customer pressure to keep the shipment on schedule.
    14. {case.defendant_short} prepared a written inspection report, identified by the parties as Exhibit {case.exhibit_number}, reflecting a failed inspection and a hold recommendation.
    15. {case.plaintiff_short} alleges the final written report was not effectively delivered to the people who could stop the truck before departure.

    ### Timeline

    - 2025-04-10: {case.plaintiff_short} schedules an independent pre-shipment inspection with {case.defendant_short}.
    - {case.inspect_date}: {case.inspector} inspects Lot {case.lot_id} and prepares the report later referred to as Exhibit {case.exhibit_number}.
    - {case.ship_date}: Truck {case.truck_id} departs with Lot {case.lot_id} despite the inspection concern.
    - {case.meeting_date}: {case.plaintiff_short} holds an internal meeting to determine how the shipment was released.
    - {case.reject_date}: {case.customer} rejects the shipment after receiving defective units.

    ## Page 3

    ### Claims and Damage

    16. {case.plaintiff_short} claims that {case.defendant_short} negligently performed and communicated the inspection, failed to ensure its hold recommendation was delivered to the correct decision-makers, and caused {case.plaintiff_short} to suffer customer rejection, expedited replacement costs, internal rework costs, and business interruption.
    17. {case.plaintiff_short} further alleges that, had {case.defendant_short} timely and clearly escalated the failed inspection and Exhibit {case.exhibit_number} hold recommendation, Truck {case.truck_id} would not have departed.
    18. {case.customer} later reported field failures linked to {case.defect_primary}, {case.defect_secondary}, and {case.defect_tertiary}.
    19. {case.plaintiff_short} seeks damages, costs, and any additional relief allowed by law.

    ### Reference to Exhibit {case.exhibit_number}

    20. Exhibit {case.exhibit_number} is central to this dispute because it is the strongest written record of the inspection findings and the recommendation not to ship Lot {case.lot_id} pending review.
    """


def answer_md(case: CaseData) -> str:
    return f"""
    # Answer and Affirmative Defenses

    ## Matter Name

    {case.matter_name}

    ## Document Date

    2025-05-01

    ## Document Type

    Answer and Affirmative Defenses

    ## Page 1

    ### Caption

    IN THE CIRCUIT COURT OF COOK COUNTY, ILLINOIS  
    LAW DIVISION

    {case.defendant.upper()}  
    Defendant, by counsel, answers the Complaint of {case.plaintiff.upper()}.

    ### General Response

    1. {case.defendant_short} admits that {case.inspector} inspected Lot {case.lot_id} on {case.inspect_date}.
    2. {case.defendant_short} admits that the inspection raised concerns and that the report later marked Exhibit {case.exhibit_number} included hold language.
    3. {case.defendant_short} denies that it failed to communicate the inspection concern to {case.plaintiff_short}.
    4. {case.defendant_short} alleges that {case.plaintiff_short} quality and operations personnel were informed of the hold recommendation on {case.inspect_date} and that {case.plaintiff_short} nevertheless allowed Truck {case.truck_id} to depart.

    ## Page 2

    ### Specific Admissions and Denials

    5. {case.defendant_short} admits that {case.quality_director} was its primary quality contact at {case.plaintiff_short}.
    6. {case.defendant_short} admits that {case.customer} was pressing for on-time delivery.
    7. {case.defendant_short} denies that the first meaningful communication of the hold occurred only after the truck departed.
    8. {case.defendant_short} states that {case.inspector} verbally communicated a hold recommendation on {case.inspect_date} and issued a preliminary written report that same evening.
    9. {case.defendant_short} denies that it had authority to physically prevent {case.plaintiff_short} from shipping the lot once {case.plaintiff_short} personnel chose to proceed.
    10. {case.defendant_short} further denies any allegation that the identified defects were hidden, trivial, or incapable of supporting a hold recommendation.

    ### Defendant's Position

    11. {case.defendant_short} contends that {case.plaintiff_short} personnel knew enough by the close of business on {case.inspect_date} to quarantine the lot.
    12. {case.defendant_short} further contends that any release of the truck on {case.ship_date} resulted from {case.plaintiff_short}'s own internal decision chain, customer pressure, and inadequate internal release controls.

    ## Page 3

    ### Affirmative Defenses

    13. As a first affirmative defense, {case.defendant_short} states that {case.plaintiff_short}'s damages were caused in whole or in part by {case.plaintiff_short}'s own acts or omissions, including the failure to maintain a reliable shipment hold process.
    14. As a second affirmative defense, {case.defendant_short} states that {case.plaintiff_short} failed to mitigate damages after learning of the inspection concern.
    15. As a third affirmative defense, {case.defendant_short} states that intervening acts by {case.plaintiff_short} operations personnel, including any undocumented verbal release, broke the chain of causation.
    16. As a fourth affirmative defense, {case.defendant_short} states that {case.plaintiff_short}'s own records reflect awareness of the hold recommendation before the truck departed.

    ### Prayer

    17. {case.defendant_short} requests judgment in its favor, dismissal of the Complaint with prejudice, costs, and any further relief deemed just.
    """


def interrogatories_md(case: CaseData) -> str:
    return f"""
    # Supplemental Interrogatories and Responses

    ## Matter Name

    {case.matter_name}

    ## Document Date

    2025-09-15

    ## Document Type

    Supplemental Interrogatories and Responses

    ## Page 1

    ### Interrogatory No. 1

    Identify when {case.plaintiff_short} management first learned that Lot {case.lot_id} had failed inspection.

    ### Response to Interrogatory No. 1

    After reasonable investigation, {case.plaintiff_short} states that definitive notice that the lot had failed inspection did not reach operations management until the morning of {case.ship_date}, after Truck {case.truck_id} had already left the facility. {case.plaintiff_short} further states that earlier communications on {case.inspect_date} were treated by some recipients as preliminary or incomplete.

    ### Interrogatory No. 2

    Identify all {case.plaintiff_short} personnel who reviewed Exhibit {case.exhibit_number} before Truck {case.truck_id} departed.

    ### Response to Interrogatory No. 2

    {case.plaintiff_short} identifies {case.quality_director} as the only employee known at this time to have reviewed the complete Exhibit {case.exhibit_number} report before departure. {case.plaintiff_short} is not presently aware of evidence that {case.plant_manager} reviewed the report before the truck left.

    ## Page 2

    ### Interrogatory No. 3

    Identify the person or persons who authorized release of Truck {case.truck_id}.

    ### Response to Interrogatory No. 3

    {case.plaintiff_short} has not identified the final approving person with certainty. Available records suggest that operations, warehouse, and quality personnel all believed someone else had final authority. {case.plaintiff_short} continues to investigate whether any verbal instruction came from {case.ops_vp} or another operations supervisor.

    ### Interrogatory No. 4

    Describe the defects that were reported during the inspection of Lot {case.lot_id}.

    ### Response to Interrogatory No. 4

    The inspection materials reference {case.defect_primary}, {case.defect_secondary}, and {case.defect_tertiary}. {case.plaintiff_short} states that internal discussion later arose concerning whether {case.defect_cosmetic} was cosmetic, but the written report itself used hold language and should have triggered a stop-ship review.

    ## Page 3

    ### Interrogatory No. 5

    Identify documents that support {case.plaintiff_short}'s position concerning the release decision.

    ### Response to Interrogatory No. 5

    Responsive documents include the Inspection Email Chain, the Nonconformance Report, the Shipment Release Form, the Bill of Lading, the Internal Meeting Notes, and the Root Cause Memo.

    ### Supplementation Statement

    {case.plaintiff_short} reserves the right to supplement these responses if additional phone logs, system audit records, or witness testimony become available.
    """


def requests_md(case: CaseData) -> str:
    return f"""
    # Requests for Production and Responses

    ## Matter Name

    {case.matter_name}

    ## Document Date

    2025-09-20

    ## Document Type

    Requests for Production and Responses

    ## Page 1

    ### Request for Production No. 1

    Produce all documents concerning Exhibit {case.exhibit_number} and the inspection of Lot {case.lot_id}.

    ### Response to Request for Production No. 1

    Responsive documents produced include Exhibit {case.exhibit_number} Inspection Report, the Inspection Email Chain, and the Nonconformance Report.

    ### Request for Production No. 2

    Produce all documents concerning release or shipment approval for Truck {case.truck_id}.

    ### Response to Request for Production No. 2

    Responsive documents produced include the Shipment Release Form and the Bill of Lading. {case.plaintiff_short} notes that the system-generated print time visible on the Shipment Release Form may not establish when all fields were first entered.

    ## Page 2

    ### Request for Production No. 3

    Produce all documents reflecting customer complaints or rejection of Lot {case.lot_id}.

    ### Response to Request for Production No. 3

    Responsive documents include the {case.customer} Rejection Letter and related internal follow-up notes referenced in the Root Cause Memo.

    ### Request for Production No. 4

    Produce all internal analyses of how the shipment was released despite the inspection concern.

    ### Response to Request for Production No. 4

    Responsive documents include Internal Meeting Notes, the Nonconformance Report, the Corrective Action Plan, and the Root Cause Memo.

    ## Page 3

    ### Request for Production No. 5

    Produce all phone logs, text messages, or voicemails regarding the morning of {case.ship_date}.

    ### Response to Request for Production No. 5

    After reasonable search, {case.plaintiff_short} has not located complete phone or voicemail records sufficient to show the content of all verbal communications that morning. {case.plaintiff_short} will supplement if additional records are found.

    ### Request for Production No. 6

    Produce all audit-log records showing when the Shipment Release Form was created or modified.

    ### Response to Request for Production No. 6

    {case.plaintiff_short} produced the available system export referenced in the Corrective Action Plan. {case.plaintiff_short} notes that the export reflects later print and save times, and disputes any inference that the printed record proves a completed approval existed before departure.
    """


def deposition_pm_md(case: CaseData) -> str:
    return f"""
    # Deposition Transcript of {case.plant_manager}

    ## Matter Name

    {case.matter_name}

    ## Document Date

    2025-11-03

    ## Document Type

    Deposition Transcript

    ## Page 12

    ### Page 12, Lines 4-23

    **Q.** Please state your name and role as of {case.inspect_date[:4]}.  
    **A.** My name is {case.plant_manager}. I was Plant Manager for {case.plant}.  
    **Q.** Did Lot {case.lot_id} fall within your responsibilities?  
    **A.** Yes. I oversaw production flow and outbound staging.  
    **Q.** Do you recall {case.defendant_short} inspecting that lot on {case.inspect_date}?  
    **A.** I do. {case.inspector} from {case.defendant_short} was on the floor that afternoon.  
    **Q.** Did {case.inspector_last_name} tell you there was a problem?  
    **A.** Yes. {case.inspector.split()[0]} told me late that afternoon that the lot should not move until quality reviewed the findings.  
    **Q.** Did {case.inspector.split()[0]} describe the problem?  
    **A.** {case.inspector.split()[0]} mentioned {case.defect_primary}, {case.defect_secondary}, and {case.defect_tertiary}.

    ## Page 13

    ### Page 13, Lines 2-21

    **Q.** Did you review Exhibit {case.exhibit_number} before Truck {case.truck_id} left on {case.ship_date}?  
    **A.** I did not study the full report, but {case.quality_director} sent me the PDF on the evening of {case.inspect_date} and I looked at the first page.  
    **Q.** What did you see?  
    **A.** I saw hold language and a note about {case.defect_primary}.  
    **Q.** Did you understand that to mean the lot had failed inspection?  
    **A.** I understood it meant the lot should stay put until somebody above me cleared it.  
    **Q.** Who did you think had authority to clear it?  
    **A.** {case.quality_director} from quality or {case.ops_vp} from operations.  
    **Q.** Did you think the issues were cosmetic?  
    **A.** No. They sounded serious to me.

    ## Page 14

    ### Page 14, Lines 5-23

    **Q.** What happened on the morning of {case.ship_date}?  
    **A.** {case.dock_supervisor} called from the dock before seven and said Truck {case.truck_id} was already staged.  
    **Q.** What did you tell {case.dock_supervisor.split()[0]}?  
    **A.** I told {case.dock_supervisor.split()[0]} to keep the truck parked unless {case.ops_vp} or {case.quality_director} cleared the release.  
    **Q.** Did you speak with {case.ops_vp} live before the truck left?  
    **A.** I do not remember a live call. I sent a message and left a voicemail.  
    **Q.** Did you personally authorize the truck to leave?  
    **A.** No.  
    **Q.** Did you see a signed release?  
    **A.** No. I never saw a signed release in real time.

    ## Page 15

    ### Page 15, Lines 3-19

    **Q.** When do you believe management first knew the lot had failed inspection?  
    **A.** {case.quality_director} knew on {case.inspect_date} because {case.quality_director.split()[0]} was dealing directly with {case.inspector.split()[0]}. I knew on {case.inspect_date} from {case.inspector.split()[0]} and from the first page of Exhibit {case.exhibit_number}.  
    **Q.** Are you able to identify the person who changed the shipment from hold to release?  
    **A.** No. I cannot identify that person with certainty.  
    **Q.** Do you know whether {case.ops_vp} gave a verbal release?  
    **A.** I heard people speculate about that later, but I did not hear {case.ops_vp.split()[0]} give that instruction myself.
    """


def deposition_quality_md(case: CaseData) -> str:
    return f"""
    # Deposition Transcript of {case.quality_director}

    ## Matter Name

    {case.matter_name}

    ## Document Date

    2025-11-10

    ## Document Type

    Deposition Transcript

    ## Page 41

    ### Page 41, Lines 6-24

    **Q.** Please state your name and role as of {case.inspect_date[:4]}.  
    **A.** {case.quality_director}. I was {case.plaintiff_short}'s Director of Quality.  
    **Q.** Were you the primary quality contact for the {case.lot_id} inspection?  
    **A.** Yes. {case.inspector} contacted me during and after the inspection.  
    **Q.** When did you first learn there was a hold recommendation?  
    **A.** {case.inspector.split()[0]} called me at approximately 5:52 p.m. on {case.inspect_date} and said the lot should not ship pending review.  
    **Q.** Did you treat that as final?  
    **A.** I treated it as a real hold, but I was still waiting on the finished PDF report.  
    **Q.** Did anyone from operations pressure you to keep the shipment moving?  
    **A.** {case.account_manager} was escalating customer pressure all evening.

    ## Page 42

    ### Page 42, Lines 3-22

    **Q.** When did you forward Exhibit {case.exhibit_number} to other personnel?  
    **A.** The complete PDF went out just after midnight, at about 12:14 a.m. on {case.ship_date}.  
    **Q.** Did {case.plant_manager} receive it before that?  
    **A.** Not the complete PDF from me. Before midnight {case.plant_manager.split()[0]} only had my verbal summary and maybe a screenshot of the cover page, not the full report.  
    **Q.** Did you tell anyone the issues were merely cosmetic?  
    **A.** I said {case.defect_cosmetic} might turn out to be cosmetic, but the hold recommendation was not cosmetic.  
    **Q.** Did you ever authorize release?  
    **A.** No. I did not authorize release.

    ## Page 43

    ### Page 43, Lines 8-25

    **Q.** What do you recall {case.ops_vp} saying?  
    **A.** {case.ops_vp.split()[0]} said words to the effect of, "Keep the delivery slot if you can, but do not ship without a green light."  
    **Q.** Did {case.ops_vp.split()[0]} later tell you the lot could go?  
    **A.** Not directly to me.  
    **Q.** Did you communicate a hold to {case.plant_manager}?  
    **A.** Yes. I told {case.plant_manager.split()[0]} on {case.inspect_date} that {case.defendant_short} had the lot on hold and that the written report would follow.  
    **Q.** Did {case.plant_manager.split()[0]} seem to understand the seriousness?  
    **A.** Yes. {case.plant_manager.split()[0]} did not sound like someone who thought it was a minor issue.

    ## Page 44

    ### Page 44, Lines 4-18

    **Q.** Do you know who gave the final release instruction on {case.ship_date}?  
    **A.** No. I do not.  
    **Q.** Did you later see the shipment release form with {case.ops_vp}'s name on it?  
    **A.** Yes. I saw it later, not before the truck left.  
    **Q.** Did that form answer the question for you?  
    **A.** No. I still could not tell whether the form reflected a real-time approval or a later system entry.
    """


def deposition_dock_md(case: CaseData) -> str:
    return f"""
    # Deposition Transcript of {case.dock_supervisor}

    ## Matter Name

    {case.matter_name}

    ## Document Date

    2025-11-18

    ## Document Type

    Deposition Transcript

    ## Page 63

    ### Page 63, Lines 5-23

    **Q.** Please state your name and role.  
    **A.** {case.dock_supervisor}. I supervised the warehouse dock at {case.plant}.  
    **Q.** Were you involved with loading Truck {case.truck_id} on {case.ship_date}?  
    **A.** Yes. The truck was already at the door before seven that morning.  
    **Q.** Did you know there had been an inspection issue?  
    **A.** I knew there was some kind of quality concern, but I did not have the report itself.

    ## Page 64

    ### Page 64, Lines 3-22

    **Q.** What did {case.plant_manager} tell you that morning?  
    **A.** {case.plant_manager.split()[0]} said not to lose the truck and to wait for direction.  
    **Q.** Did {case.plant_manager.split()[0]} tell you plainly, "Do not release the truck"?  
    **A.** Not in those exact words.  
    **Q.** Did anyone from quality tell you the truck was on hold?  
    **A.** I do not remember a direct call from quality.  
    **Q.** Did you email asking whether the truck should hold or roll?  
    **A.** Yes. I sent an email because I did not have a clean answer.

    ## Page 65

    ### Page 65, Lines 6-24

    **Q.** Did you see a shipment release form before the truck left?  
    **A.** I saw {case.screen_form_phrase} sometime around 6:45 or so.  
    **Q.** Was it signed?  
    **A.** Not with a handwritten signature. It looked like an internal form.  
    **Q.** Did {case.ops_vp} tell you directly to let the truck go?  
    **A.** No. I never spoke to {case.ops_vp.split()[0]} directly that morning.  
    **Q.** So what did you rely on?  
    **A.** A mix of the screen form, dispatch chatter, and the sense that operations wanted the load to move.

    ## Page 66

    ### Page 66, Lines 2-18

    **Q.** Who gave the final approval in your mind?  
    **A.** I cannot say for sure.  
    **Q.** Did you believe {case.plant_manager} had approved it?  
    **A.** No. I did not think {case.plant_manager.split()[0]} had personally approved it.  
    **Q.** Did anyone ever clearly tell you, "Quality has released the lot"?  
    **A.** No. No one gave me that exact message.
    """


def exhibit_report_md(case: CaseData) -> str:
    return f"""
    # Exhibit {case.exhibit_number} Inspection Report

    ## Matter Name

    {case.matter_name}

    ## Document Date

    {case.inspect_date}

    ## Document Type

    Inspection Report

    ## Page 1

    ### Report Header

    - Report Number: {case.report_number}
    - Inspector: {case.inspector}
    - Customer: {case.plaintiff}
    - Lot: {case.lot_id}
    - Product: {case.product}
    - Inspection Date: {case.inspect_date}
    - Location: {case.plant}
    - Disposition: HOLD / DO NOT SHIP

    ### Executive Findings

    {case.defendant_short} identified multiple material concerns during sampling of Lot {case.lot_id}, including {case.defect_primary}, {case.defect_secondary}, and {case.defect_tertiary}. Based on the combined findings, the lot does not meet release criteria and should not ship pending quality and operations review.

    ## Page 2

    ### Observation Summary

    1. Sampled units showed {case.defect_primary}.
    2. Additional units showed {case.defect_secondary}.
    3. Measurements confirmed {case.defect_tertiary}.
    4. {case.defect_cosmetic.capitalize()} was also observed; while that condition alone might be evaluated further, the total condition of the lot supports a hold.

    ### Recommendation

    {case.defendant_short} recommends immediate hold of Lot {case.lot_id}, segregation from released inventory, and customer notification before shipment. The lot should not move until {case.plaintiff_short} quality and operations jointly approve a disposition after reviewing the written findings.

    ## Page 3

    ### Distribution and Notice

    - Verbal hold notice to {case.quality_director} at approximately 17:52 on {case.inspect_date}.
    - Verbal summary to {case.plant_manager} at approximately 18:05 on {case.inspect_date}.
    - Preliminary PDF issued at approximately 18:42 on {case.inspect_date}.
    - Full report circulated after final formatting.

    ### Inspector Note

    These findings are significant. The observed conditions are not described here as merely cosmetic.
    """


def ncr_md(case: CaseData) -> str:
    return f"""
    # Nonconformance Report {case.ncr_number}

    ## Matter Name

    {case.matter_name}

    ## Document Date

    {case.ship_date}

    ## Document Type

    Nonconformance Report

    ## Page 1

    ### Header

    - NCR Number: {case.ncr_number}
    - Opened By: {case.quality_director}
    - Opened On: {case.ship_date} 09:35
    - Affected Lot: {case.lot_id}
    - Related Exhibit: Exhibit {case.exhibit_number}
    - Immediate Status: Quarantine Remaining Inventory

    ### Problem Statement

    Lot {case.lot_id} was identified by {case.defendant_short} as a failed or hold lot on {case.inspect_date}, but Truck {case.truck_id} departed on {case.ship_date} before the release path was documented in a reliable way.

    ## Page 2

    ### Containment and Open Issues

    - Remaining inventory from the production run was quarantined.
    - {case.customer} was notified that a field review was underway.
    - Warehouse release controls were suspended pending review.

    ### Open Questions

    1. Who gave the final instruction to release Truck {case.truck_id}?
    2. Was the {case.ops_vp} approval entry on the Shipment Release Form entered before or after departure?
    3. Did dock personnel receive a clear hold instruction, or only a request to wait for more direction?
    """


def capa_md(case: CaseData) -> str:
    return f"""
    # Corrective Action Plan

    ## Matter Name

    {case.matter_name}

    ## Document Date

    {case.meeting_date}

    ## Document Type

    Corrective Action Plan

    ## Page 1

    ### Immediate Corrective Actions

    - Owner: {case.compliance_manager}
    - Related NCR: {case.ncr_number}
    - Objective: Prevent release of any lot under unresolved inspection hold

    Immediate actions implemented:

    1. Require dual release approval from quality and operations for customer-controlled lots.
    2. Lock shipment release in the ERP when a nonconformance or external hold exists.
    3. Require dock supervisors to retain the final release record before loading completes.

    ## Page 2

    ### Evidence Review and Follow-Up

    - Preliminary audit review suggests the Shipment Release Form was printed from the system at 09:16 on {case.ship_date}, after the truck had already departed.
    - Additional work is needed to determine whether the approver field existed in the system before departure or was added later to reflect an assumed verbal approval.
    - Missing voicemail and phone records remain a gap.

    ### Next Steps

    - Complete user-access audit for the release form record.
    - Interview {case.ops_vp} concerning any verbal direction on the morning of {case.ship_date}.
    - Train dock and dispatch staff to treat inspection holds as stop-ship events unless explicitly released in writing.
    """


def release_form_md(case: CaseData) -> str:
    return f"""
    # Shipment Release Form {case.form_id}

    ## Matter Name

    {case.matter_name}

    ## Document Date

    {case.ship_date}

    ## Document Type

    Shipment Release Form

    ## Page 1

    ### Release Record

    - Form ID: {case.form_id}
    - Lot: {case.lot_id}
    - Truck: {case.truck_id}
    - Prepared By: {case.dock_supervisor}
    - Prepared Time: {case.ship_date} 06:42
    - Requested Release Time: {case.ship_date} 07:02
    - Approval Basis: Verbal operations release
    - Approver Field: {case.ops_vp}
    - Print Time on Retrieved Copy: {case.ship_date} 09:16

    ### Notes

    - Quality hold flag was not cleared on the version later printed to the file.
    - The record does not include a handwritten signature or attached email authorization.
    - The document does not state who personally told the dock to proceed.
    """


def bill_md(case: CaseData) -> str:
    return f"""
    # Bill of Lading for Truck {case.truck_id}

    ## Matter Name

    {case.matter_name}

    ## Document Date

    {case.ship_date}

    ## Document Type

    Bill of Lading

    ## Page 1

    ### Shipment Record

    - Truck Number: {case.truck_id}
    - Carrier: {case.carrier}
    - Driver: {case.driver}
    - Shipper: {case.plant}
    - Consignee: {case.customer}
    - Product: {case.product}, Lot {case.lot_id}
    - Dock Departure Time: {case.ship_date} 07:08
    - Dock Sign-Off: {case.dock_supervisor}
    - Shipping Note: Expedite due to customer shutdown risk

    ### Observations

    The bill of lading fixes the departure time of the shipment but does not identify who approved release after the inspection hold concern.
    """


def rejection_letter_md(case: CaseData) -> str:
    return f"""
    # {case.customer} Rejection Letter

    ## Matter Name

    {case.matter_name}

    ## Document Date

    {case.reject_date}

    ## Document Type

    Customer Rejection Letter

    ## Page 1

    ### Letter

    To: {case.account_manager}, {case.plaintiff_short}  
    From: {case.customer}, Supplier Quality  
    Subject: Rejection of Lot {case.lot_id} Shipment

    {case.customer} rejects the {case.ship_date} shipment associated with Lot {case.lot_id}. Incoming inspection identified failures tied to {case.defect_primary}, {case.defect_secondary}, and {case.defect_tertiary}.

    ## Page 2

    ### Requested Action

    {case.customer} requests immediate replacement product, credit for the rejected lot, and a written explanation of how the shipment was released. Because the affected components were scheduled for an active line build, {case.customer} also reserves the right to seek recovery of shutdown-related costs.
    """


def email_chain_md(case: CaseData) -> str:
    return f"""
    # Inspection Email Chain

    ## Matter Name

    {case.matter_name}

    ## Document Date

    {case.ship_date}

    ## Document Type

    Email Chain

    ## Page 1

    ### Email 1

    - Date: 2025-04-10 09:12
    - From: {case.account_manager}
    - To: {case.quality_director}, {case.plant_manager}
    - Cc: {case.ops_vp}
    - Subject: {case.customer} requires third-party inspection before release

    {case.customer} will not accept Lot {case.lot_id} without an independent inspection sign-off. Please make sure {case.defendant_short} is on site before loading starts.

    ### Email 2

    - Date: {case.inspect_date} 17:58
    - From: {case.inspector}
    - To: {case.quality_director}
    - Cc: {case.plant_manager}
    - Subject: {case.lot_id} preliminary hold recommendation

    Based on today's sample I recommend that Lot {case.lot_id} be held. The main concerns are {case.defect_primary}, {case.defect_secondary}, and {case.defect_tertiary}. Full PDF will follow after I finish the formatted report.

    ## Page 2

    ### Email 3

    - Date: {case.inspect_date} 18:11
    - From: {case.quality_director}
    - To: {case.plant_manager}
    - Cc: {case.ops_vp}
    - Subject: {case.defendant_short} hold summary - do not ship pending review

    {case.plant_manager.split()[0]}, {case.inspector.split()[0]} says the lot is on hold and should not move until quality and operations review the write-up. I do not have the final PDF attached yet, but treat this as a stop-ship message for now.

    ### Email 4

    - Date: {case.inspect_date} 19:14
    - From: {case.account_manager}
    - To: {case.ops_vp}, {case.quality_director}, {case.plant_manager}
    - Cc: {case.dock_supervisor}
    - Subject: {case.customer} line will slip if we miss tomorrow morning

    {case.customer_pressure}

    ## Page 3

    ### Email 5

    - Date: {case.ship_date} 00:14
    - From: {case.quality_director}
    - To: {case.plant_manager}, {case.ops_vp}, {case.dock_supervisor}
    - Cc: {case.account_manager}
    - Subject: Exhibit {case.exhibit_number} PDF attached

    Attached is the finished {case.defendant_short} report for {case.lot_id}. The written recommendation says HOLD / DO NOT SHIP pending quality and operations review. I am attaching this now because the formatted PDF is finally complete.

    ### Email 6

    - Date: {case.ship_date} 06:18
    - From: {case.dock_supervisor}
    - To: {case.plant_manager}, {case.ops_vp}, {case.quality_director}
    - Cc:
    - Subject: Truck {case.truck_id} at the dock - hold or roll?

    The truck is staged and dispatch wants an answer. I know there was a quality issue last night. Please confirm whether this truck is staying parked or whether operations wants it moving.

    ## Page 4

    ### Email 7

    - Date: {case.ship_date} 06:27
    - From: {case.plant_manager}
    - To: {case.dock_supervisor}, {case.quality_director}, {case.ops_vp}
    - Cc:
    - Subject: Re: Truck {case.truck_id} at the dock - hold or roll?

    Keep the truck parked until quality or ops clears the release. I am not authorizing the load to leave on my own.

    ### Email 8

    - Date: {case.ship_date} 06:39
    - From: {case.account_manager}
    - To: {case.ops_vp}, {case.plant_manager}, {case.quality_director}
    - Cc: {case.dock_supervisor}
    - Subject: Need decision in next 15 minutes

    {case.customer_pressure}

    ## Page 5

    ### Email 9

    - Date: {case.ship_date} 06:51
    - From: {case.quality_director}
    - To: {case.ops_vp}, {case.plant_manager}, {case.dock_supervisor}
    - Cc:
    - Subject: Quality is not releasing Lot {case.lot_id}

    For clarity, quality is not releasing Lot {case.lot_id} at this time. If the truck moves, it will not be because I cleared the lot.
    """


def internal_notes_md(case: CaseData) -> str:
    return f"""
    # Internal Meeting Notes

    ## Matter Name

    {case.matter_name}

    ## Document Date

    {case.meeting_date}

    ## Document Type

    Internal Meeting Notes

    ## Page 1

    ### Attendees

    - {case.quality_director}
    - {case.plant_manager}
    - {case.dock_supervisor}
    - {case.compliance_manager}
    - {case.account_manager}
    - {case.ops_vp} joined late by phone

    ### Discussion Notes

    - {case.quality_director} said {case.defendant_short} gave a verbal hold on {case.inspect_date} and that no quality release was given on {case.ship_date}.
    - {case.plant_manager} said hold language tied to Exhibit {case.exhibit_number} was seen before the truck left and that {case.dock_supervisor.split()[0]} was told to keep the truck parked unless higher authority cleared it.
    - {case.dock_supervisor} said no clean written release was received and that the dock relied on {case.screen_form_phrase}, dispatch pressure, and the assumption that operations had made a call.
    - {case.account_manager} acknowledged repeated customer pressure and said {case.customer} was threatening a line disruption.

    ## Page 2

    ### Open Issues

    - Final release decision remains unclear.
    - Unclear whether {case.ops_vp} actually gave a verbal release or whether staff inferred approval from silence and customer pressure.
    - Unclear whether the release-form approver field was entered before or after Truck {case.truck_id} departed.
    - Additional review is needed before anyone can say who gave final approval to ship.

    ### Action Items

    1. Preserve system audit logs for the release record.
    2. Confirm whether any voicemail or text messages from {case.ops_vp} still exist.
    3. Prepare contradiction chart comparing discovery responses with later witness testimony.
    """


def root_cause_md(case: CaseData) -> str:
    return f"""
    # Root Cause Memo

    ## Matter Name

    {case.matter_name}

    ## Document Date

    {case.reject_date}

    ## Document Type

    Root Cause Memo

    ## Page 1

    ### Executive Summary

    The available record shows that Lot {case.lot_id} should have remained on hold after the {case.inspect_date} inspection. Even so, Truck {case.truck_id} left the dock on {case.ship_date}. The strongest written evidence of the inspection failure is Exhibit {case.exhibit_number}, supported by the email chain and the later customer rejection.

    ### Preliminary Root Causes

    1. Customer pressure compressed the decision window.
    2. Quality and operations did not share a single documented release workflow.
    3. Dock staff relied on assumptions and incomplete records rather than a final written release.

    ## Page 2

    ### Evidence Comparison

    - Exhibit {case.exhibit_number} and the Nonconformance Report describe the defects as serious enough to justify a hold.
    - The complaint emphasizes delayed communication by {case.defendant_short}, while the answer argues {case.plaintiff_short} knew enough on {case.inspect_date} to stop the shipment.
    - The interrogatory responses say {case.plant_manager} did not review Exhibit {case.exhibit_number} before departure, but {case.plant_manager.split()[0]} later testified that the first page was seen on the evening of {case.inspect_date}.
    - {case.dock_supervisor} recalls seeing {case.screen_form_phrase}, while the Corrective Action Plan notes a later print time and unresolved audit questions.

    ## Page 3

    ### Deposition Prep Topics and Gaps

    - Pin down whether {case.quality_director}'s early evening email was treated as a true stop-ship direction.
    - Determine whether {case.ops_vp} ever gave an actual verbal release or whether others inferred approval.
    - Determine whether the approver field on the Shipment Release Form was entered live or backfilled later.
    - Ask why the dock was allowed to continue staging after repeated hold references.

    ### Unresolved Conclusion

    The record still does not identify the final approving person with confidence. Any assistant answer on that point should abstain rather than guess.
    """


def build_case_files(case: CaseData) -> dict[str, str]:
    return {
        "complaint.md": complaint_md(case),
        "answer-and-affirmative-defenses.md": answer_md(case),
        "interrogatories-and-responses.md": interrogatories_md(case),
        "requests-for-production-and-responses.md": requests_md(case),
        f"{case.deposition_pm_doc_id}.md": deposition_pm_md(case),
        f"{case.deposition_quality_doc_id}.md": deposition_quality_md(case),
        f"{case.deposition_dock_doc_id}.md": deposition_dock_md(case),
        case.exhibit_filename: exhibit_report_md(case),
        "nonconformance-report.md": ncr_md(case),
        "corrective-action-plan.md": capa_md(case),
        "shipment-release-form.md": release_form_md(case),
        "bill-of-lading.md": bill_md(case),
        "customer-rejection-letter.md": rejection_letter_md(case),
        "inspection-email-chain.md": email_chain_md(case),
        "internal-meeting-notes.md": internal_notes_md(case),
        "root-cause-memo.md": root_cause_md(case),
    }


def generate_case(case: CaseData) -> None:
    case_root = SAMPLE_DOCS / case.matter_id
    meta_root = case_root / "_meta"
    retrieval_root = case_root / "_retrieval"
    meta_root.mkdir(parents=True, exist_ok=True)
    retrieval_root.mkdir(parents=True, exist_ok=True)

    for filename, content in build_case_files(case).items():
        write_text(case_root / filename, content)

    write_text(meta_root / "README.md", build_case_readme(case))
    write_text(meta_root / "reference-notes.md", REFERENCE_NOTES)
    write_text(meta_root / "demo-questions.md", build_demo_questions(case))
    metadata = build_case_metadata(case)
    write_text(meta_root / "metadata.json", json.dumps(metadata, indent=2))

    payload = build_chunks(case_root)
    chunks_path = case_chunks_path(case_root)
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    chunks_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    ids = [chunk["chunk_id"] for chunk in payload["chunks"]]
    texts = [chunk["search_text"] for chunk in payload["chunks"]]
    vectors = SentenceTransformerEmbedder().embed_texts(texts)
    embeddings_path = case_embeddings_path(case_root)
    embeddings_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(embeddings_path, ids=np.array(ids, dtype=object), vectors=vectors)


def main() -> None:
    for case in CASES:
        generate_case(case)
        print(f"Generated {case.matter_id}")


if __name__ == "__main__":
    main()
