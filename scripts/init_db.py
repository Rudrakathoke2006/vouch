import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.src.database import engine, Base
from api.src.models import *


async def init_database():
    print("Connecting to PostgreSQL and creating schema tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] All Vouch database tables successfully created in PostgreSQL!")


if __name__ == "__main__":
    asyncio.run(init_database())
