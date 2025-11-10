"""
NAU AI Assistant Backend - AI Assistant Class
Адаптований для stateless роботи з FastAPI
"""

import httpx
import asyncio
from typing import Dict, List, Optional
import re
import google.generativeai as genai
from datetime import datetime
from utils import ContextUtils
from config import settings, SCHEDULE_KEYWORDS, GREETING_KEYWORDS, NEWS_KEYWORDS
from query_router import QueryRouter, enhance_query_with_route
from result_validator import ResultValidator, ValidationDecision
from logger import get_logger

logger = get_logger(__name__)



class NAUAssistant:
    """AI-асистент КАІ для backend API (stateless)"""
    
    def __init__(self, database, schedule_manager):
        self.db = database
        self.schedule_manager = schedule_manager
        self.show_system_prompt = settings.LOG_SYSTEM_PROMPTS
        self.query_router = QueryRouter()
        self.result_validator = ResultValidator()
        
        # Ініціалізація Gemini
        if settings.USE_GEMINI:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
            self.lm_studio_url = None
        else:
            self.lm_studio_url = settings.LM_STUDIO_URL
            self.gemini_model = None
            
    async def check_lm_studio(self) -> bool:
        """Перевірка доступності LM Studio або Gemini"""
        if settings.USE_GEMINI:
            try:
                # Простий тестовий запит до Gemini
                response = self.gemini_model.generate_content("Test", 
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=10,
                        temperature=0.1
                    ))
                if response.text:
                    logger.info(f"✅ Gemini підключен: {settings.GEMINI_MODEL}")
                    return True
            except Exception as e:
                logger.error(f"⚠️ Gemini недоступний: {e}")
                return False
        else:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get("http://localhost:1234/v1/models")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("data"):
                            self.model_name = data["data"][0]["id"]
                            logger.info(f"✅ LM Studio підключен: {self.model_name}")
                            return True
            except:
                pass
            
            logger.critical("⚠️ LM Studio недоступний - працюємо без LLM")
            return False

    async def process_query(self, message: str, group_name: Optional[str] = None, 
                          user_name: Optional[str] = None, 
                          messages: Optional[List[Dict]] = None) -> str:
        
        logger.debug(f"🤖 PROCESS_QUERY: user={user_name}, group={group_name}, message='{message[:50]}...'")
        
        lm_available = await self.check_lm_studio()
        if not lm_available:
            return self._fallback_response(message, group_name)
        
        schedule = None
        if group_name:
            schedule = self.schedule_manager.load_group_schedule(group_name)
        
        # 🧭 МАРШРУТИЗАЦІЯ ЗАПИТУ
        route_decision = await self.query_router.route_query(
            query=message,
            history=messages,
            group_name=group_name
        )

        logger.debug(f"🧭 ROUTE: scope={route_decision.search_scope}, level={route_decision.search_level}, "
              f"entity={route_decision.target_entity}, keywords={route_decision.enhancement_keywords}, "
              f"needs_search={route_decision.needs_database_search}")

        # ПОШУК З ВАЛІДАЦІЄЮ
        context_results = []
        if route_decision.needs_database_search:
            context_results = await self._search_with_validation(
                message=message,
                route_decision=route_decision
            )
            logger.debug(f"📚 ФІНАЛЬНІ РЕЗУЛЬТАТИ: {len(context_results)} документів")
        else:
            logger.debug(f"⏭️ SKIP SEARCH: нейронка вирішила не шукати в БД")
        
        context = self._format_context_for_llm_improved(context_results) if context_results else ""
        
        return await self._generate_llm_response(message, context, group_name, schedule, user_name, messages)

    async def _search_with_validation(
        self, 
        message: str, 
        route_decision
    ) -> List[Dict]:
        """
        Пошук з валідацією та ЦИКЛІЧНИМ переформулюванням
        """
        
        MAX_ATTEMPTS = 3  # Максимум 3 спроби
        
        # ВИКОРИСТОВУЄМО ТІЛЬКИ KEYWORDS ВІД НЕЙРОНКИ
        if route_decision.enhancement_keywords:
            current_query = " ".join(route_decision.enhancement_keywords)
            logger.debug(f"🧠 KEYWORDS: '{current_query}'")
        else:
            # Fallback якщо нейронка не згенерувала keywords
            current_query = message
            logger.warning(f"⚠️ Нейронка не дала keywords, використовую оригінал")
        
        for attempt in range(1, MAX_ATTEMPTS + 1):
            logger.debug(f"🔍 {'='*5}")
            logger.debug(f"🔍 СПРОБА {attempt}/{MAX_ATTEMPTS}: query='{current_query}...'")
            logger.debug(f"🔍 {'='*5}")
            
            # Пошук в БД
            raw_results = self.db.search_with_route(
                query=current_query,
                route_decision=route_decision,
                top_k=15
            )
            
            if not raw_results:
                logger.error(f"❌ СПРОБА {attempt}: БД не повернула результатів")
                if attempt == MAX_ATTEMPTS:
                    return []
                # Спробуємо спростити запит ще більше для наступної спроби
                current_query = current_query.split()[0] if len(current_query.split()) > 1 else current_query
                continue
            
            logger.debug(f"🔍 СПРОБА {attempt}: БД повернула {len(raw_results)} результатів")
            
            # Валідація
            validation_decision, selected_results = await self.result_validator.validate_and_select(
                original_query=message,
                search_results=raw_results,
                route_reasoning=route_decision.reasoning,
                attempt=attempt
            )
            
            # УСПІХ - знайшли релевантні результати
            if validation_decision.is_relevant and selected_results:
                logger.debug(f"✅ СПРОБА {attempt}: Успіх! Знайдено {len(selected_results)} релевантних результатів")
                return selected_results
            
            # НЕ РЕЛЕВАНТНІ - перевіряємо чи є переформулювання
            if validation_decision.needs_reformulation and validation_decision.reformulated_query:
                logger.debug(f"🔄 СПРОБА {attempt}: Нерелевантно, переформульовую запит")
                logger.debug(f"🔄 СТРАТЕГІЯ: {validation_decision.reformulation_strategy}")
                logger.debug(f"🔄 СТАРИЙ ЗАПИТ: '{current_query}'")
                logger.debug(f"🔄 НОВИЙ ЗАПИТ: '{validation_decision.reformulated_query}'")
                
                # Переходимо до наступної ітерації з новим запитом
                current_query = validation_decision.reformulated_query
                
                if attempt == MAX_ATTEMPTS:
                    logger.error(f"⚠️ ДОСЯГНУТО ЛІМІТ СПРОБ ({MAX_ATTEMPTS}), результатів немає")
                    return []
            else:
                # Валідатор не запропонував переформулювання - зупиняємося
                logger.error(f"❌ СПРОБА {attempt}: Валідатор не запропонував переформулювання, зупиняємося")
                return selected_results  # Повертаємо що є (можливо порожній список)
        
        # Якщо вийшли з циклу - нічого не знайшли
        logger.error(f"❌ ВСІ {MAX_ATTEMPTS} СПРОБИ ВИЧЕРПАНО: жодних релевантних результатів")
        return []

    def _format_context_for_llm_improved(self, context_results: List[Dict]) -> str:
        """
        Динамічний розподіл місця між обраними результатами
        """
        if not context_results:
            return ""
        
        MAX_TOTAL_CHARS = 4500  # Загальний ліміт символів для контексту
        
        # Розподіляємо місце рівномірно між обраними результатами
        chars_per_result = MAX_TOTAL_CHARS // len(context_results)
        
        context_parts = []
        for i, result in enumerate(context_results, 1):
            content = result["content"]
            metadata = result.get("metadata", {})
            relevance = result.get("relevance_score", 0)
            
            # Обрізаємо якщо потрібно
            if len(content) > chars_per_result:
                content = content[:chars_per_result] + "..."
            
            # Заголовок
            header = f"Інформація {i} (релевантність: {relevance:.2f})"
            
            if metadata.get("title"):
                header += f"\nЗаголовок: {metadata['title']}"
            
            if metadata.get("url"):
                header += f"\nПосилання: {metadata['url']}"
            
            if metadata.get("news_type"):
                header += f"\nТип: {metadata['news_type']}"
            # Дата новости
            if metadata.get("date"):
                header += f", дата: {metadata['date']}"
            
            context_parts.append(f"{header}\n{content}")
        
        result = "\n\n" + "="*50 + "\n\n".join(context_parts)
        
        logger.debug(f"📝 КОНТЕКСТ ДЛЯ LLM: {len(context_results)} результатів, ~{len(result)} символів")
        logger.debug(f"📝 Розподіл: по ~{chars_per_result} символів на результат")
        
        return result

    def _get_category_for_query(self, message: str) -> Optional[str]:
        """Визначення категорії для фільтрації пошуку"""
        message_lower = message.lower()
        
        category_keywords = {
            "education": ["навчання", "освіта", "факультет", "кафедра", "спеціальність"],
            "admission": ["вступ", "абітурієнт", "документи", "зарахування"],
            "science": ["наука", "дослідження", "конференція", "публікація"],
            "international": ["міжнародний", "партнерство", "співпраця"],
            "meetings": ["засідання", "рада", "збори"],
            "competitions": ["конкурс", "змагання", "олімпіада"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return category
        
        return None


    async def _generate_llm_response(self, message: str, context: str = "", 
                                   group_name: Optional[str] = None,
                                   schedule: Optional[Dict] = None,
                                   user_name: Optional[str] = None,
                                   messages: Optional[List[Dict]] = None) -> str:
        """Генерація відповіді через LLM - STATELESS версія з контекстом діалогу"""
        
        # Вибираємо системний промпт: з групою чи без
        if group_name and schedule:
            system_prompt = self._get_system_prompt_with_schedule(group_name, schedule)
        else:
            system_prompt = self._get_system_prompt_without_schedule()
        
        # Формуємо повідомлення користувача
        if context:
            user_message = f"[Додаткова інформація з бази даних КАІ: {context}]\n\nПитання: {message}"
        else:
            user_message = message
        
        # Додаємо ім'я користувача в контекст, якщо є
        if user_name:
            user_message = f"[Користувач: {user_name}]\n\n{user_message}"
        
        # будуємо контекст з історією
        context_messages = [{"role": "system", "content": system_prompt}]
        
        # Якщо є історія діалогу - додаємо з розумним обрізанням
        if messages:
            # Підраховуємо, скільки токенів вже зайнято
            system_tokens = ContextUtils.count_tokens(system_prompt)
            new_message_tokens = ContextUtils.count_tokens(user_message)
            available_for_history = settings.MAX_CONTEXT_TOKENS - system_tokens - new_message_tokens - 200  # буфер
            
            # Обрізаємо історію, якщо потрібно
            if available_for_history > 0:
                truncated_messages = ContextUtils.truncate_messages(messages, available_for_history)
                context_messages.extend(truncated_messages)
                logger.debug(f"🤖 HISTORY: використовуємо {len(truncated_messages)} з {len(messages)} повідомлень")
        
        # Додаємо нове повідомлення користувача
        context_messages.append({"role": "user", "content": user_message})
        
        # Логування
        total_tokens = sum(ContextUtils.count_tokens(msg["content"]) for msg in context_messages)
        logger.debug(f"🤖 FINAL CONTEXT: {len(context_messages)} messages, ~{total_tokens} tokens")
        
        if self.show_system_prompt:
            logger.debug("\n" + "🤖" * 30)
            logger.debug(f"🤖 ГРУПА ВСТАНОВЛЕНА: {'ТАК' if group_name else 'НІ'}")
            if group_name:
                logger.debug(f"🤖 АКТИВНА ГРУПА: {group_name}")
            logger.debug(f"🤖 КОНТЕКСТ З БД: {'ТАК' if context else 'НІ'}")
            logger.debug(f"🤖 КОРИСТУВАЧ: {user_name or 'Невідомий'}")
            logger.debug(f"🤖 ІСТОРІЯ ДІАЛОГУ: {len(messages or [])} повідомлень")
            logger.debug(f"🤖 ПОВІДОМЛЕННЯ: {message}")
            logger.debug("🤖" * 30 + "\n")

        if self.show_system_prompt:
            logger.debug("\n" + "🤖" * 30)
            logger.debug("🤖 ПОВНИЙ КОНТЕКСТ ДЛЯ LLM:")
            logger.debug("🤖" * 30)
            for i, msg in enumerate(context_messages):
                logger.debug(f"\n🤖 MESSAGE {i+1} ({msg['role']}):")
                logger.debug("-" * 60)
                logger.debug(msg['content'])
                logger.debug("-" * 60)
            logger.debug("🤖" * 30 + "\n")
        
        # ========== ТУТ ЗАМІНА НА GEMINI ==========
        if settings.USE_GEMINI:
            try:
                import google.generativeai as genai
                
                # Gemini НЕ підтримує system role, тому включаємо system prompt в КОЖНЕ повідомлення
                
                # Витягуємо system prompt
                system_content = ""
                for msg in context_messages:
                    if msg["role"] == "system":
                        system_content = msg["content"]
                        break
                
                # Будуємо історію для Gemini (без system та без останнього user message)
                gemini_history = []
                for msg in context_messages[1:]:  # Пропускаємо system (перший елемент)
                    if msg["role"] == "user":
                        gemini_history.append({
                            "role": "user",
                            "parts": [msg["content"]]
                        })
                    elif msg["role"] == "assistant":
                        gemini_history.append({
                            "role": "model",
                            "parts": [msg["content"]]
                        })
                
                # Останнє user повідомлення окремо (воно не йде в history)
                last_user_message = context_messages[-1]["content"]
                
                # КРИТИЧНО: Додаємо system prompt до ПЕРШОГО повідомлення в чаті
                if len(gemini_history) == 0:
                    # Якщо історії немає - додаємо system prompt до поточного повідомлення
                    final_message = f"{system_content}\n\n{last_user_message}"
                    chat = self.gemini_model.start_chat(history=[])
                else:
                    # Якщо є історія - додаємо system prompt до ПЕРШОГО user повідомлення в історії
                    if gemini_history[0]["role"] == "user":
                        gemini_history[0]["parts"][0] = f"{system_content}\n\n{gemini_history[0]['parts'][0]}"
                    
                    # Видаляємо останнє повідомлення з історії (воно йде окремо)
                    chat_history = gemini_history[:-1] if gemini_history[-1]["role"] == "user" else gemini_history
                    chat = self.gemini_model.start_chat(history=chat_history)
                    final_message = last_user_message
                
                logger.debug(f"🤖 GEMINI: history={len(chat.history)} messages, final_message_length={len(final_message)}")
                
                # Відправляємо повідомлення
                response = chat.send_message(
                    final_message,
                    generation_config=genai.types.GenerationConfig(
                        temperature=settings.GENERATION_TEMPERATURE,
                        max_output_tokens=settings.MAX_TOKENS,
                    )
                )
                
                ai_response = response.text
                
                logger.info(f"✅ GEMINI RESPONSE: length={len(ai_response)}, user={user_name}")
                return ai_response
                
            except asyncio.TimeoutError:
                logger.error("Timeout Gemini - використовую fallback")
                return self._fallback_response(message, group_name)
            except Exception as e:
                logger.error(f"⚠️ Помилка Gemini: {e} - використовую fallback")
                import traceback
                traceback.print_exc()
                return self._fallback_response(message, group_name)
        
        # ========== СТАРИЙ КОД ДЛЯ LM STUDIO (якщо USE_GEMINI=False) ==========
        else:
            payload = {
                "messages": context_messages,
                "temperature": settings.GENERATION_TEMPERATURE,
                "max_tokens": settings.MAX_TOKENS,
                "stream": False
            }
            
            try:
                async with httpx.AsyncClient(timeout=settings.LM_STUDIO_TIMEOUT) as client:
                    response = await client.post(self.lm_studio_url, json=payload)
                    response.raise_for_status()
                    
                    data = response.json()
                    ai_response = data["choices"][0]["message"]["content"]
                    
                    logger.info(f"✅ LLM RESPONSE: length={len(ai_response)}, user={user_name}")
                    return ai_response
                    
            except asyncio.TimeoutError:
                logger.error("⏰ Timeout LLM - використовую fallback")
                return self._fallback_response(message, group_name)
            except Exception as e:
                logger.error(f"⚠️ Помилка LLM: {e} - використовую fallback")
                return self._fallback_response(message, group_name)

    def _get_system_prompt_with_schedule(self, group_name: str, schedule: Dict) -> str:
        """Системний промпт з розкладом групи"""
        time_context = self.schedule_manager.get_current_time_context()
        schedule_text = self.schedule_manager.format_schedule_for_system_prompt(schedule)
        
        return f"""Ти - дружелюбний AI асистент Київського Авіаційного Інституту (КАЇ) (Раніше називався НАУ).

ПОТОЧНИЙ КОНТЕКСТ:
• Сьогодні: {time_context['day']}, {time_context['date']}
• Час: {time_context['time']}
• Зараз йде {time_context['week']} тиждень розкладу
• Встановлена група: {group_name}

РОЗКЛАД ГРУПИ {group_name}:
{schedule_text}

ТИ ВМІЄШ:
• Відповідати на питання про розклад (використовуючи ТОЧНУ інформацію вище)
• Допомагати з питаннями про НАУ (навчання, вступ, новини)
• Підтримувати звичайну розмову

ПРАВИЛА ДЛЯ РОЗКЛАДУ:
• Завжди кажи точний час і номер пари
• Розрізняй ТИЖДЕНЬ 1 і ТИЖДЕНЬ 2, ПІСЛЯ ДРУГОГО ТИЖНЮ ЙДЕ ЗНОВУ ПЕРШИЙ
• Якщо пари немає - так і кажи "пари немає"
• НЕ вигадуй інформацію якої немає в розкладі
• Якщо аудиторія не вказана - кажи "аудиторія не вказана"

ЛОГІКА ДЛЯ "НАСТУПНОГО" ДНЯ:
• Якщо студент питає про "наступний понеділок/вівторок/середу" і т.д.:
  - Якщо сьогодні середа-неділя: показуй день з НАСТУПНОГО тижня
  - Якщо сьогодні понеділок-вівторок: показуй день з ПОТОЧНОГО тижня (якщо він ще не пройшов)
• Приклад: Сьогодні четвер тиждень 1, питають "наступний вівторок" → показуй вівторок тижня 2
• Приклад: Сьогодні понеділок тиждень 1, питають "наступну середу" → показуй середу тижня 1
• Завжди уточнюй який саме тиждень і дату показуєш

ПРАВИЛА ДЛЯ НОВИН ТА ІНФОРМАЦІЇ:
• ЗАВЖДИ додавай посилання на джерела новин у форматі: [Читати повністю](URL)
• Якщо використовуєш інформацію з новин НАУ - обов'язково вказуй посилання на саму новину
• Посилання допомагають користувачам перевірити інформацію та дізнатися більше
• Формат: "Згідно з новиною від [дата], [короткий зміст]. [Читати повністю](https://nau.edu.ua/...)"

СТИЛЬ СПІЛКУВАННЯ:
• Говори як друг-студент
• Будь корисним і точним
• Можеш жартувати, але в міру
• Використовуй емодзі де доречно
ПРАВИЛА ВІДПОВІДІ:
- Відповідай ТІЛЬКИ на ОСТАННЄ повідомлення користувача
- Попередні повідомлення - це контекст для розуміння теми
- НЕ повторюй свої попередні відповіді
- Якщо питають "а завтра?" - рахуй від сьогоднішньої дати"""

    def _get_system_prompt_without_schedule(self) -> str:
        """Системний промпт БЕЗ расписания группы"""
        time_context = self.schedule_manager.get_current_time_context()
        
        return f"""Ти - дружелюбний AI асистент Київського Авіаційного Інституту (КАЇ) (Раніше називався НАУ).

ПОТОЧНИЙ КОНТЕКСТ:
• Сьогодні: {time_context['day']}, {time_context['date']}
• Час: {time_context['time']}
• Зараз йде {time_context['week']} тиждень розкладу

РОЗКЛАД ПАР У НАУ (ЗАГАЛЬНИЙ):
1 пара: 08:00-09:35
2 пара: 09:50-11:25  
3 пара: 11:40-13:15
4 пара: 13:30-15:05
5 пара: 15:20-16:55
6 пара: 17:10-18:45
7 пара: 19:00-20:35

ТИ ВМІЄШ:
• Розповідати загальну інформацію про НАУ
• Допомагати з питаннями про навчання та вступ
• Підтримувати звичайну розмову
• Сказати який зараз час і номер поточної пари

ЯКЩО ПИТАЮТЬ ПРО КОНКРЕТНИЙ РОЗКЛАД:
"Для отримання розкладу конкретної групи потрібно встановити свою групу. Зараз я можу лише сказати загальну інформацію про час пар."

ПРАВИЛА ДЛЯ НОВИН ТА ІНФОРМАЦІЇ:
• ЗАВЖДИ додавай посилання на джерела новин у форматі: [Читати повністю](URL)
• Якщо використовуєш інформацію з новин НАУ - обов'язково вказуй посилання на саму новину
• Посилання допомагають користувачам перевірити інформацію та дізнатися більше
• Формат: "Згідно з новиною від [дата], [короткий зміст]. [Читати повністю](https://nau.edu.ua/...)"

СТИЛЬ СПІЛКУВАННЯ:
• Говори як друг-студент
• Будь корисним і точним
• Можеш жартувати, але в міру
• Використовуй емодзі де доречно

ПРАВИЛА ВІДПОВІДІ:
- Відповідай ТІЛЬКИ на ОСТАННЄ повідомлення користувача
- Попередні повідомлення - це контекст для розуміння теми
- НЕ повторюй свої попередні відповіді
- Якщо питають "а завтра?" - рахуй від сьогоднішньої дати"""

    def _format_context_for_llm(self, context_results: List[Dict]) -> str:
        """Форматування контексту для LLM"""
        if not context_results:
            return ""
        
        context_parts = []
        for result in context_results[:3]:
            content = result["content"]
            max_length = 400
            if len(content) > max_length:
                content = content[:max_length] + "..."
            context_parts.append(content)
        
        return "\n\n---\n\n".join(context_parts)

    def _seems_like_schedule_question(self, message: str) -> bool:
        """Перевірка, чи схоже питання на питання про розклад"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in SCHEDULE_KEYWORDS)

    def _fallback_response(self, message: str, group_name: Optional[str] = None) -> str:
        """Fallback відповідь, коли LLM недоступний"""
        
        # Привітання
        if any(word in message.lower() for word in GREETING_KEYWORDS):
            if group_name:
                return f"👋 Привіт! Я AI асистент КАІ для групи {group_name}. LLM зараз недоступний, але я можу допомогти з базовою інформацією."
            else:
                return "👋 Привіт! Я AI асистент КАІ. LLM зараз недоступний, але я можу допомогти з пошуком інформації про університет."
        
        # Питання про розклад без групи
        if self._seems_like_schedule_question(message) and not group_name:
            return "📅 Для отримання розкладу потрібно вказати групу. LLM зараз недоступний для детального аналізу."
        
        # Питання про розклад з групою
        if self._seems_like_schedule_question(message) and group_name:
            try:
                # Намагаємося надати базову інформацію про розклад
                schedule = self.schedule_manager.load_group_schedule(group_name)
                if schedule:
                    time_context = self.schedule_manager.get_current_time_context()
                    return f"📅 Розклад групи {group_name} завантажено. Сьогодні {time_context['day']}, {time_context['time']}. LLM недоступний для детального аналізу, але дані є."
                else:
                    return f"❌ Розклад групи {group_name} не знайдено. LLM також недоступний."
            except Exception as e:
                return f"⚠️ Помилка завантаження розкладу: {str(e)}"
        
        # Пошук в базі
        results = self.db.search(message, top_k=3)
        if not results:
            return "❌ На жаль, LLM недоступний, а в базі даних нічого не знайдено. Спробуйте перефразувати запит або зачекайте."
        
        return self._format_search_results(results)

    def _format_search_results(self, results: List[Dict]) -> str:
        """Форматування результатів пошуку"""
        if not results:
            return "Інформація не знайдена"
        
        parts = ["📚 Знайдена інформація (LLM недоступний):"]
        for i, result in enumerate(results[:3], 1):
            content = result["content"]
            if len(content) > 300:
                content = content[:300] + "..."
            parts.append(f"\n{i}. {content}")
        
        return "\n".join(parts)

    def set_group(self, group_name: str) -> bool:
        """
        Валідація групи (без збереження стану)
        Повертає True, якщо група є валідною і розклад доступний
        """
        logger.debug(f"ВАЛІДАЦІЯ ГРУПИ: {group_name}")
        
        if not self.schedule_manager.extract_group_name(group_name):
            logger.error(f"❌ ВАЛІДАЦІЯ ГРУПИ: Неправильний формат {group_name}")
            return False
        
        # Перевіряємо можливість завантаження розкладу
        schedule = self.schedule_manager.load_group_schedule(group_name)
        if schedule:
            logger.debug(f"✅ ВАЛІДАЦІЯ ГРУПИ: Розклад доступний для {group_name}")
            return True
        else:
            logger.error(f"❌ ВАЛІДАЦІЯ ГРУПИ: Розклад недоступний для {group_name}")
            return False

    def set_system_prompt_display(self, show: bool):
        """Встановлення відображення системного промпта"""
        self.show_system_prompt = show
        status = "увімкнено" if self.show_system_prompt else "вимкнено"
        logger.info(f"🤖 Відображення системного промпту: {status}")

    def get_current_lesson_info(self, group_name: str) -> Dict:
        """Отримання інформації про поточне заняття для групи"""
        return self.schedule_manager.get_current_lesson_info(group_name)

    def search_schedule(self, group_name: str, day: Optional[str] = None, 
                       week: Optional[int] = None) -> List[Dict]:
        """Пошук розкладу (через schedule_manager)"""
        return self.schedule_manager.load_group_schedule(group_name)

    def get_time_context(self) -> Dict:
        """Отримання контексту часу"""
        return self.schedule_manager.get_current_time_context()

    def validate_group_format(self, group_name: str) -> Optional[str]:
        """Валідація формату групи"""
        return self.schedule_manager.extract_group_name(group_name)

    def find_similar_groups(self, query: str) -> List[str]:
        """Пошук схожих груп"""
        return self.schedule_manager.search_similar_groups(query)

    def get_news(self, days: int = 30, category: Optional[str] = None) -> List[Dict]:
        """Отримання новин"""
        return self.db.search_recent_news(days=days, category=category)

    def search_database(self, query: str, category: Optional[str] = None, 
                       source: Optional[str] = None) -> List[Dict]:
        """Пошук у базі даних"""
        return self.db.search(
            query=query, 
            top_k=settings.SEARCH_TOP_K,
            category_filter=category,
            source_filter=source
        )