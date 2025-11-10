"""
NAU AI Assistant Backend - Result Validator
Валідація та ре-ранжування результатів пошуку з автоматичною переформулюванням
"""

import httpx
import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from config import settings
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationDecision:
    """Рішення валідатора"""
    is_relevant: bool  # Чи є результати релевантними
    selected_indices: List[int]  # Індекси обраних результатів (1-3)
    confidence: float  # Впевненість 0-1
    reasoning: str  # Пояснення рішення
    needs_reformulation: bool  # Чи потрібно переформулювати запит
    reformulated_query: Optional[str] = None  # Новий запит для embedding якщо потрібно
    reformulation_strategy: Optional[str] = None  # Стратегія переформулювання


class ResultValidator:
    """
    Валідатор результатів пошуку з розумним переформулюванням
    """
    
    def __init__(self):
        """Ініціалізація"""
        if settings.USE_GEMINI:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
            self.lm_studio_url = None
        else:
            self.lm_studio_url = "http://localhost:1234/v1/chat/completions"
            self.gemini_model = None
            
        self.max_retries = 2
    
    async def validate_and_select(
        self, 
        original_query: str,
        search_results: List[Dict],
        route_reasoning: str,
        attempt: int = 1
    ) -> Tuple[ValidationDecision, List[Dict]]:
        """
        Валідує результати та вибирає найкращі
        
        Args:
            original_query: оригінальний запит користувача
            search_results: результати з БД (топ-6)
            route_reasoning: пояснення від Query Router про що очікується
            attempt: номер спроби (для рекурсії)
        
        Returns:
            (ValidationDecision, відфільтровані результати з повним контентом)
        """
        
        logger.debug(f"🔍 ВАЛІДАЦІЯ (спроба {attempt}): query='{original_query[:50]}...', results={len(search_results)}")
        logger.debug(f"🎯 ОЧІКУВАННЯ ROUTER: {route_reasoning}")
        
        # Готуємо скорочені версії для аналізу
        summarized_results = self._summarize_results(search_results)
        
        # Викликаємо LLM для аналізу
        decision = await self._llm_validation(
            original_query=original_query,
            summarized_results=summarized_results,
            route_reasoning=route_reasoning,
            attempt=attempt
        )
        
        logger.debug(f"✅ РІШЕННЯ ВАЛІДАТОРА: relevant={decision.is_relevant}, "
              f"selected={decision.selected_indices}, needs_reformulation={decision.needs_reformulation}")
        
        if decision.reformulated_query:
            logger.debug(f"🔄 СТРАТЕГІЯ: {decision.reformulation_strategy}")
            logger.debug(f"🔄 НОВИЙ ЗАПИТ: '{decision.reformulated_query}'")
        
        # Якщо нерелевантні та потрібна переформулювання - повертаємо пусті результати
        # Основна логіка повторного пошуку буде в assistant.py
        if decision.needs_reformulation and attempt < self.max_retries:
            return decision, []
        
        # Якщо все ок - повертаємо обрані результати з ПОВНИМ контентом
        if decision.is_relevant and decision.selected_indices:
            selected_results = [
                search_results[i-1]  # -1 бо LLM дає 1-based індекси
                for i in decision.selected_indices 
                if 1 <= i <= len(search_results)
            ]
            return decision, selected_results
        
        # Якщо нічого не підійшло навіть після переформулювання
        logger.error(f"❌ ВАЛІДАЦІЯ: жодних релевантних результатів не знайдено")
        return decision, []
    
    def _summarize_results(self, results: List[Dict], max_chars: int = 150) -> List[Dict]:
        """Створює скорочені версії результатів для аналізу"""
        summarized = []
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            
            # Скорочений контент
            short_content = content[:max_chars] + "..." if len(content) > max_chars else content
            
            summarized.append({
                "index": i,
                "title": metadata.get("title", "Без заголовка"),
                "content_preview": short_content,
                "faculty": metadata.get("faculty"),
                "department": metadata.get("department"),
                "category": metadata.get("category"),
                "news_type": metadata.get("news_type"),
                "relevance_score": result.get("relevance_score", 0),
                "search_type": result.get("search_type", "unknown")
            })
        
        return summarized
    
    async def _llm_validation(
        self, 
        original_query: str, 
        summarized_results: List[Dict],
        route_reasoning: str,
        attempt: int,
        max_retries: int = 3
    ) -> ValidationDecision:
        """
        Виклик LLM для валідації результатів з автоматичними retry
        
        Args:
            max_retries: максимум попыток при ошибках JSON (по умолчанию 3)
        """
        
        system_prompt = self._build_validation_prompt()
        
        # Форматуємо результати
        results_text = "\n\n".join([
            f"📄 РЕЗУЛЬТАТ #{r['index']}:\n"
            f"Заголовок: {r['title']}\n"
            f"Факультет: {r.get('faculty', 'Не вказано')}\n"
            f"Кафедра: {r.get('department', 'Не вказано')}\n"
            f"Категорія: {r.get('category', 'Не вказано')}\n"
            f"Тип: {r.get('news_type', 'Не вказано')}\n"
            f"Релевантність (БД): {r['relevance_score']:.2f}\n"
            f"Тип пошуку: {r.get('search_type', 'unknown')}\n"
            f"Превью контенту:\n{r['content_preview']}"
            for r in summarized_results
        ])
        
        user_message = f"""ОРИГІНАЛЬНИЙ ЗАПИТ КОРИСТУВАЧА: "{original_query}"

    ЩО ОЧІКУЄТЬСЯ (від Query Router):
    {route_reasoning}

    СПРОБА ПОШУКУ: {attempt} з {self.max_retries}

    РЕЗУЛЬТАТИ ПОШУКУ В БД ({len(summarized_results)} документів):

    {results_text}

    ---

    Проаналізуй чи відповідають ці результати ОЧІКУВАННЯМ від Query Router та ЗАПИТУ користувача.

    ВАЖЛИВО:
    - Якщо жодного релевантного результату - ПЕРЕФОРМУЛЮЙ запит для embedding
    - При переформулюванні СПРОЩУЙ: видаляй зайві слова ("контакти", "інформація"), залишай суть (ім'я, назву)
    - Якщо шукали "контакти Іванова" і не знайшли - шукай просто "Іванов викладач"
    - Якщо шукали конкретну подію і не знайшли - шукай більш загально

    Відповідай ТІЛЬКИ JSON:
    {{
      "reasoning": "Пояснення",
      "is_relevant": true/false,
      "selected_indices": [1, 2],
      "confidence": 0.85,
      "needs_reformulation": false,
      "reformulated_query": null,
      "reformulation_strategy": null
    }}"""

        # ✅ RETRY LOOP
        for retry_attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"🤖 ВАЛІДАТОР LLM: спроба {retry_attempt}/{max_retries}")
                
                # ========== ЗАМІНА НА GEMINI ==========
                if settings.USE_GEMINI:
                    import google.generativeai as genai
                    
                    full_prompt = f"{system_prompt}\n\n{user_message}"
                    
                    response = self.gemini_model.generate_content(
                        full_prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.3,
                            max_output_tokens=1000,
                        )
                    )
                    
                    llm_response = response.text
                    logger.debug(f"🤖 ВАЛІДАТОР ВІДПОВІВ: {llm_response}")
                    
                    # ✅ ПАРСИНГ JSON
                    parsed = self._extract_json_from_llm(llm_response)
                    
                    if parsed:
                        # ✅ УСПЕШНО РАСПАРСИЛИ
                        logger.debug(f"✅ JSON успішно розпарсений на спробі {retry_attempt}")
                        
                        return ValidationDecision(
                            is_relevant=parsed.get("is_relevant", False),
                            selected_indices=parsed.get("selected_indices", []),
                            confidence=parsed.get("confidence", 0.0),
                            reasoning=parsed.get("reasoning", ""),
                            needs_reformulation=parsed.get("needs_reformulation", False),
                            reformulated_query=parsed.get("reformulated_query"),
                            reformulation_strategy=parsed.get("reformulation_strategy")
                        )
                    else:
                        # ❌ НЕ СМОГЛИ РАСПАРСИТЬ - RETRY
                        logger.warning(f"⚠️ Валідатор (спроба {retry_attempt}): не вдалося розпарсити JSON")
                        if retry_attempt < max_retries:
                            logger.debug(f"🔄 Повторна спроба валідації...")
                            continue  # ← ПОВТОРЯЕМ
                        else:
                            # ❌ ВСЕ ПОПЫТКИ ПРОВАЛИЛИСЬ - FALLBACK
                            logger.error(f"❌ Вичерпано спроби ({max_retries}), fallback на базове рішення")
                            return ValidationDecision(
                                is_relevant=len(summarized_results) > 0,
                                selected_indices=[1, 2, 3] if len(summarized_results) >= 3 else list(range(1, len(summarized_results) + 1)),
                                confidence=0.3,
                                reasoning="Fallback: LLM не зміг розпарсити JSON після всіх спроб",
                                needs_reformulation=False,
                                reformulated_query=None,
                                reformulation_strategy=None
                            )
                
                # ========== СТАРИЙ КОД ДЛЯ LM STUDIO ==========
                else:
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        response = await client.post(
                            self.lm_studio_url,
                            json={
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_message}
                                ],
                                "temperature": 0.3,
                                "max_tokens": 1000
                            }
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            llm_response = data["choices"][0]["message"]["content"]
                            logger.debug(f"🤖 ВАЛІДАТОР ВІДПОВІВ: {llm_response[:300]}...")
                            
                            # ✅ ПАРСИНГ JSON
                            parsed = self._extract_json_from_llm(llm_response)
                            
                            if parsed:
                                # ✅ УСПЕШНО РАСПАРСИЛИ
                                logger.debug(f"✅ JSON успішно розпарсений на спробі {retry_attempt}")
                                
                                return ValidationDecision(
                                    is_relevant=parsed.get("is_relevant", False),
                                    selected_indices=parsed.get("selected_indices", []),
                                    confidence=parsed.get("confidence", 0.0),
                                    reasoning=parsed.get("reasoning", ""),
                                    needs_reformulation=parsed.get("needs_reformulation", False),
                                    reformulated_query=parsed.get("reformulated_query"),
                                    reformulation_strategy=parsed.get("reformulation_strategy")
                                )
                            else:
                                # ❌ НЕ СМОГЛИ РАСПАРСИТЬ - RETRY
                                logger.warning(f"⚠️ Валідатор (спроба {retry_attempt}): не вдалося розпарсити JSON")
                                if retry_attempt < max_retries:
                                    logger.debug(f"🔄 Повторна спроба валідації...")
                                    continue  # ← ПОВТОРЯЕМ
                                else:
                                    # ❌ ВСЕ ПОПЫТКИ ПРОВАЛИЛИСЬ - FALLBACK
                                    logger.error(f"❌ Вичерпано спроби ({max_retries}), fallback на базове рішення")
                                    return ValidationDecision(
                                        is_relevant=len(summarized_results) > 0,
                                        selected_indices=[1, 2, 3] if len(summarized_results) >= 3 else list(range(1, len(summarized_results) + 1)),
                                        confidence=0.3,
                                        reasoning="Fallback: LLM не зміг розпарсити JSON після всіх спроб",
                                        needs_reformulation=False,
                                        reformulated_query=None,
                                        reformulation_strategy=None
                                    )
                        else:
                            logger.warning(f"⚠️ Валідатор (спроба {retry_attempt}): HTTP {response.status_code}")
                            if retry_attempt < max_retries:
                                continue
                            # Fallback
                            return ValidationDecision(
                                is_relevant=False,
                                selected_indices=[],
                                confidence=0.0,
                                reasoning=f"HTTP error {response.status_code}",
                                needs_reformulation=False
                            )
                            
            except Exception as e:
                logger.error(f"⚠️ Валідатор (спроба {retry_attempt}): помилка {e}")
                if retry_attempt < max_retries:
                    logger.debug(f"🔄 Повторна спроба валідації...")
                    continue
                # Fallback на останній спробі
                return ValidationDecision(
                    is_relevant=False,
                    selected_indices=[],
                    confidence=0.0,
                    reasoning=f"Exception: {str(e)}",
                    needs_reformulation=False
                )
        
        # Цей код ніколи не виконається, але для безпеки
        return ValidationDecision(
            is_relevant=False,
            selected_indices=[],
            confidence=0.0,
            reasoning="Unknown error in retry loop",
            needs_reformulation=False
        )
    
    def _build_validation_prompt(self) -> str:
        return """You are an expert validation system for NAU search results.

YOUR TASK:
1. Analyze if DB results ACTUALLY match what is expected
2. Select 1-3 BEST results for response
3. If results are irrelevant - REFORMULATE query for embedding search

━━━━
🎯 VALIDATION RULES
━━━━

✅ RESULT IS RELEVANT IF:
- Matches query TOPIC and Router EXPECTATIONS
- Contains information about CORRECT person/event/place
- Correct CONTEXT (faculty/department)
- Not outdated (if query is about "recent")

❌ RESULT IS IRRELEVANT IF:
- Completely different topic
- Different person with same name
- Wrong faculty/department
- Outdated data when fresh is needed

━━━━
🔄 REFORMULATION STRATEGIES (CRITICALLY IMPORTANT!)
━━━━

Embedding search works POORLY with overly specific queries!

🚫 DOESN'T WORK: "контакти Іванова Петра Степановича email телефон кафедра ІПЗ"
✅ WORKS: "Іванов Петро Степанович кафедра викладач"

🚫 DOESN'T WORK: "реквізити для оплати навчання банківські дані рахунок"
✅ WORKS: "оплата навчання реквізити банківські"

🚫 DOESN'T WORK: "остання конференція політ дата проведення учасники програма"
✅ WORKS: "конференція політ"

**GOLDEN RULE:** SIMPLER and MORE GENERAL → BETTER embedding will find!

STRATEGIES:

1. **"enrich_person"** - enrich for people
   - Add: "викладач доцент професор персонал завідувач"
   - Add faculty/department if available
   - "Малярчук" → "Малярчук викладач доцент професор"

2. **"enrich_event"** - enrich for events
   - Add: "подія захід конференція семінар"
   - "політ" → "політ конференція захід НАУ ФКНТ"

3. **"enrich_contacts"** - enrich contacts
   - Add: "контакти email телефон зв'язок"
   - "КСМ" → "КСМ контакти email телефон кафедра"

4. **"generalize_topic"** - generalize topic
   - Was: "стипендія соціальна допомога підтримка студентів умови"
   - Became: "стипендія студенти"

5. **"expand_scope"** - expand scope
   - When: confidence < 0.7 or empty
   - Remove narrow constraints, add broader context
   - "Туруй КСМ статті" → "Туруй ФКНТ викладач публікації дослідження статті"

6. **"add_synonyms"** - add topic synonyms
   - "статті" = "публікації дослідження наукові роботи"
   - "контакти" = "email телефон зв'язок адреса"

━━━━
📋 EXAMPLES
━━━━

EXAMPLE 1: Teacher not found
Query: "скажи его номер"
Router Expectations: "Контакти Малярчука з КСМ"
Router confidence: 0.75
Results: random news, not about Malyarchuk

Decision:
{
  "reasoning": "Analyzing search results... See that Router expects Malyarchuk's contacts from KSM. Looking at results: there's news about KSM, but nothing about Malyarchuk. This means query was too complex for embedding. Solution: simplifying query - adding synonyms 'викладач', 'доцент', 'професор' and context 'КСМ ФКНТ'. Also adding word 'контакти' to find contact info.",
  "is_relevant": false,
  "selected_indices": [],
  "confidence": 0.2,
  "needs_reformulation": true,
  "reformulated_query": "Малярчук викладач доцент професор КСМ ФКНТ персонал контакти",
  "reformulation_strategy": "enrich_person"
}

---

EXAMPLE 2: Article not found - narrow scope
Query: "найди статтю Туруя"
Router Expectations: "Публікації Туруя з КСМ"
Router confidence: 0.6, target_entity: "КСМ"
Results: general info about KSM, nothing about articles

Decision:
{
  "reasoning": "Thinking... Router has low confidence (0.6) and limited search to KSM only. Results: there are materials about department, but no mention of Turuy's articles. Maybe Turuy is not from KSM, or his articles are not within department scope. Solution: expanding scope from KSM to entire FKNT + adding synonyms 'публікації', 'дослідження', 'наукові роботи'. This will increase chances of finding.",
  "is_relevant": false,
  "selected_indices": [],
  "confidence": 0.3,
  "needs_reformulation": true,
  "reformulated_query": "Туруй ФКНТ викладач публікації дослідження статті наукові роботи",
  "reformulation_strategy": "expand_scope"
}

---

EXAMPLE 3: Found event, but few details
Query: "коли була конференція політ"
Results:
  #1 - Brief mention of Polit in FKNT news
  #2 - Department history (has word "політ")
  #3 - Sports news

Decision:
{
  "reasoning": "Analyzing results... Result #1 mentions Polit, but very briefly. Result #2 - not about conference at all. Result #3 - off topic. Conclusion: embedding found something, but too superficially. Need details about event - date, program. Solution: enriching query with event context + synonyms 'захід', 'семінар', adding that it's НАУ ФКНТ.",
  "is_relevant": false,
  "selected_indices": [],
  "confidence": 0.4,
  "needs_reformulation": true,
  "reformulated_query": "конференція політ захід семінар НАУ ФКНТ дата програма",
  "reformulation_strategy": "enrich_event"
}

---

EXAMPLE 4: Found CORRECTLY - no need to reformulate
Query: "контакти Іванова"
Results:
  #1 - Ivanov P.S., head of IPZ, email: ivanov@..., tel: +380...
  #2 - Ivanova O.M., associate professor KIT
  #3 - IPZ history

Decision:
{
  "reasoning": "Looking at results... Result #1 - PERFECT: Ivanov P.S., head of IPZ, has full contacts (email, phone). This is exactly what's needed! Result #2 - different person (Ivanova is female). Result #3 - historical reference, not relevant. Conclusion: first result fully matches query, additional ones not needed. Selecting only #1.",
  "is_relevant": true,
  "selected_indices": [1],
  "confidence": 0.95,
  "needs_reformulation": false,
  "reformulated_query": null,
  "reformulation_strategy": null
}

━━━━
⚠️ CRITICALLY IMPORTANT: RESPONSE FORMAT
━━━━

🎯 **MANDATORY FIELD ORDER:**

1. **reasoning** - ALWAYS FIRST FIELD! Here you think aloud BEFORE making decision
2. Then all other fields

**JSON FORMAT (reasoning FIRST!):**

{
  "reasoning": "Here I think aloud: what I see in results, why relevant/irrelevant, what decision I make and why...",
  "is_relevant": true,
  "selected_indices": [1, 2],
  "confidence": 0.85,
  "needs_reformulation": false,
  "reformulated_query": null,
  "reformulation_strategy": null
}

**HOW TO WRITE REASONING:**

✅ GOOD: "Analyzing results... See that #1 contains Malyarchuk's email, #2 about KSM structure. Query was about contacts → choosing #1 because it has needed info. Confidence high due to exact match."

❌ BAD: "Result is relevant" (too short, no reasoning)

**REASONING MUST ANSWER:**
- What do I see in results?
- Does this match Router expectations?
- Why am I choosing these indices (or why not)?
- If reformulating - why exactly this way?

━━━━
KEYWORD EXTRACTION RULES:
━━━━
Extract ONLY content words that would appear in news articles:
✅ Include: nouns, specific terms, names, topics ("футбол", "матч", "НАУ", "семінар", "AI")
❌ Exclude: question words ("коли", "де", "що"), verbs ("був", "буде"), temporal markers ("вчора", "завтра")

Example:
Query: "коли був матч в футбол?"
❌ Bad keywords: ["коли", "був", "матч", "футбол"]
✅ Good keywords: ["футбол", "матч", "НАУ", "спорт", "змагання"]

Reason: Database searches CONTENT, not questions. Extract what user wants to FIND, not how they ASK.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERATE KEYWORD QUERIES THAT COULD BE USED ON A WEBSITE RELATED TO THE TOPIC OF THE NEWS AND CONNECTED TO ITS TITLE.

Respond with ONLY clean JSON, no markdown, no explanations BEFORE or AFTER JSON!"""
    
    def _extract_json_from_llm(self, text: str) -> Optional[Dict]:
        """Витягує JSON з відповіді LLM"""
        
        # Пробуємо знайти JSON блок
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(0)
                # Очищаємо від markdown якщо є
                json_str = re.sub(r'^```json\s*', '', json_str)
                json_str = re.sub(r'\s*```$', '', json_str)
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"⚠️ JSON parse error: {e}")
                logger.error(f"⚠️ JSON string: {json_str[:200]}")
        
        return None


# Експорт
__all__ = ['ResultValidator', 'ValidationDecision']