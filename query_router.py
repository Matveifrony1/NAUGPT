"""
NAU AI Assistant Backend - Query Router
Умная маршрутизация запросов с контекстным анализом
"""

import httpx
import json
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from nau_structure import NAU_STRUCTURE, find_entity_by_alias, extract_entities_from_text
from config import settings
from logger import get_logger

logger = get_logger(__name__)


class RouteDecision(BaseModel):
    """Рішення про маршрутизацію запиту"""
    search_scope: str = Field(..., description="Факультет (ФКНТ/ФАЕТ) або global")
    search_level: str = Field(..., description="faculty/department/person/general")
    target_entity: Optional[str] = Field(None, description="Конкретна кафедра (ІПЗ/КІТ/...)")
    search_intent: str = Field(..., description="info/schedule/news/contacts/events")
    enhancement_keywords: List[str] = Field(default=[], description="Додаткові ключові слова")
    confidence: float = Field(..., description="Впевненість у рішенні 0-1")
    reasoning: str = Field(..., description="Пояснення рішення")
    needs_database_search: bool = Field(..., description="Чи потрібен пошук у базі даних")

class QueryRouter:
    """
    Розумний роутер запитів з LLM-аналізом
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
            
        self.nau_structure = NAU_STRUCTURE
            
        # Словник смислових розширень
        self.semantic_expansions = {
            # Події та зустрічі
            "політ": ["конференція", "захід", "зустріч", "семінар", "форум", "збори"],
            "зустріч": ["засідання", "нарада", "конференція", "семінар"],
            "подія": ["захід", "конференція", "форум", "семінар", "святкування"],
            
            # Викладачі та люди
            "викладач": ["професор", "доцент", "завідувач", "науковець", "педагог"],
            "завідувач": ["завкафедри", "керівник кафедри", "декан", "професор"],
            
            # Навчання
            "навчання": ["освіта", "заняття", "пари", "лекції", "семінари", "курс"],
            "розклад": ["пари", "заняття", "графік", "час занять"],
            
            # Наука
            "дослідження": ["наука", "наукова робота", "публікації", "конференції"],
            "конференція": ["симпозіум", "форум", "наукова подія", "семінар"],
            
            # Вступ
            "вступ": ["абітурієнт", "прийом", "документи", "конкурс", "зарахування"],
            
            # Контакти
            "контакти": ["телефон", "адреса", "email", "зв'язок", "розташування"],
        }
    
    async def route_query(self, query: str, history: Optional[List[Dict]] = None,
                         group_name: Optional[str] = None) -> RouteDecision:
        
        logger.debug(f"🧭 QUERY ROUTER: Аналіз запиту '{query[:50]}...'")
        
        # Завжди викликаємо LLM
        llm_decision = await self._llm_routing(query, history, group_name)
        
        if llm_decision:
            logger.debug(f"🧭 LLM РІШЕННЯ: scope={llm_decision.search_scope}, entity={llm_decision.target_entity}")
            return llm_decision
        
        # Fallback на евристику тільки якщо LLM не спрацював
        logger.error(f"⚠️ LLM недоступний → евристична маршрутизація")
        heuristic_decision = self._heuristic_routing(query, history, group_name)
        logger.error(f"🧭 HEURISTIC: scope={heuristic_decision.search_scope}")
        return heuristic_decision
    
    def _heuristic_routing(self, query: str, history: Optional[List[Dict]], 
                          group_name: Optional[str]) -> RouteDecision:
        """
        Швидка евристична маршрутизація (без LLM)
        """
        
        query_lower = query.lower()
        
        # === ВИЛУЧЕННЯ СУТНОСТЕЙ З ЗАПИТУ ===
        entities = extract_entities_from_text(query)
        
        # === АНАЛІЗ ІСТОРІЇ ===
        context_scope = None
        context_entity = None
        
        if history:
            # Беремо останні 3 повідомлення
            recent_history = history[-6:] if len(history) > 6 else history
            history_text = " ".join([msg["content"] for msg in recent_history])
            history_entities = extract_entities_from_text(history_text)
            
            if history_entities:
                last_entity = history_entities[-1]
                if last_entity["type"] == "faculty":
                    context_scope = last_entity["code"]
                elif last_entity["type"] == "department":
                    context_scope = last_entity["faculty_code"]
                    context_entity = last_entity["code"]
        
        # === ПРІОРИТЕТИ: Пряма згадка > Історія > Група ===
        
        # 1. ПРЯМЕ ЗГАДАННЯ в запиті
        search_scope = "global"
        search_level = "general"
        target_entity = None
        confidence = 0.5
        
        if entities:
            entity = entities[0]  # Берімо першу знайдену
            if entity["type"] == "faculty":
                search_scope = entity["code"]
                search_level = "faculty"
                confidence = 0.95
            elif entity["type"] == "department":
                search_scope = entity["faculty_code"]
                search_level = "department"
                target_entity = entity["code"]
                confidence = 0.98
        
        # 2. КОНТЕКСТ З ІСТОРІЇ (якщо не знайшли в запиті)
        elif context_scope:
            search_scope = context_scope
            if context_entity:
                search_level = "department"
                target_entity = context_entity
                confidence = 0.75
            else:
                search_level = "faculty"
                confidence = 0.70
        
        # 3. ГРУПА СТУДЕНТА
        elif group_name:
            # Спробуємо визначити факультет за групою (за патернами кодів груп)
            # Наприклад, групи ІР/КІТ → ФКНТ
            if any(x in group_name.upper() for x in ["ІР", "КІТ", "КІ", "ПМ", "КБ"]):
                search_scope = "ФКНТ"
                search_level = "faculty"
                confidence = 0.60
        
        # === ВИЗНАЧЕННЯ INTENT ===
        search_intent = self._detect_intent(query_lower)
        
        # === ГЕНЕРАЦІЯ КЛЮЧОВИХ СЛІВ ДЛЯ ПОКРАЩЕННЯ ===
        enhancement_keywords = self._generate_enhancement_keywords(query_lower, search_intent)
        
        # === REASONING ===
        reasoning = self._build_reasoning(
            entities, context_scope, context_entity, 
            search_scope, search_level, target_entity
        )
        
        # === ВИЗНАЧЕННЯ needs_database_search ===
        # Проста евристика для режиму fallback
        greeting_words = ["привіт", "привет", "дякую", "спасибо", "пока", "бувай", "hi", "hello", "bye"]
        question_words = ["що", "як", "коли", "де", "хто", "чому", "який", "яка", "яке", "чи"]

        query_lower = query.lower()
        is_greeting = any(word in query_lower for word in greeting_words)
        has_question = any(word in query_lower for word in question_words)

        # Якщо короткий запит і привітання - не шукаємо
        # Якщо є запитальні слова - шукаємо
        needs_search = (not (len(query.split()) <= 3 and is_greeting)) or has_question

        return RouteDecision(
            search_scope=search_scope,
            search_level=search_level,
            target_entity=target_entity,
            search_intent=search_intent,
            enhancement_keywords=enhancement_keywords,
            confidence=0.5,
            reasoning=reasoning,
            needs_database_search=needs_search
        )
    
    async def _llm_routing(self, query: str, history: Optional[List[Dict]], 
                          group_name: Optional[str], max_retries: int = 3) -> Optional[RouteDecision]:
        """
         LLM маршрутизація з автоматичними retry при помилках парсингу JSON
        
        Args:
            max_retries: максимум спроб (за замовчуванням 3)
        """
        
        system_prompt = self._build_llm_routing_prompt()
        
        history_text = ""
        if history and len(history) > 0:
            history_to_show = history.copy()
            if history_to_show and history_to_show[-1].get('role') == 'user':
                last_content = history_to_show[-1].get('content', '').strip()
                if last_content == query.strip():
                    history_to_show = history_to_show[:-1]            
            if history_to_show:
                history_text = "\n".join([
                    f"{'👤 Користувач' if m['role'] == 'user' else '🤖 Асистент'}: {m['content']}" 
                    for m in history_to_show
                ])
        
        user_message = f"""КОНТЕКСТ ДІАЛОГУ:
    {history_text if history_text else "Початок діалогу"}

    ГРУПА СТУДЕНТА: {group_name if group_name else "Не вказано"}

    НОВИЙ ЗАПИТ: "{query}"

    Проаналізуй запит з урахуванням контексту та дай рішення про маршрутизацію."""

        # RETRY LOOP
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"🤖 LLM ROUTING: спроба {attempt}/{max_retries}")
                
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
                    logger.debug(f"🤖 LLM ВІДПОВІВ: {llm_response}")
                    
                    # ПАРСИНГ JSON
                    parsed = self._extract_json_from_llm(llm_response)
                    
                    if parsed:
                        logger.debug(f"✅ JSON успішно розпарсений на спробі {attempt}")
                        
                        return RouteDecision(
                            search_scope=parsed.get("search_scope", "global"),
                            search_level=parsed.get("search_level", "general"),
                            target_entity=parsed.get("target_entity"),
                            search_intent=parsed.get("search_intent", "info"),
                            enhancement_keywords=parsed.get("enhancement_keywords", []),
                            confidence=parsed.get("confidence", 0.5),
                            reasoning=parsed.get("reasoning", "LLM routing"),
                            needs_database_search=parsed.get("needs_database_search", True)
                        )
                    else:
                        logger.warning(f"⚠️ LLM routing (спроба {attempt}): не вдалося розпарсити JSON")
                        if attempt < max_retries:
                            logger.debug(f"🔄 Повторна спроба...")
                            continue
                        else:
                            logger.error(f"❌ Вичерпано спроби ({max_retries}), fallback на евристику")
                            return None
                
                # ========== СТАРИЙ КОД ДЛЯ LM STUDIO ==========
                else:
                    async with httpx.AsyncClient(timeout=30.0) as client:
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
                            logger.debug(f"🤖 LLM ВІДПОВІВ: {llm_response[:200]}...")
                            
                            # ПАРСИНГ JSON
                            parsed = self._extract_json_from_llm(llm_response)
                            
                            if parsed:
                                logger.debug(f"✅ JSON успішно розпарсений на спробі {attempt}")
                                
                                return RouteDecision(
                                    search_scope=parsed.get("search_scope", "global"),
                                    search_level=parsed.get("search_level", "general"),
                                    target_entity=parsed.get("target_entity"),
                                    search_intent=parsed.get("search_intent", "info"),
                                    enhancement_keywords=parsed.get("enhancement_keywords", []),
                                    confidence=parsed.get("confidence", 0.5),
                                    reasoning=parsed.get("reasoning", "LLM routing"),
                                    needs_database_search=parsed.get("needs_database_search", True)
                                )
                            else:
                                logger.warning(f"⚠️ LLM routing (спроба {attempt}): не вдалося розпарсити JSON")
                                if attempt < max_retries:
                                    logger.debug(f"🔄 Повторна спроба...")
                                    continue  
                                else:
                                    logger.error(f"❌ Вичерпано спроби ({max_retries}), fallback на евристику")
                                    return None
                        else:
                            logger.warning(f"⚠️ LLM routing (спроба {attempt}): HTTP {response.status_code}")
                            if attempt < max_retries:
                                continue
                            return None
                            
            except Exception as e:
                logger.warning(f"⚠️ LLM routing (спроба {attempt}): помилка {e}")
                if attempt < max_retries:
                    logger.debug(f"🔄 Повторна спроба...")
                    continue
                return None
        
        # Якщо всі спроби провалилися
        return None
    
    def _build_llm_routing_prompt(self) -> str:
        """Побудова промпта для LLM"""
        
        # Генеруємо компактне представлення структури КАІ
        structure_summary = []
        for faculty_code, faculty_data in self.nau_structure.items():
            if faculty_code == "global":
                continue
            structure_summary.append(f"- {faculty_code}: {faculty_data['full_name']}")
            for dept_code, dept_data in faculty_data.get("departments", {}).items():
                structure_summary.append(f"  - {dept_code}: {dept_data['full_name']}")
        
        structure_text = "\n".join(structure_summary)
        
        return f"""You are an expert routing system for National Aviation University (NAU).

NAU STRUCTURE:
{structure_text}

━━━━
🧠 CRITICAL: DIALOGUE CONTEXT HANDLING
━━━━

📜 WHAT IS CONTEXT:
- You ALWAYS receive FULL dialogue history with the user
- Each previous message is a KEY to understanding the new query
- User does NOT repeat information - expects you to remember the dialogue

🎯 MAIN CONTEXT RULE:
If user does NOT specify who/what they're asking about in new query → they MEAN 
the same thing discussed in PREVIOUS MESSAGES!

🔍 HOW TO ANALYZE CONTEXT:

1️ ALWAYS read ENTIRE dialogue history BEFORE analyzing new query
2️ Look for key entities in previous messages:
   - People's names (teachers, students, staff)
   - Names (departments, faculties, events, conferences)
   - Conversation topics (sports, science, education)
   
3️ If new query contains pronouns or vague expressions:
   - "he", "she", "they" → WHO was mentioned before?
   - "this", "that" → WHAT was discussed before?
   - "there" → WHERE was the conversation about?
   - Just "teacher" WITHOUT name → WHICH teacher was discussed?

4️ MANDATORY add to enhancement_keywords:
   - ALL names and surnames from context, if query is about THAT SAME person
   - ALL event/location names from context, if query is about them
   - Synonyms and variations of what was discussed

5️ IF new query topic is UNRELATED to previous context, DON'T reference it

━━━━
📚 CONTEXT HANDLING EXAMPLES:
━━━━

EXAMPLE 1 - Person clarification:
Context:
  👤 User: Хто завідувач ІПЗ?
  🤖 Assistant: Завідувач кафедри ІПЗ - професор Іванов Петро Степанович
New query: "А його email?"

YOUR ANALYSIS:
{{
  "reasoning": "Reading dialogue history... See that Ivanov Petro Stepanovych, head of IPZ, was discussed earlier. New query 'his email' - pronoun 'his' refers to this person from context. This is continuation of topic about IPZ teacher. Setting: scope=ФКНТ (because IPZ is there), entity=ІПЗ, intent=contacts (asking for email). Adding to keywords full name + position synonyms.",
  "search_scope": "ФКНТ",
  "search_level": "department",
  "target_entity": "ІПЗ",
  "search_intent": "contacts",
  "enhancement_keywords": ["Іванов", "Петро", "Степанович", "викладач", "персонал", "завідувач", "email", "контакти"],
  "confidence": 0.95,
  "needs_database_search": true
}}

━━━━

EXAMPLE 2 - Topic continuation without clarification:
Context:
  👤 User: Кто такой Малярчук?
  🤖 Assistant: [explanation that it's a joke about teachers]
  👤 User: А на ФКНТ є такі?
  🤖 Assistant: [list of FKNT teachers]
New query: "та це з ксм препод"

YOUR ANALYSIS:
{{
  "reasoning": "Analyzing context... Entire dialogue is about NAU teachers. First asked about Malyarchuk (joke), then about FKNT teachers. New query 'this is from ksm teacher' - 'this' = teacher (dialogue topic), 'ksm' = KSM department, 'teacher' = teacher. User clarifies it's specifically about KSM teacher. Setting scope=ФКНТ, entity=КСМ. Adding 'Malyarchuk' to keywords as initial dialogue topic.",
  "search_scope": "ФКНТ",
  "search_level": "department",
  "target_entity": "КСМ",
  "search_intent": "info",
  "enhancement_keywords": ["викладач", "викладачі", "професор", "доцент", "персонал", "КСМ", "Малярчук"],
  "confidence": 0.85,
  "needs_database_search": true
}}

━━━━
⚙️ ROUTING PARAMETERS:
━━━━

TASK: Determine the following parameters:

1. reasoning: detailed explanation of your analysis (FIRST FIELD!)
   - How you used dialogue history
   - What pronouns/vague expressions mean from context
   - Why you chose such scope/entity/intent
   - Which keywords you added and why

2. search_scope: "ФКНТ" / "ФАЕТ" / "global"
   - Faculty if specific department mentioned
   - "global" if general question about NAU

3. search_level: "faculty" / "department" / "general"  
   - "department" if about specific department
   - "faculty" if about faculty in general
   - "general" for general questions

4. target_entity: department code (ІПЗ/КІТ/КСМ/...) or null
   - Fill if department exists in context or query

5. search_intent: "info" / "schedule" / "news" / "contacts" / "events"
   - "info" - general information
   - "contacts" - email, phones, communication
   - "news" - news, announcements
   - "events" - events, conferences, activities

6. enhancement_keywords: list of search keywords (SEE DETAILED RULES BELOW!)

7. confidence: 0.0-1.0
   - High (0.9+) if everything is clear from context
   - Medium (0.7-0.9) if there are assumptions
   - Low (<0.7) if much uncertainty

8. needs_database_search: true / false

━━━━
⚠️ CRITICAL: ENHANCEMENT_KEYWORDS RULES
━━━━

**MAIN RULE:** Generate keywords that **EXIST IN NEWS**, not in questions!

**HOW EMBEDDING SEARCH WORKS:**
- Searches for **vector similarity** between query and news text
- If query has words that are **ABSENT** in news → search fails
- News contains: event names, names, places, topics
- News does NOT contain: question words, temporal markers from questions

✅ **CORRECT KEYWORDS** (exist in news):
- Topics: "теніс", "футбол", "конференція", "семінар"
- Names: "Іванов", "Малярчук", "Туруй"  
- Places: "НАУ", "ФКНТ", "КСМ", "спорткомплекс"
- Events: "Універсіада", "турнір", "змагання"

❌ **WRONG KEYWORDS** (absent in news):
- Question words: "коли", "де", "що", "хто", "як"
- Verbs from questions: "був", "буде", "відбувся"
- Temporal markers FROM QUESTIONS: "остання", "наступна", "вчора", "завтра"

⚠️ **NOTE:** Temporal markers in questions ("остання гра", "останній турнір") should be REMOVED. News will be found by topic words.

🧠 **KEYWORD GENERATION ALGORITHM:**
1. Extract NOUNS from query (people, places, events, topics)
2. Add SYNONYMS of these nouns
3. Add CONTEXT (faculty, department, event type)
4. REMOVE everything else: question words, verbs, temporal markers, service words

**EXAMPLES:**
Query: "коли була остання гра в теніс?"
❌ BAD: ["коли", "була", "остання", "гра", "теніс"]
✅ GOOD: ["теніс", "гра", "спорт", "змагання", "НАУ"]

Query: "хто виграв останній турнір?"
❌ BAD: ["хто", "виграв", "останній", "турнір"]  
✅ GOOD: ["турнір", "переможець", "змагання", "спорт", "НАУ"]

━━━━
✅ RULES FOR needs_database_search:
━━━━

🟢 TRUE (search in DB):
- Factual questions about NAU (teachers, events, news)
- Clarifications about something mentioned in context
- Questions about sports, science, NAU conferences
- General "who", "what", "when", "where" questions about NAU

🔴 FALSE (DON'T search):
- Greetings ("привіт", "дякую")
- Requests to explain ALREADY PROVIDED information
- Philosophical questions not about NAU
- ⚠️ Schedule queries ("розклад", "які пари")

━━━━
📤 RESPONSE FORMAT:
━━━━

⚠️ CRITICAL: MANDATORY FIELD ORDER!

**reasoning ALWAYS FIRST FIELD!** Think first, then decide.

RESPOND ONLY WITH JSON, NO ADDITIONAL TEXT:

{{
  "reasoning": "First analyzing dialogue context... [here you describe in detail your thinking process: what you see in history, how you interpret new query, why you choose these parameters]",
  "search_scope": "ФКНТ",
  "search_level": "department",
  "target_entity": "КСМ",
  "search_intent": "info",
  "enhancement_keywords": ["викладач", "професор", "доцент", "КСМ", "персонал"],
  "confidence": 0.85,
  "needs_database_search": true
}}

**HOW TO WRITE REASONING:**
✅ GOOD: "Reading dialogue history... See that Malyarchuk from KSM was discussed earlier. New query 'his number' - pronoun 'his' = Malyarchuk. This continues teacher topic. Setting scope=ФКНТ (KSM belongs to FKNT), entity=КСМ, intent=contacts (number = contact). Adding to keywords 'Malyarchuk' + teacher synonyms + 'контакти телефон'."

❌ BAD: "Query about teacher" (too short, no context analysis)

GENERATE KEYWORD QUERIES THAT COULD BE USED ON A WEBSITE RELATED TO THE TOPIC OF THE NEWS AND CONNECTED TO ITS TITLE."""
    
    def _detect_intent(self, query: str) -> str:
        """Визначення наміру користувача"""
        
        intent_patterns = {
            "schedule": ["розклад", "пари", "заняття", "коли", "о котрій"],
            "news": ["новин", "подій", "останн", "що нового", "актуальн"],
            "contacts": ["контакт", "телефон", "адрес", "email", "де знаходиться"],
            "events": ["захід", "конференція", "семінар", "зустріч", "форум", "політ"],
            "info": ["інформац", "розкажи", "що", "як", "хто", "викладач"],
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in query for pattern in patterns):
                return intent
        
        return "info"
    
    def _generate_enhancement_keywords(self, query: str, intent: str) -> List[str]:
        """
        Генерація додаткових ключових слів для поліпшення пошуку
        """
        
        keywords = []
        
        # 1. Смислові розширення зі словника
        for key, expansions in self.semantic_expansions.items():
            if key in query:
                keywords.extend(expansions[:3])  # Топ-3
        
        # 2. Intent-based keywords
        intent_keywords = {
            "schedule": ["графік", "час", "аудиторія"],
            "news": ["подія", "оголошення", "інформація"],
            "contacts": ["зв'язок", "телефон", "адреса"],
            "events": ["подія", "зустріч", "захід"],
            "info": ["інформація", "дані", "відомості"],
        }
        
        keywords.extend(intent_keywords.get(intent, []))
        
        # 3. Прибираємо дублікати
        return list(set(keywords))[:5]  # Максимум 5
    
    def _build_reasoning(self, entities, context_scope, context_entity,
                        search_scope, search_level, target_entity) -> str:
        """Побудова пояснення рішення"""
        
        if entities:
            entity = entities[0]
            return f"Знайдено: {entity['matched_alias']} → {entity['full_name']}"
        elif context_entity:
            return f"Контекст з історії: {context_entity}"
        elif context_scope:
            return f"Контекст з історії: факультет {context_scope}"
        elif search_scope != "global":
            return f"Визначено факультет: {search_scope}"
        else:
            return "Загальний запит про НАУ"
    
    def _extract_json_from_llm(self, text: str) -> Optional[Dict]:
        """Витяг JSON з відповіді LLM"""
        
        # Ищем JSON блок
        json_match = re.search(r'\{[^\}]+\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None


# === ДОПОМІЖНІ ФУНКЦІЇ ===

def format_route_for_search(route: RouteDecision) -> Dict:
    """
    Форматування RouteDecision для використання в database.py
    
    Повертає:
        Dict з фільтрами для ChromaDB
    """
    
    filters = {}
    
    # Scope фільтр
    if route.search_scope != "global":
        filters["faculty"] = route.search_scope
    
    # Entity фільтр
    if route.target_entity:
        filters["department"] = route.target_entity
    
    # Intent фільтр (категорія)
    intent_to_category = {
        "schedule": "schedule",
        "news": "news",
        "events": "events",
        "contacts": "contacts",
        "info": None
    }
    
    category = intent_to_category.get(route.search_intent)
    if category:
        filters["category"] = category
    
    return filters


def enhance_query_with_route(query: str, route: RouteDecision) -> str:
    """
    Розширення запиту з використанням інформації з маршруту
    
    Args:
        query: Оригінальний запит
        route: Рішення про маршрутизацію
    
    Returns:
        Розширений запит
    """
    
    parts = [query]
    
    # Додаємо повні назви
    if route.search_scope != "global" and route.search_scope in NAU_STRUCTURE:
        faculty = NAU_STRUCTURE[route.search_scope]
        parts.append(faculty["full_name"])
    
    if route.target_entity and route.search_scope in NAU_STRUCTURE:
        dept = NAU_STRUCTURE[route.search_scope]["departments"].get(route.target_entity)
        if dept:
            parts.append(dept["full_name"])
    
    # Додаємо ключові слова для покращення
    if route.enhancement_keywords:
        parts.extend(route.enhancement_keywords)
    
    return " ".join(parts)


# Экспорт
__all__ = [
    'QueryRouter',
    'RouteDecision',
    'format_route_for_search',
    'enhance_query_with_route'
]