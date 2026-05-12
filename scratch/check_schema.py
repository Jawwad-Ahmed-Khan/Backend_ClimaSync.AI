import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check_schema():
    async with engine.connect() as conn:
        for table in ["audit_logs", "conversations", "messages"]:
            print(f"\nChecking table: {table}")
            try:
                result = await conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"))
                columns = [row[0] for row in result.fetchall()]
                if columns:
                    print(f"Columns: {', '.join(columns)}")
                else:
                    print("Table does not exist.")
            except Exception as e:
                print(f"Error checking {table}: {e}")

if __name__ == "__main__":
    asyncio.run(check_schema())
