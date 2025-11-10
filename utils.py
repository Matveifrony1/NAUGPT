"""
NAU AI Assistant Backend - Utility Functions
Допоміжні функції для роботи backend'а
"""

import re
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from logger import get_logger

logger = get_logger(__name__)



class TextUtils:
    """Утиліти для роботи з текстом"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Очищення тексту від зайвих символів"""
        if not text:
            return ""
        
        # Видаляємо множинні пробіли та переноси рядків
        text = re.sub(r'\s+', ' ', text)
        # Прибираємо зайві символи
        text = re.sub(r'[^\w\s\-\.\,\!\?\:\;\"\'А-Яа-яІіЇїЄєҐґ]', '', text)
        return text.strip()
    
    @staticmethod
    def extract_group_name(text: str) -> Optional[str]:
        """Витяг назви групи з тексту"""
        pattern = r'\b[БМКД]-\d{3}-\d{2}-\d-[А-ЯІЇЄҐA-Z]{1,4}\b'
        matches = re.findall(pattern, text.upper())
        return matches[0] if matches else None
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 300, suffix: str = "...") -> str:
        """Обрізання тексту до вказаної довжини"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def normalize_day_name(day: str) -> str:
        """Нормалізація назви дня тижня"""
        day_mapping = {
            'понедельник': 'Понеділок',
            'вторник': 'Вівторок', 
            'среда': 'Середа',
            'четверг': 'Четвер',
            'пятница': 'П\'ятниця',
            'суббота': 'Субота',
            'воскресенье': 'Неділя',
            'monday': 'Понеділок',
            'tuesday': 'Вівторок',
            'wednesday': 'Середа',
            'thursday': 'Четвер',
            'friday': 'П\'ятниця',
            'saturday': 'Субота',
            'sunday': 'Неділя'
        }
        return day_mapping.get(day.lower(), day)


class DateUtils:
    """Утиліти для роботи з датами"""
    
    @staticmethod
    def get_current_week_number() -> int:
        """Отримання номера поточного навчального тижня"""
        semester_start = datetime(2025, 9, 1)
        now = datetime.now()
        
        if now < semester_start:
            return 1
            
        days_passed = (now - semester_start).days
        weeks_passed = days_passed // 7
        return (weeks_passed % 2) + 1
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """Розбір дати з різних форматів"""
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y", 
            "%d.%m.%Y",
            "%Y-%m-%d",
            "%d/%m/%y",
            "%d-%m-%y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    
    @staticmethod
    def format_date(date: datetime, format_type: str = "ukrainian") -> str:
        """Форматування дати"""
        if format_type == "ukrainian":
            return date.strftime("%d.%m.%Y")
        elif format_type == "iso":
            return date.isoformat()
        else:
            return date.strftime("%Y-%m-%d")
    
    @staticmethod
    def is_recent(date: datetime, days: int = 30) -> bool:
        """Перевірка, чи є дата недавньою"""
        cutoff = datetime.now() - timedelta(days=days)
        return date >= cutoff


class ScheduleUtils:
    """Утиліти для роботи з розкладом"""
    
    TIME_SLOTS = [
        ("1", "08:00", "09:35"),
        ("2", "09:50", "11:25"),
        ("3", "11:40", "13:15"),
        ("4", "13:30", "15:05"),
        ("5", "15:20", "16:55"),
        ("6", "17:10", "18:45"),
        ("7", "19:00", "20:35")
    ]
    
    @staticmethod
    def get_current_lesson() -> Optional[Dict]:
        """Визначення поточної пари"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        for num, start, end in ScheduleUtils.TIME_SLOTS:
            if start <= current_time <= end:
                return {
                    "number": num,
                    "start": start,
                    "end": end,
                    "is_active": True
                }
        return None
    
    @staticmethod
    def get_next_lesson() -> Optional[Dict]:
        """Визначення наступної пари"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        for num, start, end in ScheduleUtils.TIME_SLOTS:
            if current_time < start:
                return {
                    "number": num,
                    "start": start,
                    "end": end,
                    "is_next": True
                }
        return None
    
    @staticmethod
    def format_lesson_time(lesson_num: str) -> str:
        """Форматування часу пари"""
        for num, start, end in ScheduleUtils.TIME_SLOTS:
            if num == lesson_num:
                return f"{start}-{end}"
        return ""


class HashUtils:
    """Утиліти для хешування"""
    
    @staticmethod
    def generate_content_hash(content: str) -> str:
        """Генерація хешу контенту"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_document_id(content: str, metadata: Dict) -> str:
        """Генерація ID документа"""
        source = metadata.get('source', '')
        title = metadata.get('title', '')
        combined = f"{source}_{title}_{content[:100]}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]


class ValidationUtils:
    """Утиліти для валідації"""
    
    @staticmethod
    def validate_group_format(group_name: str) -> bool:
        """Валідація формату групи"""
        pattern = r'^[БМКД]-\d{3}-\d{2}-\d-[А-ЯІЇЄҐA-Z]{1,4}$'
        return bool(re.match(pattern, group_name.upper()))
    
    @staticmethod
    def validate_user_name(name: str) -> bool:
        """Валідація імені користувача"""
        if not name or len(name.strip()) < 2:
            return False
        # Дозволяємо тільки літери, цифри, пробіли та базові символи
        pattern = r'^[А-Яа-яІіЇїЄєҐґA-Za-z0-9\s\-\.]{2,50}$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def validate_message(message: str) -> bool:
        """Валідація повідомлення"""
        if not message or len(message.strip()) < 1:
            return False
        if len(message) > 2000:  # Максимальна довжина повідомлення
            return False
        return True


class FileUtils:
    """Утиліти для роботи з файлами"""
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """Створення директорії, якщо вона не існує"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def read_json_file(file_path: Union[str, Path]) -> Optional[Dict]:
        """Читання JSON файлу"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Помилка читання JSON файлу {file_path}: {e}")
            return None
    
    @staticmethod
    def write_json_file(data: Dict, file_path: Union[str, Path]) -> bool:
        """Запис JSON файлу"""
        try:
            FileUtils.ensure_directory(Path(file_path).parent)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Помилка запису JSON файлу {file_path}: {e}")
            return False


class AsyncUtils:
    """Утиліти для асинхронної роботи"""
    
    @staticmethod
    async def run_with_timeout(coro, timeout: float = 30.0):
        """Виконання корутини з таймаутом"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Операція перевищила таймаут {timeout}s")
            return None
    
    @staticmethod
    async def retry_async(func, max_attempts: int = 3, delay: float = 1.0):
        """Повторне виконання асинхронної функції"""
        for attempt in range(max_attempts):
            try:
                return await func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                logger.warning(f"Спроба {attempt + 1} не вдалася: {e}")
                await asyncio.sleep(delay * (2 ** attempt))  # Експоненціальна затримка


class CategoryUtils:
    """Утиліти для категоризації"""
    
    CATEGORY_KEYWORDS = {
        "education": ["факультет", "кафедра", "спеціальність", "освітн", "навчан"],
        "admission": ["вступ", "приймальн", "абітурієнт", "документи", "заява"],
        "schedule": ["розклад", "пара", "заняття", "лекція", "семінар"],
        "news": ["новин", "подій", "останн", "актуальн", "свіж"],
        "contacts": ["контакт", "телефон", "адрес", "email", "зв'язатися"],
        "general": []
    }
    
    @staticmethod
    def categorize_content(title: str, content: str) -> str:
        """Автоматична категоризація контенту"""
        text = f"{title} {content}".lower()
        
        category_scores = {}
        for category, keywords in CategoryUtils.CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return "general"


class ResponseUtils:
    """Утиліти для форматування відповідей"""
    
    @staticmethod
    def format_error_response(error: str, details: Optional[Dict] = None) -> Dict:
        """Форматування відповіді про помилку"""
        response = {
            "status": "error",
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        if details:
            response["details"] = details
        return response
    
    @staticmethod
    def format_success_response(data: Any, message: str = "Success") -> Dict:
        """Форматування успішної відповіді"""
        return {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_schedule_response(schedule: Dict, group: str) -> str:
        """Форматування відповіді з розкладом"""
        if not schedule:
            return f"Розклад для групи {group} не знайдено"
        
        # Базовое форматирование
        lines = [f"Розклад групи {group}"]
        current_week = DateUtils.get_current_week_number()
        
        for week_num in [1, 2]:
            week_data = schedule.get("weeks", {}).get(week_num, {})
            if not week_data:
                continue
                
            marker = " ← ПОТОЧНА" if week_num == current_week else ""
            lines.append(f"\nТиждень {week_num}{marker}:")
            
            for day, day_schedule in week_data.items():
                if day_schedule:
                    lines.append(f"\n{day}:")
                    for lesson_num, lessons in day_schedule.items():
                        time_str = ScheduleUtils.format_lesson_time(lesson_num)
                        for lesson in lessons:
                            subject = lesson.get('subject', 'Не вказано')
                            lines.append(f"  {lesson_num} пара ({time_str}): {subject}")
        
        return "\n".join(lines)


class ConfigUtils:
    """Утиліти для роботи з конфігурацією"""
    
    @staticmethod
    def load_env_vars() -> Dict[str, str]:
        """Завантаження змінних оточення"""
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        return {
            key: value for key, value in os.environ.items()
            if key.startswith(('NAU_', 'LM_', 'VECTOR_', 'SCHEDULE_'))
        }
    
    @staticmethod
    def validate_required_vars(required_vars: List[str]) -> Dict[str, bool]:
        """Валідація обов'язкових змінних"""
        import os
        return {var: var in os.environ for var in required_vars}

class ContextUtils:
    """Утиліти для управління контекстом діалогу"""
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """Приблизний підрахунок токенів (1 токен ≈ 4 символи для кирилиці)"""
        return len(text) // 4
    
    @staticmethod
    def truncate_messages(messages: List[Dict], max_tokens: int) -> List[Dict]:
        """Розумна обрізка повідомлень - залишаємо останні"""
        if not messages:
            return []
        
        total_tokens = 0
        result = []
        
        # Йдемо з кінця, залишаємо останні повідомлення
        for message in reversed(messages):
            message_tokens = ContextUtils.count_tokens(message["content"])
            if total_tokens + message_tokens <= max_tokens:
                result.insert(0, message)
                total_tokens += message_tokens
            else:
                break
        
        return result

# Експорт основних утиліт
__all__ = [
    'TextUtils',
    'DateUtils', 
    'ScheduleUtils',
    'HashUtils',
    'ValidationUtils',
    'FileUtils',
    'AsyncUtils',
    'CategoryUtils',
    'ResponseUtils',
    'ConfigUtils',
    'ContextUtils'
]