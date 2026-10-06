import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

async def run():
    # just run the test directly via pytest logic, but I can just modify the test to print res.json()
    pass
