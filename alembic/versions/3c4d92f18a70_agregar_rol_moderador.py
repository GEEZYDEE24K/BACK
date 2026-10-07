"""agregar rol moderador al enum de usuarios

Revision ID: 3c4d92f18a70
Revises: 1975ea83b712
"""

from alembic import op

revision = "3c4d92f18a70"
down_revision = "1975ea83b712"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rol_enum') THEN
                CREATE TYPE rol_enum AS ENUM ('usuario', 'administrador', 'moderador');
            ELSE
                ALTER TYPE rol_enum ADD VALUE IF NOT EXISTS 'moderador';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely when rows may use them.
    pass
