import asyncio
import os
import pytest
from api.src.database import engine
from api.src.models import Base
from api.src.services.payment.factory import reset_payment_provider


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure all database tables are created before running tests."""
    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_init())


@pytest.fixture(autouse=True)
def default_mock_env():
    """Ensure tests run in mock payment and mock LLM provider mode by default."""
    os.environ["PAYMENT_PROVIDER"] = "mock"
    os.environ["LLM_PROVIDER"] = "mock"
    reset_payment_provider()
