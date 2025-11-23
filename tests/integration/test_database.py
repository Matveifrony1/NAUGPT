import os
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
import chromadb
from database import VectorDatabase


@pytest.fixture
def db(tmp_path):
    """
    ChromaDB in-memory через EphemeralClient.
    """
    with patch("database.chromadb.PersistentClient") as mock_client_cls:

        # In-memory клиент ChromaDB
        memory_client = chromadb.EphemeralClient()

        test_collection = memory_client.get_or_create_collection("test_collection")

        # Подменяем PersistentClient → EphemeralClient
        mock_client_cls.return_value = memory_client

        # Инициализируем основной DB-класс
        db = VectorDatabase(db_path=str(tmp_path))

        # Но коллекция должна быть наша in-memory
        db.client = memory_client
        db.collection = test_collection

        yield db


@pytest.fixture
def mock_embedding():
    """
    Мокаем SentenceTransformer.encode → возвращает numpy array.
    """
    with patch("database.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.15] * 1024])
        mock_cls.return_value = mock_model
        yield mock_model


def test_add_documents(db, mock_embedding):
    docs = [
        {
            "id": "d1",
            "content": "News about NAU",
            "metadata": {"source": "news", "category": "events"},
        }
    ]

    db.add_documents(docs)

    stored = db.collection.get()

    assert len(stored["ids"]) == 1
    assert stored["ids"][0] == "d1"


def test_search_embedding(db, mock_embedding):
    db.add_documents([
        {
            "id": "111",
            "content": "This is NAU faculty news",
            "metadata": {"source": "news", "category": "info"},
        }
    ])

    results = db.search("facult", top_k=5)

    assert isinstance(results, list)
    assert len(results) > 0
    assert "nau" in results[0]["content"].lower()


def test_update_document(db, mock_embedding):
    db.add_documents([
        {
            "id": "upd",
            "content": "old",
            "metadata": {"source": "news"}
        }
    ])

    db.update_document("upd", new_content="new")

    r = db.collection.get(ids=["upd"])

    assert r["documents"][0] == "new"


def test_export_json(db, mock_embedding, tmp_path):
    out = tmp_path / "exp.json"

    db.add_documents([
        {
            "id": "exp",
            "content": "Export me",
            "metadata": {"source": "news"}
        }
    ])

    db.export_to_json(str(out))

    assert out.exists()
    assert out.stat().st_size > 0
