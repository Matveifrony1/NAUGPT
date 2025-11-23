import os
import pytest
from unittest.mock import Mock


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Базове тестове оточення для всіх тестів"""
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "ERROR"
    # НЕ чіпаємо тут USE_GEMINI, щоб не ламати поведінку,
    # а LLM будемо мокати окремо глобально.
    yield


@pytest.fixture(autouse=True)
def mock_llm(mocker):
    """
    Глобальний мок для LLM-викликів.

    - Мокаємо Google Gemini (якщо використовується)
    - Мокаємо httpx.AsyncClient, щоб зовнішні HTTP-запити до LM Studio не ходили в інтернет
    """
    # Якщо у тебе немає google.generativeai – це безпечно, просто не буде використовуватись.
    mocker.patch("google.generativeai.GenerativeModel", autospec=True)

    # Заглушка для httpx.AsyncClient, щоб будь-які виклики не йшли назовні
    mock_client_cls = mocker.patch("httpx.AsyncClient", autospec=True)
    client_instance = mock_client_cls.return_value.__aenter__.return_value
    client_instance.post.return_value = Mock(status_code=200, json=lambda: {"choices": []})


@pytest.fixture(autouse=True)
def mock_embeddings(mocker):
    """
    Глобальний мок для embeddings-моделі, щоб НЕ качати справжні моделі
    в тестах, де VectorDatabase створюється без додаткового патчу.
    """
    mock_model = Mock()
    mock_model.encode.return_value = [[0.1] * 1024]

    # Якщо VectorDatabase імпортує так:
    # from sentence_transformers import SentenceTransformer
    # то цього патчу достатньо
    mocker.patch(
        "sentence_transformers.SentenceTransformer",
        return_value=mock_model,
    )
