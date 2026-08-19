import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT email FROM users'))
        print(res.all())

if __name__ == "__main__":
    asyncio.run(check())
