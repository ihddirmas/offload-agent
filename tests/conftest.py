import pytest

from offload.db import init_db


@pytest.fixture(autouse=True)
async def fresh_db(tmp_path):
    await init_db(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
