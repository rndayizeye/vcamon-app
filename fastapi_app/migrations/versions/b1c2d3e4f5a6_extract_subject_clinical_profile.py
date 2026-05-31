"""Extract shared clinical fields into Subject table

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-05-30

Structural change: Case and Partner now own a Subject row that holds all
shared clinical fields (reason_for_exam, treatment, legacy lab slots, symptom
fields, historical_primary_*).  LabResultEntry and SymptomEntry reference
subject_id instead of the dual case_id / partner_id columns.

Migration steps
---------------
1. Create subjects table.
2. For each existing case: insert a subject row (copying clinical fields),
   then set cases.subject_id.
3. For each existing partner:
   - If linked_case_id is set, reuse that case's subject_id.
   - Otherwise insert a new subject row and set partners.subject_id.
4. Add subject_id to lab_results and symptom_entries, populating from the
   now-linked case/partner subjects.
5. Drop the old case_id / partner_id columns from lab_results / symptom_entries.
6. Drop the shared clinical columns from cases and partners.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Shared clinical column definitions reused across create and drop
_SHARED_COLS = [
    sa.Column("reason_for_exam", sa.String(50), nullable=True),
    sa.Column("treatment_date", sa.Date(), nullable=True),
    sa.Column("medical_info", sa.Text(), nullable=True),
    sa.Column("lab_1", sa.String(50), nullable=True),
    sa.Column("lab_2", sa.String(50), nullable=True),
    sa.Column("lab_3", sa.String(100), nullable=True),
    sa.Column("treatment", sa.String(50), nullable=True),
    sa.Column("lesion_type", sa.String(50), nullable=True),
    sa.Column("symptom", sa.String(50), nullable=True),
    sa.Column("symptom_classification", sa.String(50), nullable=True),
    sa.Column("symptom_onset_date", sa.Date(), nullable=True),
    sa.Column("symptom_duration_days", sa.Integer(), nullable=True),
    sa.Column("symptom_ongoing", sa.Boolean(), nullable=True),
    sa.Column("historical_primary_chancre", sa.Boolean(), nullable=True),
    sa.Column("historical_primary_date", sa.Date(), nullable=True),
    sa.Column("lab_1_date", sa.Date(), nullable=True),
    sa.Column("lab_2_date", sa.Date(), nullable=True),
    sa.Column("lab_3_date", sa.Date(), nullable=True),
]

_SHARED_COL_NAMES = [c.name for c in _SHARED_COLS]


def upgrade() -> None:
    # -----------------------------------------------------------------
    # 1. Create subjects table
    # -----------------------------------------------------------------
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        *_SHARED_COLS,
    )

    bind = op.get_bind()

    # -----------------------------------------------------------------
    # 2. Populate subjects from cases; store mapping case_id → subject_id
    # -----------------------------------------------------------------
    cases = bind.execute(
        sa.text(
            "SELECT id, "
            + ", ".join(_SHARED_COL_NAMES)
            + " FROM cases"
        )
    ).fetchall()

    case_to_subject: dict[int, int] = {}
    for row in cases:
        row_dict = dict(row._mapping)
        case_id = row_dict.pop("id")
        result = bind.execute(
            sa.text(
                "INSERT INTO subjects ("
                + ", ".join(_SHARED_COL_NAMES)
                + ") VALUES ("
                + ", ".join(f":{n}" for n in _SHARED_COL_NAMES)
                + ")"
            ),
            row_dict,
        )
        case_to_subject[case_id] = result.lastrowid

    # -----------------------------------------------------------------
    # 3. Add subject_id to cases and populate
    # -----------------------------------------------------------------
    with op.batch_alter_table("cases") as batch_op:
        batch_op.add_column(sa.Column("subject_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_cases_subject_id", "subjects", ["subject_id"], ["id"]
        )

    for case_id, subject_id in case_to_subject.items():
        bind.execute(
            sa.text("UPDATE cases SET subject_id = :sid WHERE id = :cid"),
            {"sid": subject_id, "cid": case_id},
        )

    # -----------------------------------------------------------------
    # 4. Populate subjects from partners; store mapping partner_id → subject_id
    # -----------------------------------------------------------------
    partners = bind.execute(
        sa.text(
            "SELECT id, linked_case_id, "
            + ", ".join(_SHARED_COL_NAMES)
            + " FROM partners"
        )
    ).fetchall()

    partner_to_subject: dict[int, int] = {}
    for row in partners:
        row_dict = dict(row._mapping)
        partner_id = row_dict.pop("id")
        linked_case_id = row_dict.pop("linked_case_id")

        if linked_case_id is not None and linked_case_id in case_to_subject:
            partner_to_subject[partner_id] = case_to_subject[linked_case_id]
        else:
            result = bind.execute(
                sa.text(
                    "INSERT INTO subjects ("
                    + ", ".join(_SHARED_COL_NAMES)
                    + ") VALUES ("
                    + ", ".join(f":{n}" for n in _SHARED_COL_NAMES)
                    + ")"
                ),
                row_dict,
            )
            partner_to_subject[partner_id] = result.lastrowid

    # -----------------------------------------------------------------
    # 5. Add subject_id to partners and populate
    # -----------------------------------------------------------------
    with op.batch_alter_table("partners") as batch_op:
        batch_op.add_column(sa.Column("subject_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_partners_subject_id", "subjects", ["subject_id"], ["id"]
        )

    for partner_id, subject_id in partner_to_subject.items():
        bind.execute(
            sa.text("UPDATE partners SET subject_id = :sid WHERE id = :pid"),
            {"sid": subject_id, "pid": partner_id},
        )

    # -----------------------------------------------------------------
    # 6. Add subject_id to lab_results, populate, drop old FKs
    # -----------------------------------------------------------------
    with op.batch_alter_table("lab_results") as batch_op:
        batch_op.add_column(sa.Column("subject_id", sa.Integer(), nullable=True))

    # Populate subject_id from case_id
    bind.execute(
        sa.text(
            "UPDATE lab_results "
            "SET subject_id = (SELECT subject_id FROM cases WHERE cases.id = lab_results.case_id) "
            "WHERE case_id IS NOT NULL"
        )
    )
    # Populate subject_id from partner_id (for rows where case_id is NULL)
    bind.execute(
        sa.text(
            "UPDATE lab_results "
            "SET subject_id = (SELECT subject_id FROM partners WHERE partners.id = lab_results.partner_id) "
            "WHERE partner_id IS NOT NULL AND subject_id IS NULL"
        )
    )

    with op.batch_alter_table("lab_results") as batch_op:
        batch_op.create_foreign_key(
            "fk_lab_results_subject_id", "subjects", ["subject_id"], ["id"]
        )
        batch_op.drop_column("case_id")
        batch_op.drop_column("partner_id")

    # -----------------------------------------------------------------
    # 7. Add subject_id to symptom_entries, populate, drop old FKs
    # -----------------------------------------------------------------
    with op.batch_alter_table("symptom_entries") as batch_op:
        batch_op.add_column(sa.Column("subject_id", sa.Integer(), nullable=True))

    bind.execute(
        sa.text(
            "UPDATE symptom_entries "
            "SET subject_id = (SELECT subject_id FROM cases WHERE cases.id = symptom_entries.case_id) "
            "WHERE case_id IS NOT NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE symptom_entries "
            "SET subject_id = (SELECT subject_id FROM partners WHERE partners.id = symptom_entries.partner_id) "
            "WHERE partner_id IS NOT NULL AND subject_id IS NULL"
        )
    )

    with op.batch_alter_table("symptom_entries") as batch_op:
        batch_op.create_foreign_key(
            "fk_symptom_entries_subject_id", "subjects", ["subject_id"], ["id"]
        )
        batch_op.drop_column("case_id")
        batch_op.drop_column("partner_id")

    # -----------------------------------------------------------------
    # 8. Drop shared clinical columns from cases and partners
    # -----------------------------------------------------------------
    with op.batch_alter_table("cases") as batch_op:
        for col_name in _SHARED_COL_NAMES:
            batch_op.drop_column(col_name)

    with op.batch_alter_table("partners") as batch_op:
        for col_name in _SHARED_COL_NAMES:
            batch_op.drop_column(col_name)


def downgrade() -> None:
    # -----------------------------------------------------------------
    # Restore shared clinical columns on cases and partners
    # -----------------------------------------------------------------
    with op.batch_alter_table("cases") as batch_op:
        for col in _SHARED_COLS:
            batch_op.add_column(sa.Column(col.name, col.type, nullable=True))

    with op.batch_alter_table("partners") as batch_op:
        for col in _SHARED_COLS:
            batch_op.add_column(sa.Column(col.name, col.type, nullable=True))

    bind = op.get_bind()

    # Restore cases clinical data from subjects
    for col_name in _SHARED_COL_NAMES:
        bind.execute(
            sa.text(
                f"UPDATE cases SET {col_name} = "
                f"(SELECT {col_name} FROM subjects WHERE subjects.id = cases.subject_id)"
            )
        )

    # Restore partners clinical data from subjects
    for col_name in _SHARED_COL_NAMES:
        bind.execute(
            sa.text(
                f"UPDATE partners SET {col_name} = "
                f"(SELECT {col_name} FROM subjects WHERE subjects.id = partners.subject_id)"
            )
        )

    # Restore case_id / partner_id on lab_results
    with op.batch_alter_table("lab_results") as batch_op:
        batch_op.add_column(sa.Column("case_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("partner_id", sa.Integer(), nullable=True))

    bind.execute(
        sa.text(
            "UPDATE lab_results "
            "SET case_id = (SELECT id FROM cases WHERE cases.subject_id = lab_results.subject_id)"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE lab_results "
            "SET partner_id = (SELECT id FROM partners WHERE partners.subject_id = lab_results.subject_id) "
            "WHERE case_id IS NULL"
        )
    )

    with op.batch_alter_table("lab_results") as batch_op:
        batch_op.drop_column("subject_id")

    # Restore case_id / partner_id on symptom_entries
    with op.batch_alter_table("symptom_entries") as batch_op:
        batch_op.add_column(sa.Column("case_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("partner_id", sa.Integer(), nullable=True))

    bind.execute(
        sa.text(
            "UPDATE symptom_entries "
            "SET case_id = (SELECT id FROM cases WHERE cases.subject_id = symptom_entries.subject_id)"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE symptom_entries "
            "SET partner_id = (SELECT id FROM partners WHERE partners.subject_id = symptom_entries.subject_id) "
            "WHERE case_id IS NULL"
        )
    )

    with op.batch_alter_table("symptom_entries") as batch_op:
        batch_op.drop_column("subject_id")

    # Drop subject_id from cases and partners
    with op.batch_alter_table("cases") as batch_op:
        batch_op.drop_column("subject_id")

    with op.batch_alter_table("partners") as batch_op:
        batch_op.drop_column("subject_id")

    # Drop subjects table
    op.drop_table("subjects")
