"""Test fixtures: an in-memory SQLite DB shared across the app + a test client.

The client fixture also injects the offline providers (mock WhatsApp + fake LLM)
so webhook tests exercise the full inbound -> assistant -> send path with no keys.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401  (register tables on Base.metadata)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.providers.llm.factory import get_llm_client
from app.providers.llm.fake import FakeLLMClient, text_response
from app.providers.whatsapp.factory import get_whatsapp_provider
from app.providers.whatsapp.mock import MockWhatsAppProvider


@pytest.fixture
def engine() -> Iterator[Engine]:
    # StaticPool keeps a single connection so the in-memory DB is shared.
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        yield session


@pytest.fixture
def mock_whatsapp() -> MockWhatsAppProvider:
    return MockWhatsAppProvider()


@pytest.fixture
def client(engine: Engine, mock_whatsapp: MockWhatsAppProvider) -> Iterator[TestClient]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_whatsapp_provider] = lambda: mock_whatsapp
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient(
        default=text_response("Sure, I can help with that! 🙂")
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
