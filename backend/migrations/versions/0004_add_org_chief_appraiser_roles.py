"""add org chief appraiser roles

Revision ID: 0004_add_org_chief_appraiser_roles
Revises: 0003_product_schema_alignment
Create Date: 2026-06-11 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_add_org_chief_appraiser_roles"
down_revision = "0003_product_schema_alignment"
branch_labels = None
depends_on = None

ROLE_ROWS = [
    (
        "CHIEF_APPRAISER_ZQ",
        "中勤首席评估师",
        "中勤签发审核角色",
        True,
    ),
    (
        "CHIEF_APPRAISER_ZLGJ",
        "中立国际首席评估师",
        "中立国际签发审核角色",
        True,
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "roles" not in inspector.get_table_names():
        return

    roles = sa.table(
        "roles",
        sa.column("code", sa.String(length=64)),
        sa.column("name", sa.String(length=64)),
        sa.column("description", sa.String(length=255)),
        sa.column("is_system_fixed", sa.Boolean()),
    )

    existing_codes = {
        row[0]
        for row in bind.execute(sa.text("SELECT code FROM roles")).fetchall()
    }
    rows_to_insert = [
        {
            "code": code,
            "name": name,
            "description": description,
            "is_system_fixed": is_system_fixed,
        }
        for code, name, description, is_system_fixed in ROLE_ROWS
        if code not in existing_codes
    ]
    if rows_to_insert:
        op.bulk_insert(roles, rows_to_insert)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "roles" not in inspector.get_table_names():
        return

    codes = [row[0] for row in ROLE_ROWS]
    bind.execute(
        sa.text("DELETE FROM roles WHERE code IN :codes").bindparams(
            sa.bindparam("codes", expanding=True)
        ),
        {"codes": codes},
    )
