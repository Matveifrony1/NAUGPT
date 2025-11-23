import json
import pytest
from unittest.mock import AsyncMock, patch

from query_router import QueryRouter, RouteDecision


class TestQueryRouterWithMocks:
    """Tests for QueryRouter with mocked LLM responses."""

    @pytest.fixture
    def router(self):
        return QueryRouter()

    @pytest.fixture
    def mock_llm_response(self):
        """Standard structured LLM response."""
        return {
            "reasoning": "Test reasoning",
            "search_scope": "ФКНТ",
            "search_level": "department",
            "target_entity": "ІПЗ",
            "search_intent": "info",
            "enhancement_keywords": ["викладач", "професор"],
            "confidence": 0.9,
            "needs_database_search": True,
        }

    # ----------------------------------------------------------------------
    # LLM SUCCESS
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    @patch("query_router.httpx.AsyncClient")
    async def test_llm_routing_success(
        self,
        mock_client,
        router,
        mock_llm_response,
    ):
        """Ensure LLM routing works and returns a RouteDecision."""

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(mock_llm_response)
                    }
                }
            ]
        }

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await router.route_query("Хто викладач ІПЗ?")
        assert isinstance(result, RouteDecision)
        assert result.search_scope == "ФКНТ"
        assert result.target_entity == "ІПЗ"

    # ----------------------------------------------------------------------
    # LLM FAIL → HEURISTIC FALLBACK
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_fallback_to_heuristic_on_llm_failure(self, router):
        """If LLM fails → fallback to heuristic routing."""
        with patch.object(router, "_llm_routing", return_value=None):
            result = await router.route_query("питання про ФКНТ")
            assert isinstance(result, RouteDecision)
            assert result.confidence < 1.0

    # ----------------------------------------------------------------------
    # DIRECT FACULTY MENTION
    # ----------------------------------------------------------------------
    def test_heuristic_routing_with_faculty_mention(self, router):
        """Heuristic routing detects faculty mentions."""
        result = router._heuristic_routing(
            query="Розкажи про ФКНТ",
            history=None,
            group_name=None,
        )

        assert result.search_scope == "ФКНТ"
        assert result.search_level == "faculty"

    # ----------------------------------------------------------------------
    # CONTEXT FROM DIALOG HISTORY
    # ----------------------------------------------------------------------
    def test_context_from_history(self, router):
        """
        Heuristic router must correctly use dialog history.
        NOTE:
            Router CANNOT detect the teacher → department relation
            because NAU_STRUCTURE contains ONLY faculties + departments,
            and no teacher database exists.

            Therefore:
            - It can extract only the faculty (ФКНТ)
            - It CANNOT infer department (ІПЗ)
            - target_entity MUST remain None
        """

        history = [
            {"role": "user", "content": "Хто викладач Малярчук ФКНТ?"},
            {"role": "assistant", "content": "Малярчук"},
        ]

        result = router._heuristic_routing(
            query="А його контакти?",
            history=history,
            group_name=None,
        )

        # Router correctly pulls faculty from context
        assert result.search_scope == "ФКНТ"
        assert result.search_level == "faculty"

        # Router CANNOT infer department → must stay None
        assert result.target_entity is None

        # Intent must be contacts
        assert result.search_intent == "contacts"

        # Reasoning must mention usage of history
        assert "Контекст з історії" in result.reasoning

        # Heuristic ALWAYS returns confidence = 0.5
        assert result.confidence == 0.5
