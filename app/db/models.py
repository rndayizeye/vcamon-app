"""
app/db/models.py

SQLAlchemy ORM models for the VCA contact tracing application.
Table structure derived from vcamon-launch-v1.xlsm sheets:
  - Case       ← root record (OP sheet + Names sheet)
  - Partner    ← P1 / AddPartner2 sheets
  - MAPEntry   ← MAP / MAPOP / MAP1 sheets (46-item checklist)
  - ArrowLink  ← Arrows sheet (transmission links)
  - Ghosting   ← GhostingSource / GhostingSpread sheets
  - TimelineEvent ← Chart / AddPartner2 calendar columns
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# ---------------------------------------------------------------------------
# Enums — sourced directly from the DropDowns sheet
# ---------------------------------------------------------------------------

class ReasonForExam(str, enum.Enum):
    VOLUNTEER            = "Volunteer"
    P1_TO_710            = "P1 to 710"
    P1_TO_720            = "P1 to 720"
    P1_TO_730            = "P1 to 730"
    CLUSTER_RELATED      = "Cluster Related"
    HEALTH_DEPT_REFERRAL = "Health Dept Referral"
    NOT_YET_INTERVIEWED  = "Not yet interviewed"
    PRE_NATAL_SCREENING  = "Pre-Natal Screening"
    PT_REF               = "Pt Ref"
    SCREENING            = "Screening"
    SELF_REFERRED        = "Self-Referred"


class LabResult(str, enum.Enum):
    """RPR / VDRL titer results from the DropDowns sheet."""
    RPR_NEG      = "RPR Neg"
    RPR_REACTIVE = "RPR Reactive"
    RPR_1_1      = "RPR 1:1"
    RPR_1_2      = "RPR 1:2"
    RPR_1_4      = "RPR 1:4"
    RPR_1_8      = "RPR 1:8"
    RPR_1_16     = "RPR 1:16"
    RPR_1_32     = "RPR 1:32"
    RPR_1_64     = "RPR 1:64"
    RPR_1_128    = "RPR 1:128"
    RPR_1_256    = "RPR 1:256"
    RPR_1_512    = "RPR 1:512"
    RPR_1_1024   = "RPR 1:1024"
    RPR_GT_1024  = "RPR > 1024"
    VDRL_NEG     = "VDRL Neg"
    VDRL_REACTIVE = "VDRL Reactive"
    VDRL_1_1     = "VDRL 1:1"
    VDRL_1_2     = "VDRL 1:2"
    VDRL_1_4     = "VDRL 1:4"
    VDRL_1_8     = "VDRL 1:8"
    VDRL_1_16    = "VDRL 1:16"
    VDRL_1_32    = "VDRL 1:32"
    VDRL_1_64    = "VDRL 1:64"
    VDRL_1_128   = "VDRL 1:128"
    VDRL_1_256   = "VDRL 1:256"
    VDRL_1_512   = "VDRL 1:512"
    VDRL_1_1024  = "VDRL 1:1024"
    VDRL_GT_1024 = "VDRL > 1024"


class TreponemalResult(str, enum.Enum):
    """Confirmatory treponemal test results."""
    TPPA_POS  = "TPPA+"
    TPPA_NEG  = "TPPA-"
    TP_AB_POS = "TP-AB+"
    TP_AB_NEG = "TP-AB-"
    DFKD_POS  = "DFKD+"
    FTA_POS   = "FTA+"
    FTA_NEG   = "FTA-"
    MHATP     = "MHATP"
    OTHER     = "Other"


class Treatment(str, enum.Enum):
    RX_BIC_2_4           = "Rx Bic 2.4"
    RX_BIX_2_4_X3        = "Rx Bix 2.4 x3"
    DOXY_100_14          = "Doxy 100 2x/Day 14 days"
    DOXY_100_28          = "Doxy 100 2x/Day 28 days"
    OTHER                = "Other"


class LesionType(str, enum.Enum):
    ANAL    = "Anal LX"
    LAB     = "Non-genital LX"  # Not a typo — "Lab" is used in the DropDowns
                                # sheet to mean "Lesion, non-genital"
    LX      = "LX"  # Non-specific lesion type (used when exact location
                    # is unknown or not specified)
    ORAL    = "Oral LX"
    PENILE  = "Penile LX"
    RECTAL  = "Rectal LX"
    VAGINAL = "Vaginal LX"


class Symptom(str, enum.Enum):
    RASH     = "Rash"
    PP_RASH  = "PP Rash"
    GB_RASH  = "GB Rash"
    C_LATA   = "C-lata"
    ALOPECIA = "Alopecia"


class SymptomClassification(str, enum.Enum):
    PRIMARY   = "Primary"
    SECONDARY = "Secondary"


class TestCategory(str, enum.Enum):
    NON_TREPONEMAL = "Non-treponemal"
    TREPONEMAL     = "Treponemal"


class GhostingType(str, enum.Enum):
    SOURCE       = "Ghosting a Source"
    SPREAD_GHOST = "Ghosting a Spread Ghost"
    SPREAD       = "Ghosting a Spread"


# ---------------------------------------------------------------------------
# Case  (the original patient / OP)
# ---------------------------------------------------------------------------

class Case(Base):
    """
    Root record. Corresponds to the OP sheet + Names sheet.
    One case = one original patient (OP) with all their associated data.
    """
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Patient identifiers (OP sheet rows 1-2)
    patient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lot: Mapped[str | None] = mapped_column(String(10))        # 700, 710, 720, 730
    case_manager: Mapped[str | None] = mapped_column(String(200))
    initial_contact_date: Mapped[date | None] = mapped_column(Date)

    # OP form fields
    reason_for_exam: Mapped[str | None] = mapped_column(
        Enum(ReasonForExam, name="reason_for_exam_enum")
    )
    treatment_date: Mapped[date | None] = mapped_column(Date)
    medical_info: Mapped[str | None] = mapped_column(Text)

    # Lab results (Legacy 3 slots - keeping for compatibility but will 
    # prefer LabResultEntry)
    lab_1: Mapped[str | None] = mapped_column(
        Enum(LabResult, name="lab_result_1_enum")
    )
    lab_2: Mapped[str | None] = mapped_column(
        Enum(TreponemalResult, name="trep_result_enum")
    )
    lab_3: Mapped[str | None] = mapped_column(
        String(100)
    )    # free-text / "Drfd N/A" logic

    # Treatment
    treatment: Mapped[str | None] = mapped_column(
        Enum(Treatment, name="treatment_enum")
    )
    lesion_type: Mapped[str | None] = mapped_column(
        Enum(LesionType, name="lesion_enum")
    )
    symptom: Mapped[str | None] = mapped_column(
        Enum(Symptom, name="symptom_enum")
    )

    # Clinical details for VCA analysis
    symptom_classification: Mapped[str | None] = mapped_column(
        Enum(SymptomClassification, name="symptom_class_enum")
    )
    symptom_onset_date: Mapped[date | None] = mapped_column(Date)
    symptom_duration_days: Mapped[int | None] = mapped_column(Integer)
    symptom_ongoing: Mapped[bool] = mapped_column(Boolean, default=False)
    
    historical_primary_chancre: Mapped[bool | None] = mapped_column(Boolean)
    historical_primary_date: Mapped[date | None] = mapped_column(Date)

    # Lab dates (Legacy)
    lab_1_date: Mapped[date | None] = mapped_column(Date)
    lab_2_date: Mapped[date | None] = mapped_column(Date)
    lab_3_date: Mapped[date | None] = mapped_column(Date)
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    partners: Mapped[list["Partner"]] = relationship(
        "Partner", back_populates="case", cascade="all, delete-orphan"
    )
    relationships: Mapped[list["CasePartnerRelationship"]] = relationship(
        "CasePartnerRelationship", back_populates="case", cascade="all, delete-orphan"
    )
    map_entries: Mapped[list["MAPEntry"]] = relationship(
        "MAPEntry", back_populates="case", cascade="all, delete-orphan"
    )
    arrow_links: Mapped[list["ArrowLink"]] = relationship(
        "ArrowLink", back_populates="case", cascade="all, delete-orphan"
    )
    ghostings: Mapped[list["Ghosting"]] = relationship(
        "Ghosting", back_populates="case", cascade="all, delete-orphan"
    )
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(
        "TimelineEvent", back_populates="case", cascade="all, delete-orphan"
    )
    lab_results: Mapped[list["LabResultEntry"]] = relationship(
        "LabResultEntry", back_populates="case", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} patient={self.patient_name!r}>"


# ---------------------------------------------------------------------------
# Partner  (P1 sheet + AddPartner2 sheet)
# ---------------------------------------------------------------------------

class Partner(Base):
    """
    A contact partner of the original patient.
    Shares the same field structure as Case (OP form).
    partner_number is 1-based (Partner 1, Partner 2, ...).
    """
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    partner_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3...

    name: Mapped[str | None] = mapped_column(String(200))
    reason_for_exam: Mapped[str | None] = mapped_column(
        Enum(ReasonForExam, name="partner_reason_enum")
    )
    treatment_date: Mapped[date | None] = mapped_column(Date)
    medical_info: Mapped[str | None] = mapped_column(Text)

    lab_1: Mapped[str | None] = mapped_column(
        Enum(LabResult, name="partner_lab1_enum")
    )
    lab_2: Mapped[str | None] = mapped_column(
        Enum(TreponemalResult, name="partner_lab2_enum")
    )
    lab_3: Mapped[str | None] = mapped_column(String(100))

    treatment: Mapped[str | None] = mapped_column(
        Enum(Treatment, name="partner_treatment_enum")
    )
    lesion_type: Mapped[str | None] = mapped_column(
        Enum(LesionType, name="partner_lesion_enum")
    )
    symptom: Mapped[str | None] = mapped_column(
        Enum(Symptom, name="partner_symptom_enum")
    )
    # Clinical details for VCA analysis
    symptom_classification: Mapped[str | None] = mapped_column(
        Enum(SymptomClassification, name="p_symptom_class_enum")
    )
    symptom_onset_date: Mapped[date | None] = mapped_column(Date)
    symptom_duration_days: Mapped[int | None] = mapped_column(Integer)
    symptom_ongoing: Mapped[bool] = mapped_column(Boolean, default=False)

    historical_primary_chancre: Mapped[bool | None] = mapped_column(Boolean)
    historical_primary_date: Mapped[date | None] = mapped_column(Date)

    # Lab dates
    lab_1_date: Mapped[date | None] = mapped_column(Date)
    lab_2_date: Mapped[date | None] = mapped_column(Date)
    lab_3_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="partners")
    relationships: Mapped[list["CasePartnerRelationship"]] = relationship(
        "CasePartnerRelationship",
        back_populates="partner",
        cascade="all, delete-orphan",
    )
    map_entries: Mapped[list["MAPEntry"]] = relationship(
        "MAPEntry", back_populates="partner", cascade="all, delete-orphan"
    )
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(
        "TimelineEvent", back_populates="partner", cascade="all, delete-orphan"
    )
    lab_results: Mapped[list["LabResultEntry"]] = relationship(
        "LabResultEntry", back_populates="partner", cascade="all, delete-orphan"
    )
    symptoms: Mapped[list["SymptomEntry"]] = relationship(
        "SymptomEntry", back_populates="partner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Partner id={self.id} #{self.partner_number} case={self.case_id}>"


# ---------------------------------------------------------------------------
# LabResultEntry (New — for repeatable lab history)
# ---------------------------------------------------------------------------

class LabResultEntry(Base):
    """
    A single laboratory result (RPR, VDRL, or Treponemal).
    Allows multiple historical labs per Case or Partner.
    """
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"))
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"))

    test_category: Mapped[str] = mapped_column(
        Enum(TestCategory, name="test_category_enum"), nullable=False
    )
    test_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    titer: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[str | None] = mapped_column(String(100))
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)

    case: Mapped["Case | None"] = relationship("Case", back_populates="lab_results")
    partner: Mapped["Partner | None"] = relationship(
        "Partner", back_populates="lab_results"
    )

    def __repr__(self) -> str:
        return (
            f"<LabResultEntry id={self.id} "
            f"cat={self.test_category} date={self.collection_date}>"
        )


class SymptomEntry(Base):
    """
    A single symptom or lesion occurrence.
    Allows multiple symptoms per Case or Partner.
    """
    __tablename__ = "symptom_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"))
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"))

    # We use a string for the type to accommodate both LesionType and Symptom enums
    symptom_type: Mapped[str] = mapped_column(String(100), nullable=False)
    classification: Mapped[str | None] = mapped_column(
        Enum(SymptomClassification, name="entry_symptom_class_enum")
    )
    onset_date: Mapped[date | None] = mapped_column(Date)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    ongoing: Mapped[bool] = mapped_column(Boolean, default=False)

    case: Mapped["Case | None"] = relationship("Case", back_populates="symptoms")
    partner: Mapped["Partner | None"] = relationship(
        "Partner", back_populates="symptoms"
    )

    def __repr__(self) -> str:
        return f"<SymptomEntry id={self.id} type={self.symptom_type}>"


# ---------------------------------------------------------------------------
# MAPEntry  (MAP / MAPOP / MAP1 sheets — 46-item assessment checklist)
# ---------------------------------------------------------------------------


class MAPEntry(Base):
    """
    One row in the Major Analytical Points assessment.

    item_number: 1–46 matching the Excel numbering.
    subject: 'OP' or the partner_id (int as string) — mirrors MAPOP vs MAP1.
    p_value / c_value: Previous and Current interview checkboxes.
    notes: free-text comments for that item.

    The 46 items are defined in MAP_ITEMS below — use them to
    render the form UI rather than storing item descriptions in the DB.
    """
    __tablename__ = "map_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"))

    item_number: Mapped[int] = mapped_column(Integer, nullable=False)   # 1–46
    p_value: Mapped[bool] = mapped_column(Boolean, default=False)       # Previous
    c_value: Mapped[bool] = mapped_column(Boolean, default=False)       # Current
    notes: Mapped[str | None] = mapped_column(Text)
    high_priority: Mapped[bool] = mapped_column(Boolean, default=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="map_entries")
    partner: Mapped["Partner | None"] = relationship(
        "Partner", back_populates="map_entries"
    )

    def __repr__(self) -> str:
        return f"<MAPEntry case={self.case_id} item={self.item_number}>"


# ---------------------------------------------------------------------------
# ArrowLink  (Arrows sheet — transmission network)
# ---------------------------------------------------------------------------

class ArrowLink(Base):
    """
    A directed transmission link between two parties.
    from_ref / to_ref use 'OP' or a partner number string ('1', '2', etc.)
    matching the convention in the Arrows sheet.
    """
    __tablename__ = "arrow_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    from_ref: Mapped[str] = mapped_column(String(20), nullable=False)  # 'OP' | '1'..'N'
    to_ref: Mapped[str] = mapped_column(String(20), nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="arrow_links")

    def __repr__(self) -> str:
        return f"<ArrowLink {self.from_ref} -> {self.to_ref} case={self.case_id}>"


# ---------------------------------------------------------------------------
# Ghosting  (GhostingSource + GhostingSpread sheets)
# ---------------------------------------------------------------------------

class Ghosting(Base):
    """
    Tracks ghosted lesion exposure paths.
    ghosting_type distinguishes the three sub-tables from the Excel sheet.
    """
    __tablename__ = "ghostings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)

    ghosting_type: Mapped[str] = mapped_column(
        Enum(GhostingType, name="ghosting_type_enum"), nullable=False
    )
    from_ref: Mapped[str | None] = mapped_column(String(20))   # partner ref or 'OP'
    to_ref: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)

    case: Mapped["Case"] = relationship("Case", back_populates="ghostings")

    def __repr__(self) -> str:
        return f"<Ghosting type={self.ghosting_type} case={self.case_id}>"


# ---------------------------------------------------------------------------
# TimelineEvent  (Chart sheet — calendar activity tracking)
# ---------------------------------------------------------------------------

class TimelineEvent(Base):
    """
    A dated activity entry on the partner timeline calendar.
    Maps to the Chart sheet's monthly day grid.
    """
    __tablename__ = "timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"))

    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str | None] = mapped_column(
        String(100)
    )   # e.g. "Treatment", "Lab"
    notes: Mapped[str | None] = mapped_column(Text)

    case: Mapped["Case"] = relationship("Case", back_populates="timeline_events")
    partner: Mapped["Partner | None"] = relationship(
        "Partner", back_populates="timeline_events"
    )

    def __repr__(self) -> str:
        return f"<TimelineEvent date={self.event_date} case={self.case_id}>"


# ---------------------------------------------------------------------------
# CasePartnerRelationship (new association table for OP-Partner specific data)
# ---------------------------------------------------------------------------

class CasePartnerRelationship(Base):
    __tablename__ = "case_partner_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), nullable=False)

    # Relationship-specific clinical details (Consensus Narrative)
    exposure_first_date: Mapped[date | None] = mapped_column(Date)
    exposure_last_date: Mapped[date | None] = mapped_column(Date)
    sex_types: Mapped[str | None] = mapped_column(String(200)) # JSON array

    case: Mapped["Case"] = relationship("Case", back_populates="relationships")
    partner: Mapped["Partner"] = relationship("Partner", back_populates="relationships")
    reports: Mapped[list["RelationshipReport"]] = relationship(
        "RelationshipReport",
        back_populates="relationship",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("case_id", "partner_id", name="uq_case_partner_relationship"),
    )

    def __repr__(self) -> str:
        return (
            f"<CasePartnerRelationship case={self.case_id} "
            f"partner={self.partner_id}>"
        )


class RelationshipReport(Base):
    """
    Stores a specific report of relationship details provided by a reporter.
    This serves as the 'evidence' for the consensus narrative in
    CasePartnerRelationship.
    """
    __tablename__ = "relationship_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    relationship_id: Mapped[int] = mapped_column(
        ForeignKey("case_partner_relationships.id"), nullable=False
    )

    reporter: Mapped[str] = mapped_column(
        String(100), nullable=False
    ) # e.g. "OP", "Partner 1"
    exposure_first_date: Mapped[date | None] = mapped_column(Date)
    exposure_last_date: Mapped[date | None] = mapped_column(Date)
    sex_types: Mapped[str | None] = mapped_column(String(200)) # JSON array

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    relationship: Mapped["CasePartnerRelationship"] = relationship(
        "CasePartnerRelationship", back_populates="reports"
    )

    def __repr__(self) -> str:
        return (
            f"<RelationshipReport rel_id={self.relationship_id} "
            f"reporter={self.reporter!r}>"
        )


# ---------------------------------------------------------------------------
# MAP_ITEMS — reference data (not a DB table)
# Used by the Streamlit UI to render the 46-item MAP checklist.
# Sourced from MAP sheet rows 9-36.
# ---------------------------------------------------------------------------

MAP_ITEMS: dict[int, dict] = {
    # --- Patient Assessment: Social History ---
    1:  {"section": "Social History",    "label": "Confirm Address"},
    2:  {"section": "Social History",    "label": "Time In Area/At Address"},
    3:  {"section": "Social History",    "label": "Ix Period Travel"},
    4:  {"section": "Social History",    "label": "Marital Status/Living With"},
    5:  {"section": "Social History",    "label": "Life Style (Hangouts/"
            "Social Activities)"},
    6:  {"section": "Social History",    "label": "E-Mail Address"},
    7:  {"section": "Social History",    "label": "Internet Activities/Info "
            "(Screen names, web sites)"},
    8:  {"section": "Social History",    "label": ""},
    9:  {"section": "Social History",    "label": ""},
    10: {"section": "Social History",    "label": ""},
    # --- Patient Assessment: Medical History ---
    11: {"section": "Medical History",   "label": "Lesion History/Ghosted Lesion"},
    12: {"section": "Medical History",   "label": "Reason for Exam"},
    13: {"section": "Medical History",   "label": "STD History (GC, CT, Labs, RV)"},
    14: {"section": "Medical History",   "label": "Self Rx"},
    15: {"section": "Medical History",   "label": "General Medical "
            "(Medications, Illnesses, Hospitalizations)"},
    16: {"section": "Medical History",   "label": "Patient's Understanding of "
            "Medical Aspects of Infection"},
    17: {"section": "Medical History",   "label": "Illogical Aspects (Lesion, "
            "Lesion Hx, Lab Results)"},
    18: {"section": "Medical History",   "label": "Drug Use (Concealed, Unclear, "
            "Downplayed)"},
    19: {"section": "Medical History",   "label": ""},
    20: {"section": "Medical History",   "label": ""},
    # --- Disease Intervention: Partners ---
    21: {"section": "Partners",          "label": "Exposure Gap"},
    22: {"section": "Partners",          "label": "Exposure Inconsistencies "
            "(Doesn't match what partners say)"},
    23: {"section": "Partners",          "label": "No Partners Named During Lesion"},
    24: {"section": "Partners",          "label": "Unexplained Change in Sexual "
            "Activity or Pattern"},
    25: {"section": "Partners",          "label": "No 'Steady' Partner Named"},
    26: {"section": "Partners",          "label": "Challenge Claims of Anonymous "
            "Partners Only"},
    27: {"section": "Partners",          "label": "Partners Met on the Internet"},
    28: {"section": "Partners",          "label": "Source or Source Candidates"},
    29: {"section": "Partners",          "label": "Locating on Open Partners/Suspects"},
    30: {"section": "Partners",          "label": "Locating on Marginal Partners"},
    31: {"section": "Partners",          "label": "Partners of Same Sex"},
    32: {"section": "Partners",          "label": ""},
    # --- Disease Intervention: Clusters ---
    33: {"section": "Clusters",          "label": "OP Not Being Named by Partners"},
    34: {"section": "Clusters",          "label": "A2s/SC2s to OP Identified"},
    35: {"section": "Clusters",          "label": "OP Named by Previously "
            "Unnamed Partners"},
    36: {"section": "Clusters",          "label": "SC2s to Other Cases"},
    37: {"section": "Clusters",          "label": "Were symptoms of OP Observed?"},
    38: {"section": "Clusters",          "label": ""},
    # --- Disease Intervention: Risk Reduction ---
    39: {"section": "Risk Reduction",    "label": "Established Risk Reduction Plan"},
    40: {"section": "Risk Reduction",    "label": ""},
    # --- Other ---
    41: {"section": "Other",             "label": "Commitments Made to/by OP"},
    42: {"section": "Other",             "label": "Missing IR Elements"},
    43: {"section": "Other",             "label": ""},
    44: {"section": "Other",             "label": ""},
    45: {"section": "Other",             "label": ""},
    46: {"section": "Other",             "label": ""},
}