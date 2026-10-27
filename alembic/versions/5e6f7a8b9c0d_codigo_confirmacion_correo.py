"""agregar codigo_confirmacion y codigo_confirmacion_expira a usuarios

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-10-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "5e6f7a8b9c0d"
down_revision = "4d5e6f7a8b9c"
branch_labels = None
depends_on = None


def _obtener_columnas_existentes(bind, table_name="usuarios") -> set[str]:
    inspector = Inspector.from_engine(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    existentes = _obtener_columnas_existentes(bind, "usuarios")

    if not existentes:
        return

    if "codigo_confirmacion" not in existentes:
        op.add_column("usuarios", sa.Column("codigo_confirmacion", sa.String(64), nullable=True))

    if "codigo_confirmacion_expira" not in existentes:
        op.add_column("usuarios", sa.Column("codigo_confirmacion_expira", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    existentes = _obtener_columnas_existentes(bind, "usuarios")

    if not existentes:
        return

    if "codigo_confirmacion_expira" in existentes:
        op.drop_column("usuarios", "codigo_confirmacion_expira")

    if "codigo_confirmacion" in existentes:
        op.drop_column("usuarios", "codigo_confirmacion")
