import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient

from main import app, system_components


@pytest.fixture
def app_with_mocks():
    """Перекрываем system_components, не трогаем DI."""

    # Фейковая база данных
    mock_db = Mock()
    mock_db.get_stats.return_value = {"total_documents": 123}

    # Фейковый schedule manager
    mock_schedule = Mock()
    mock_schedule.get_current_time_context.return_value = {
        "time": "10:00",
        "day": "Понеділок",
        "week": 1,
    }
    mock_schedule.extract_group_name.return_value = "Б-171-22-1-ІР"
    mock_schedule.load_group_schedule.return_value = {"dummy": "schedule"}
    mock_schedule.search_similar_groups.return_value = ["Б-171-22-1-ІР"]

    # Фейковый ассистент
    mock_assistant = Mock()
    mock_assistant.check_lm_studio = AsyncMock(return_value=True)
    mock_assistant.process_query = AsyncMock(return_value="Test response")

    # Меняем глобальные компоненты
    system_components.clear()
    system_components.update({
        "db": mock_db,
        "schedule_manager": mock_schedule,
        "assistant": mock_assistant
    })

    return app


@pytest.fixture
def client(app_with_mocks):
    return TestClient(app_with_mocks)


class TestChatFlowE2E:

    def test_complete_conversation_flow(self, client):
        """Полный чат-флоу."""

        # health
        health = client.get("/health")
        assert health.status_code == 200

        # первое сообщение
        r1 = client.post(
            "/chat",
            json={
                "user_name": "E2E Test",
                "message": "Привіт!",
                "messages": []
            },
        )
        assert r1.status_code == 200
        assert r1.json()["response"] == "Test response"

        # второе сообщение с историей
        r2 = client.post(
            "/chat",
            json={
                "user_name": "E2E Test",
                "message": "Розкажи про ФКНТ",
                "messages": [
                    {"role": "user", "content": "Привіт!"},
                    {"role": "assistant", "content": r1.json()["response"]},
                ]
            },
        )
        assert r2.status_code == 200
        assert "response" in r2.json()

    def test_group_validation_flow(self, client):
        r = client.post(
            "/group/validate",
            json={"group_name": "Б-171-22-1-ІР"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["is_valid"] is True
        assert data["extracted_name"] == "Б-171-22-1-ІР"

    def test_error_handling_flow(self, client):
        """Невалидный чат-запрос должен вернуть 422."""
        r = client.post(
            "/chat",
            json={
                "user_name": "",
                "message": "",
            },
        )
        assert r.status_code == 422
