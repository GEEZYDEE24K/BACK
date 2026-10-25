"""crear tabla usuarios

Revision ID: 1975ea83b712
Revises: 
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa

# Identificadores de revisión de Alembic
revision = "1975ea83b712"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.String(), primary_key=True, index=True),
        sa.Column("email", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("role", sa.String(), default="user", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("telefono", sa.String(), nullable=True),
        sa.Column("carrera", sa.String(), nullable=True),
        sa.Column("universidad", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table("usuarios")
