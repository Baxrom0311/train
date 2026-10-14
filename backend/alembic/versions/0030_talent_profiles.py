"""0030_talent_profiles

Saqlangan nomzod profillari (CONTRACT.md §33): `talent_profiles` jadvali va
mavjud Run'lardan to'ldirish.

To'ldirish hisobi §10.1 qoidalarining shu migratsiyadagi nusxasi (`app.talent.profile`
import qilinmaydi — ilova kodi keyin o'zgarsa ham migratsiya o'zgarmasin).

Revision ID: 0030_talent_profiles
Revises: 0029_error_monitoring
Create Date: 2026-10-14 20:00:00

"""
from collections import defaultdict
from datetime import datetime, timezone
from statistics import fmean
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0030_talent_profiles"
down_revision: Union[str, Sequence[str], None] = "0029_error_monitoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB

# §10.1: profilga kiradigan Run'lar
ELIGIBLE_RUNS = sa.text("""
    SELECT r.id, r.user_id, r.last_activity_at, r.competency_scores,
           r.final_report -> 'overall_score' AS overall_score,
           r.final_report #> '{summary,strengths}' AS strengths,
           s.id AS scenario_id, s.title, s.company_name, s.sector
    FROM runs r
    JOIN scenario_versions v ON v.id = r.scenario_version_id
    JOIN scenarios s ON s.id = v.scenario_id
    WHERE r.status = 'completed'
      AND r.final_report IS NOT NULL
      AND s.owner_company_id IS NULL
      AND r.team_id IS NULL
      AND NOT EXISTS (SELECT 1 FROM certificates c WHERE c.run_id = r.id AND c.revoked_at IS NOT NULL)
""").columns(competency_scores=JSONB, overall_score=JSONB, strengths=JSONB)

BATCH = 500


def _profiles(rows) -> list[dict]:
    best: dict[tuple, dict] = {}
    for row in rows:
        summary = {
            "run_id": str(row.id),
            "scenario_id": str(row.scenario_id),
            "scenario_title": row.title,
            "company_name": row.company_name,
            "sector": row.sector,
            "completed_at": row.last_activity_at,
            "overall_score": row.overall_score,
            "competency_scores": row.competency_scores or {},
            "strengths": list(row.strengths or []),
        }
        key = (row.user_id, row.scenario_id)
        rank = ((summary["overall_score"] or -1), summary["completed_at"])
        if key not in best or rank > ((best[key]["overall_score"] or -1), best[key]["completed_at"]):
            best[key] = summary

    by_user: dict = defaultdict(list)
    for (user_id, _), summary in best.items():
        by_user[user_id].append(summary)

    now = datetime.now(timezone.utc)
    out = []
    for user_id, runs in by_user.items():
        runs.sort(key=lambda r: r["completed_at"], reverse=True)
        scores = [r["overall_score"] for r in runs if r["overall_score"] is not None]
        acc: dict[str, list[float]] = defaultdict(list)
        for r in runs:
            for key, value in r["competency_scores"].items():
                acc[key].append(value)
        out.append({
            "user_id": user_id,
            "overall_score": round(fmean(scores), 1) if scores else None,
            "runs_completed": len(runs),
            "sectors": sorted({r["sector"] for r in runs}),
            "competencies": {k: round(fmean(v), 1) for k, v in sorted(acc.items())},
            "last_completed_at": runs[0]["completed_at"],
            "runs": [{**r, "completed_at": r["completed_at"].isoformat()} for r in runs],
            "updated_at": now,
        })
    return out


def upgrade() -> None:
    table = op.create_table(
        "talent_profiles",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("runs_completed", sa.Integer(), nullable=False),
        sa.Column("sectors", postgresql.ARRAY(sa.String(20)), nullable=False),
        sa.Column("competencies", JSONB, nullable=False),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("runs", JSONB, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_talent_profiles_sectors", "talent_profiles", ["sectors"], postgresql_using="gin")
    op.create_index("ix_talent_profiles_competencies", "talent_profiles", ["competencies"], postgresql_using="gin")
    op.create_index("ix_talent_profiles_overall_score", "talent_profiles", ["overall_score"])
    op.create_index("ix_talent_profiles_last_completed_at", "talent_profiles", ["last_completed_at"])

    profiles = _profiles(op.get_bind().execute(ELIGIBLE_RUNS))
    for i in range(0, len(profiles), BATCH):
        op.bulk_insert(table, profiles[i:i + BATCH])


def downgrade() -> None:
    op.drop_index("ix_talent_profiles_last_completed_at", table_name="talent_profiles")
    op.drop_index("ix_talent_profiles_overall_score", table_name="talent_profiles")
    op.drop_index("ix_talent_profiles_competencies", table_name="talent_profiles")
    op.drop_index("ix_talent_profiles_sectors", table_name="talent_profiles")
    op.drop_table("talent_profiles")
