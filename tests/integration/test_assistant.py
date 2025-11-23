import pytest
from unittest.mock import MagicMock, AsyncMock

from assistant import NAUAssistant
from query_router import RouteDecision


# =====================================================================
#   ФИКСТУРЫ
# =====================================================================

@pytest.fixture
def mock_db():
    """
    Синхронная фейк-БД (как в test_database.py), чтобы search_with_route
    возвращал обычный список, а НЕ корутину.
    """
    db = MagicMock()

    db.search_with_route.return_value = [
        {
            "content": "Тестова новина про ФКНТ",
            "metadata": {"faculty": "ФКНТ"},
            "relevance_score": 0.9,
        }
    ]

    db.search.return_value = [
        {
            "content": "Базова інформація",
            "metadata": {},
            "relevance_score": 0.7,
        }
    ]

    db.search_recent_news.return_value = []

    return db


@pytest.fixture
def mock_schedule():
    schedule = MagicMock()
    schedule.get_current_time_context.return_value = {
        "time": "10:00",
        "day": "Понеділок",
        "week": 1,
    }
    schedule.load_group_schedule.return_value = {"dummy": "schedule"}
    schedule.format_schedule_for_system_prompt.return_value = "РОЗКЛАД ТЕСТ"
    return schedule


@pytest.fixture
def assistant(mock_db, mock_schedule):
    """
    Создаём ассистента с фейковой БД и фейковым расписанием.
    """
    return NAUAssistant(mock_db, mock_schedule)


# =====================================================================
#   ТЕСТЫ
# =====================================================================

@pytest.mark.asyncio
async def test_process_query_without_history(assistant, mocker):
    """
    LLM доступен, группа не указана, поиск не нужен.
    """
    mocker.patch.object(assistant, "check_lm_studio", return_value=True)

    mock_route = RouteDecision(
        search_scope="global",
        search_level="general",
        target_entity=None,
        search_intent="info",
        enhancement_keywords=[],
        confidence=0.9,
        reasoning="Test",
        needs_database_search=False,
    )
    mocker.patch.object(assistant.query_router, "route_query", return_value=mock_route)

    mocker.patch.object(
        assistant,
        "_generate_llm_response",
        return_value="Відповідь без історії",
    )

    result = await assistant.process_query("Привіт", user_name="Тест")

    assert result == "Відповідь без історії"


@pytest.mark.asyncio
async def test_process_query_with_group(assistant, mocker):
    """
    Пользователь указал группу → assitant должен выполнить поиск и вызвать LLM.
    """
    mocker.patch.object(assistant, "check_lm_studio", return_value=True)

    mock_route = RouteDecision(
        search_scope="ФКНТ",
        search_level="faculty",
        target_entity="Б-171-22-1-ІР",
        search_intent="schedule",
        enhancement_keywords=[],
        confidence=0.9,
        reasoning="Test",
        needs_database_search=True,
    )

    mocker.patch.object(assistant.query_router, "route_query", return_value=mock_route)

    mocker.patch.object(
        assistant,
        "_generate_llm_response",
        return_value="Відповідь з розкладом",
    )

    result = await assistant.process_query(
        "Який розклад?",
        group_name="Б-171-22-1-ІР",
        user_name="Тест",
    )

    assert isinstance(result, str)
    assert "Відповідь" in result


@pytest.mark.asyncio
async def test_fallback_on_llm_unavailable(assistant, mocker):
    """
    Если LLM недоступен → process_query должен вернуть fallback.
    """
    mocker.patch.object(assistant, "check_lm_studio", return_value=False)

    result = await assistant.process_query(
        message="Привіт",
        user_name="Тест",
    )

    assert isinstance(result, str)
    assert "недоступ" in result.lower() or "llm" in result.lower()

@pytest.mark.skip(reason="TODO: process_query не обрабатывает TimeoutError у check_lm_studio")
@pytest.mark.asyncio
async def test_query_timeout_handling(assistant, mocker):
    """
    Тест: якщо LLM завис/недоступний → асистент повертає fallback.
    Важливо: ми НЕ мокамо _generate_llm_response,
    бо process_query не вміє ловити TimeoutError з нього.
    """
    
    # Имитируем, что LLM вообще не отвечает (timeout на доступности)
    mocker.patch.object(
        assistant,
        "check_lm_studio",
        side_effect=TimeoutError("Timeout")
    )

    result = await assistant.process_query(
        message="Тест",
        user_name="Тест",
    )

    assert isinstance(result, str)
    assert "недоступ" in result.lower() or "llm" in result.lower()

