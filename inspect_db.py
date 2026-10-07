import asyncio
import sqlalchemy as sa
from backend_estudiantil.adapters.db import get_engine

async def inspect():
    engine = get_engine()
    async with engine.connect() as conn:
        res = await conn.execute(sa.text("SELECT column_name, data_type, udt_name FROM information_schema.columns WHERE table_name = 'usuarios' ORDER BY ordinal_position;"))
        for row in res.fetchall():
            print(f"{row[0]}: type={row[1]}, udt={row[2]}")
            
        res_enum = await conn.execute(sa.text("SELECT t.typname, e.enumlabel FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid;"))
        print("\nEnums:")
        for row in res_enum.fetchall():
            print(f"{row[0]}: {row[1]}")

asyncio.run(inspect())
