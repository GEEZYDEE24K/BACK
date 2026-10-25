"""verificacion de comunidad, dominios institucionales y perfil de usuario extendido

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d92f18a70
Create Date: 2026-10-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "4d5e6f7a8b9c"
down_revision = "3c4d92f18a70"
branch_labels = None
depends_on = None

DOMINIOS_DEFAULT = {
    "unal.edu.co": "Universidad Nacional de Colombia",
    "udea.edu.co": "Universidad de Antioquia",
    "uniandes.edu.co": "Universidad de los Andes",
    "javeriana.edu.co": "Pontificia Universidad Javeriana",
    "univalle.edu.co": "Universidad del Valle",
    "udistrital.edu.co": "Universidad Distrital Francisco José de Caldas",
    "uis.edu.co": "Universidad Industrial de Santander",
    "uninpahu.edu.co": "UNINPAHU",
}


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

    # 1. Columnas de perfil extendido
    if "telefono" not in existentes:
        op.add_column("usuarios", sa.Column("telefono", sa.String(30), nullable=True))
    if "universidad" not in existentes:
        op.add_column("usuarios", sa.Column("universidad", sa.String(150), nullable=True))
    if "semestre" not in existentes:
        op.add_column("usuarios", sa.Column("semestre", sa.Integer(), nullable=True))
    if "foto_url" not in existentes:
        op.add_column("usuarios", sa.Column("foto_url", sa.String(512), nullable=True))
    if "carnet_path" not in existentes:
        op.add_column("usuarios", sa.Column("carnet_path", sa.String(512), nullable=True))
    if "perfil_completo" not in existentes:
        op.add_column(
            "usuarios",
            sa.Column("perfil_completo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        )

    # 2. Verificación de comunidad: agregar columna si no existe o cambiar default a False
    if "verificado_comunidad" not in existentes:
        op.add_column(
            "usuarios",
            sa.Column("verificado_comunidad", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        )
    else:
        if bind.dialect.name == "postgresql":
            op.alter_column("usuarios", "verificado_comunidad", server_default=sa.text("false"))

    # 3. Migración de datos:
    # "La migración debe marcar como no verificados a los usuarios existentes,
    # salvo los que tengan correo de un dominio permitido."
    # Identificar nombres de columnas de email (correo_institucional o email)
    email_col = "correo_institucional" if "correo_institucional" in existentes else ("email" if "email" in existentes else None)
    if not email_col:
        return

    nombre_col = "nombre" if "nombre" in existentes else ("name" if "name" in existentes else None)
    carrera_col = "programa_area" if "programa_area" in existentes else ("carrera" if "carrera" in existentes else None)

    metadata = sa.MetaData()
    metadata.reflect(bind=bind, only=["usuarios"])
    usuarios_table = metadata.tables["usuarios"]

    conn = bind.connect() if hasattr(bind, "connect") else bind
    filas = conn.execute(sa.select(usuarios_table)).fetchall()

    for row in filas:
        row_dict = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
        user_id = row_dict["id"]
        email = (row_dict.get(email_col) or "").lower().strip()
        universidad_actual = row_dict.get("universidad")
        nombre_val = row_dict.get(nombre_col) or ""
        carrera_val = row_dict.get(carrera_col) or ""

        es_verificado = False
        universidad_asignada = universidad_actual

        for dominio, uni_nombre in DOMINIOS_DEFAULT.items():
            if email.endswith(f"@{dominio}") or email.endswith(f".{dominio}"):
                es_verificado = True
                if not universidad_asignada:
                    universidad_asignada = uni_nombre
                break

        perfil_completo = bool(
            str(nombre_val).strip()
            and str(universidad_asignada or "").strip()
            and str(carrera_val).strip()
        )

        update_values = {
            "verificado_comunidad": es_verificado,
            "perfil_completo": perfil_completo,
        }
        if universidad_asignada:
            update_values["universidad"] = universidad_asignada

        conn.execute(
            usuarios_table.update()
            .where(usuarios_table.c.id == user_id)
            .values(**update_values)
        )


def downgrade() -> None:
    bind = op.get_bind()
    existentes = _obtener_columnas_existentes(bind, "usuarios")

    columnas_a_borrar = [
        "carnet_path",
        "foto_url",
        "semestre",
        "perfil_completo",
    ]
    for col in columnas_a_borrar:
        if col in existentes:
            op.drop_column("usuarios", col)

    if "verificado_comunidad" in existentes and bind.dialect.name == "postgresql":
        op.alter_column("usuarios", "verificado_comunidad", server_default=sa.text("true"))
