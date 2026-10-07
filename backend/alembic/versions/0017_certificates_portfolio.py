"""0017_certificates_portfolio

Sertifikatlar va portfolio (CONTRACT.md §13): jadvallar, `manage_portfolio`
(student) va `manage_certificates` (admin) ruxsatlari, avval tugagan
Run'lar uchun sertifikatlar.

Revision ID: 0017_certificates_portfolio
Revises: 0016_more_sectors
Create Date: 2026-10-07 21:00:00

"""
import secrets
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0017_certificates_portfolio"
down_revision: Union[str, Sequence[str], None] = "0016_more_sectors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = (
    ("00000000-0000-0000-0000-000000000109", "manage_portfolio", "student"),
    ("00000000-0000-0000-0000-000000000110", "manage_certificates", "admin"),
)
# app.credentials.issue bilan bir xil; migratsiya ilova kodiga bog'lanmaydi
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def _code() -> str:
    body = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return f"TJ-{body[:4]}-{body[4:]}"


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=12), nullable=False, unique=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("holder_name", sa.String(), nullable=False),
        sa.Column("scenario_title", sa.String(length=200), nullable=False),
        sa.Column("company_name", sa.String(length=120), nullable=False),
        sa.Column("sector", sa.String(length=20), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("competency_scores", postgresql.JSONB(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=300), nullable=True),
    )
    op.create_index("ix_certificates_user_id", "certificates", ["user_id"])
    op.create_table(
        "portfolios",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("slug", sa.String(length=40), nullable=False, unique=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("headline", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("about", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("links", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    conn = op.get_bind()
    for perm_id, key, role in PERMISSIONS:
        conn.execute(sa.text("INSERT INTO permissions (id, key) VALUES (:id, :key) ON CONFLICT DO NOTHING"),
                     {"id": perm_id, "key": key})
        conn.execute(sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.name = :role AND p.key = :key ON CONFLICT DO NOTHING"
        ), {"role": role, "key": key})

    # Avval tugagan Run'lar (§13.1)
    rows = conn.execute(sa.text(
        "SELECT r.id, r.user_id, r.last_activity_at, r.final_report->'overall_score' AS score, "
        "       COALESCE(r.competency_scores, r.final_report->'competency_scores', '{}'::jsonb) AS comps, "
        "       u.full_name, s.title, s.company_name, s.sector, s.difficulty, s.duration_days "
        "FROM runs r JOIN users u ON u.id = r.user_id "
        "JOIN scenario_versions v ON v.id = r.scenario_version_id JOIN scenarios s ON s.id = v.scenario_id "
        "WHERE r.status = 'completed' AND (r.final_report->>'certificate')::boolean IS TRUE"
    )).mappings().all()
    used: set[str] = set()
    certificates = sa.table(
        "certificates", *(sa.column(c) for c in (
            "id", "code", "run_id", "user_id", "issued_at", "holder_name", "scenario_title", "company_name",
            "sector", "difficulty", "duration_days", "completed_at", "overall_score", "competency_scores",
        )),
    )
    for r in rows:
        code = _code()
        while code in used:
            code = _code()
        used.add(code)
        score = r["score"]
        conn.execute(certificates.insert().values(
            id=uuid.uuid4(), code=code, run_id=r["id"], user_id=r["user_id"], issued_at=r["last_activity_at"],
            holder_name=r["full_name"], scenario_title=r["title"], company_name=r["company_name"],
            sector=r["sector"], difficulty=r["difficulty"], duration_days=r["duration_days"],
            completed_at=r["last_activity_at"], overall_score=float(score) if score is not None else None,
            competency_scores=sa.cast(sa.literal(r["comps"], postgresql.JSONB()), postgresql.JSONB()),
        ))


def downgrade() -> None:
    conn = op.get_bind()
    for _, key, _ in PERMISSIONS:
        conn.execute(sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE key = :key)"
        ), {"key": key})
        conn.execute(sa.text("DELETE FROM permissions WHERE key = :key"), {"key": key})
    op.drop_table("portfolios")
    op.drop_index("ix_certificates_user_id", table_name="certificates")
    op.drop_table("certificates")
