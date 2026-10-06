import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import Base, engine
import uuid

async def run():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/auth/login", data={"username": "student@example.com", "password": "pass"})
        print("LOGIN:", res.status_code, res.json())
asyncio.run(run())
