import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
import time
from logger import get_logger

logger = get_logger(__name__)

class ScheduleManager:
    """Менеджер розкладу КАІ з логікою retry"""
    
    def __init__(self):
        self.base_url = "https://portal.nau.edu.ua"
        self.groups_list_url = f"{self.base_url}/schedule/group/list"
        self.days = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
        self.time_slots = [
            ("1", "08:00", "09:35"),
            ("2", "09:50", "11:25"),
            ("3", "11:40", "13:15"),
            ("4", "13:30", "15:05"),
            ("5", "15:20", "16:55"),
            ("6", "17:10", "18:45"),
            ("7", "19:00", "20:35")
        ]
        self.cached_schedules = {}
        self.max_retries = 10  # максимальна кількість спроб
        self.retry_delay = 10.0  # базова затримка між спробами
        
    def _make_request_with_retry(self, url: str, timeout: int = 10) -> Optional[requests.Response]:
        """Виконання HTTP запиту з логікою retry"""
        for attempt in range(self.max_retries):
            try:                
                response = requests.get(
                    url, 
                    timeout=timeout,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )
                response.raise_for_status()  # Перевіряємо HTTP статус
                return response
                
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Спроба {attempt + 1} не вдалася: {e}")
                
                if attempt < self.max_retries - 1:
                    # Экспоненциальная задержка: 1s, 2s, 4s, 8s, ...
                    delay = self.retry_delay * (2 ** attempt)
                    logger.debug(f"⏳ Чекаємо {delay:.1f}s перед наступною спробою...")
                    time.sleep(delay)
                else:
                    logger.critical(f"💥 Усі {self.max_retries} спроби вичерпані")
                    return None
        
        return None
    
    def extract_group_name(self, text: str) -> Optional[str]:
        """Витяг назви групи з тексту"""
        # Патерн для груп КАІ 
        pattern = r'\b[БМКД]-\d{3}-\d{2}-\d-[А-ЯІЇЄҐA-Z]{1,4}\b'
        matches = re.findall(pattern, text.upper())
        return matches[0] if matches else None
    
    def get_current_week(self) -> int:
        """Визначення поточного навчального тижня (1 або 2)"""
        # 1 вересня 2025 року - початок семестру з тижня 1
        semester_start = datetime(2025, 9, 1)
        now = datetime.now()
        
        if now < semester_start:
            return 1
            
        days_passed = (now - semester_start).days
        weeks_passed = days_passed // 7
        
        # Чергування: непарні тижні = 1, парні = 2
        return (weeks_passed % 2) + 1
    
    def get_current_time_context(self) -> Dict:
        """Отримання контексту поточного часу"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = self.days[now.weekday()] if now.weekday() < 7 else None
        current_week = self.get_current_week()
        
        # Визначаємо поточну і наступну пару
        current_lesson = None
        next_lesson = None
        
        for num, start, end in self.time_slots:
            if start <= current_time <= end:
                current_lesson = f"{num} пара ({start}-{end})"
            elif current_time < start and not next_lesson:
                next_lesson = f"{num} пара ({start}-{end})"
                break
        
        return {
            "time": current_time,
            "date": now.strftime("%d.%m.%Y"),
            "day": current_day,
            "week": current_week,
            "current_lesson": current_lesson,
            "next_lesson": next_lesson,
            "is_weekend": now.weekday() >= 5
        }
    
    def find_group_url(self, group_name: str) -> Optional[str]:
        """Пошук URL сторінки розкладу групи з retry"""
        logger.debug(f"🔍 ПОШУК ГРУПИ: {group_name}")
        
        response = self._make_request_with_retry(self.groups_list_url)
        if not response:
            return None
            
        try:
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                if link.get_text(strip=True) == group_name:
                    href = link.get('href')
                    if href and '/schedule/group?id=' in href:
                        full_url = self.base_url + href
                        print(f"✅ ЗНАЙДЕНО URL: {full_url}")
                        return full_url
            
            logger.error(f"❌ Група {group_name} не знайдено в списку")
            return None
            
        except Exception as e:
            logger.error(f"❌ Помилка парсингу списку груп: {e}")
            return None
    
    def search_similar_groups(self, query: str) -> List[str]:
        """Пошук схожих груп з retry"""
        response = self._make_request_with_retry(self.groups_list_url)
        if not response:
            return []
            
        try:
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            groups = []
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True)
                if query.upper() in text.upper() and '/schedule/group?id=' in link.get('href', ''):
                    groups.append(text)
            
            return sorted(list(set(groups)))[:15]
        except Exception as e:
            logger.error(f"❌ Помилка пошуку груп: {e}")
            return []
    
    def parse_schedule_page(self, url: str) -> Optional[Dict]:
        """Парсинг сторінки розкладу з retry"""
        logger.debug(f"📄 ПАРСИНГ РОЗКЛАДУ: {url}")
        
        response = self._make_request_with_retry(url)
        if not response:
            return None
            
        try:
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Название группы
            group_elem = soup.find('span', class_='group-name')
            group_name = group_elem.get_text(strip=True) if group_elem else "Unknown"
            schedule = {
                "group": group_name,
                "weeks": {1: {}, 2: {}}
            }
            
            # Парсимо тижні
            week_sections = soup.find_all('div', class_='wrapper')
            
            for week_idx, section in enumerate(week_sections[:2], 1):             
                table = section.find('table', class_='schedule')
                if not table:
                    print(f"❌ ПАРСИНГ: Таблиця не знайдена для тижня {week_idx}")
                    continue
                    
                tbody = table.find('tbody')
                if not tbody:
                    print(f"❌ ПАРСИНГ: tbody не знайдено для тижня {week_idx}")
                    continue
                
                rows = tbody.find_all('tr')              
                for row_idx, row in enumerate(rows):
                    hour_cell = row.find('th', class_='hour-name')
                    if not hour_cell:
                        continue
                    
                    hour_num = hour_cell.find('div', class_='name')
                    if not hour_num:
                        continue
                    
                    lesson_num = hour_num.get_text(strip=True)
                    
                    # Парсим дни
                    day_cells = row.find_all('td')
                    
                    for day_idx, cell in enumerate(day_cells):
                        if day_idx >= len(self.days):
                            break
                        
                        day = self.days[day_idx]
                        if day not in schedule["weeks"][week_idx]:
                            schedule["weeks"][week_idx][day] = {}
                        
                        pairs_div = cell.find('div', class_='pairs')
                        if not pairs_div:
                            continue
                        
                        lessons = []
                        pair_divs = pairs_div.find_all('div', class_='pair')
                        
                        for pair in pair_divs:
                            lesson_data = self._parse_lesson(pair)
                            if lesson_data:
                                lessons.append(lesson_data)
                        
                        if lessons:
                            schedule["weeks"][week_idx][day][lesson_num] = lessons
            
            # Підсумкова статистика
            total_lessons = 0
            for week_num, week_data in schedule["weeks"].items():
                for day, day_schedule in week_data.items():
                    day_lessons = sum(len(lessons) for lessons in day_schedule.values())
                    total_lessons += day_lessons
            
            logger.debug(f"ПАРСИНГ ВСЬОГО: {total_lessons} занять для групи {group_name}")
            return schedule
            
        except Exception as e:
            logger.error(f"❌ ПАРСИНГ ПОМИЛКА: {e}")
            return None
    
    def _parse_lesson(self, pair_div) -> Optional[Dict]:
        """Парсинг одного заняття"""
        lesson = {}
        
        subject = pair_div.find('div', class_='subject')
        if subject:
            subject_text = subject.get_text(strip=True).replace('\n', ' ')
            # Прибираємо додатковий текст з датами в дужках
            subject_text = re.sub(r'\(з .* тижн.*?\)', '', subject_text)
            subject_text = re.sub(r'\(с .* недели.*?\)', '', subject_text)
            subject_text = re.sub(r'\(from .* week.*?\)', '', subject_text)
            # Прибираємо множинні пробіли
            subject_text = re.sub(r'\s+', ' ', subject_text).strip()
            lesson['subject'] = subject_text
        
        teachers = []
        for teacher in pair_div.find_all('div', class_='teacher'):
            text = teacher.get_text(strip=True)
            if text and not text.startswith('Розклад буде'):
                teachers.append(text)
        if teachers:
            lesson['teacher'] = ', '.join(teachers)
        
        room = pair_div.find('div', class_='room')
        if room:
            room_span = room.find('span')
            if room_span:
                lesson['room'] = f"ауд. {room_span.get_text(strip=True)}"
        
        activity = pair_div.find('div', class_='activity-tag')
        if activity:
            lesson['type'] = activity.get_text(strip=True)
        
        return lesson if lesson else None
    
    def load_group_schedule(self, group_name: str) -> Optional[Dict]:
        """Завантаження розкладу групи з retry"""
        logger.debug(f"ЗАВАНТАЖЕННЯ РОЗКЛАДУ: Група {group_name}")
        
        # Проверяем кэш
        if group_name in self.cached_schedules:
            logger.debug(f"ЗАВАНТАЖЕННЯ: Знайдено в кеші")
            return self.cached_schedules[group_name]
            
        url = self.find_group_url(group_name)
        if not url:
            logger.error(f"❌ ЗАВАНТАЖЕННЯ: URL не знайдено для групи {group_name}")
            return None
        
        logger.debug(f"ЗАВАНТАЖЕННЯ: Знайдено URL: {url}")
        
        # Парсим расписание с retry
        schedule = self.parse_schedule_page(url)
        if schedule:
            self.cached_schedules[group_name] = schedule
            logger.debug(f"✅ ЗАВАНТАЖЕННЯ: Розклад {group_name} збережено в кеш")
        else:
            logger.error(f"❌ ЗАВАНТАЖЕННЯ: Помилка парсингу розкладу {group_name}")
        
        return schedule
    
    def format_schedule_for_system_prompt(self, schedule: Dict) -> str:
        """Форматування розкладу для системного промпта LLM"""
        from datetime import timedelta
        
        lines = []
        current_week = self.get_current_week()
        now = datetime.now()
        
        # Знаходимо понеділок поточного тижня
        days_since_monday = now.weekday()
        current_monday = now - timedelta(days=days_since_monday)
        
        lines.append(f"ГРУПА {schedule['group']} - ПОВНИЙ РОЗКЛАД")
        lines.append("=" * 40)
        lines.append(f"ПОТОЧНИЙ ТИЖДЕНЬ: {current_week}")
        lines.append("")
        
        # Визначаємо дати для обох тижнів
        if current_week == 1:
            week1_monday = current_monday
            week2_monday = current_monday + timedelta(days=7)
        else:  # current_week == 2
            week1_monday = current_monday - timedelta(days=7)
            week2_monday = current_monday
        
        # Проходимо по тижнях
        for week_num in [1, 2]:
            week_data = schedule["weeks"].get(week_num, {})
            if not week_data:
                continue
            
            # Обчислюємо дати тижня
            if week_num == 1:
                week_monday = week1_monday
            else:
                week_monday = week2_monday
            
            week_sunday = week_monday + timedelta(days=6)
            
            # Форматуємо дати
            monday_str = week_monday.strftime("%d.%m")
            sunday_str = week_sunday.strftime("%d.%m")
            
            # Визначаємо статус тижня
            if week_num == current_week:
                marker = f" ({monday_str} - {sunday_str}) ← ЗАРАЗ"
            elif week_num > current_week:
                marker = f" ({monday_str} - {sunday_str}) наступний"
            else:
                marker = f" ({monday_str} - {sunday_str}) попередній"
            
            lines.append(f"ТИЖДЕНЬ {week_num}{marker}:")
            
            # Проходимо по днях (без неділі)
            for day_idx, day in enumerate(self.days[:6]):
                day_schedule = week_data.get(day, {})
                
                # Додаємо дату дня
                day_date = week_monday + timedelta(days=day_idx)
                day_date_str = day_date.strftime("%d.%m")
                
                if day_schedule:
                    lines.append(f"{day} ({day_date_str}):")
                    # Сортуємо пари за номерами
                    sorted_lessons = sorted(day_schedule.keys(), key=lambda x: int(x) if x.isdigit() else 0)
                    
                    for lesson_num in sorted_lessons:
                        lessons = day_schedule[lesson_num]
                        time_slot = self.time_slots[int(lesson_num)-1] if lesson_num.isdigit() else None
                        time_str = f"{time_slot[1]}-{time_slot[2]}" if time_slot else ""
                        
                        for lesson in lessons:
                            subject = lesson.get('subject', 'Невідомо')
                            teacher = lesson.get('teacher', '')
                            room = lesson.get('room', '')
                            
                            # Максимально стислий формат
                            lesson_line = f"  {lesson_num} ({time_str}) {subject}"
                            if teacher:
                                # Скорочуємо довгі імена викладачів
                                if len(teacher) > 25:
                                    teacher = teacher[:22] + "..."
                                lesson_line += f" - {teacher}"
                            if room:
                                lesson_line += f" - {room}"
                            
                            lines.append(lesson_line)
                else:
                    lines.append(f"{day} ({day_date_str}): пар немає")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def get_current_lesson_info(self, group_name: str) -> Dict:
        """Отримання інформації про поточну пару для групи"""
        context = self.get_current_time_context()
        
        if context["is_weekend"]:
            return {
                "status": "weekend",
                "message": "Сьогодні вихідний день",
                "context": context
            }
        
        # Завантажуємо розклад
        schedule = self.load_group_schedule(group_name)
        if not schedule:
            return {
                "status": "error",
                "message": f"Розклад групи {group_name} не знайдено",
                "context": context
            }
        
        # Отримуємо розклад на сьогодні
        week = context["week"]
        day = context["day"]
        
        today_schedule = schedule["weeks"].get(week, {}).get(day, {})
        
        if not today_schedule:
            return {
                "status": "no_lessons",
                "message": f"На сьогодні ({day}, тиждень {week}) пар немає",
                "context": context
            }
        
        # Формуємо інформацію про поточну та наступну пару
        result = {
            "status": "ok",
            "group": group_name,
            "context": context,
            "current": None,
            "next": None,
            "today_lessons": []
        }
        
        # Знаходимо поточну і наступну пару
        for lesson_num in ["1", "2", "3", "4", "5", "6", "7"]:
            if lesson_num in today_schedule:
                lesson_time = self.time_slots[int(lesson_num)-1]
                time_str = f"{lesson_time[1]}-{lesson_time[2]}"
                
                for lesson in today_schedule[lesson_num]:
                    lesson_info = {
                        "number": lesson_num,
                        "time": time_str,
                        **lesson
                    }
                    result["today_lessons"].append(lesson_info)
                    
                    # Перевіряємо, чи це не поточна пара
                    if context["current_lesson"] and lesson_num in context["current_lesson"]:
                        result["current"] = lesson_info
                    # Перевіряємо, чи не наступна
                    elif context["next_lesson"] and lesson_num in context["next_lesson"]:
                        if not result["next"]:  # Беремо тільки першу наступну
                            result["next"] = lesson_info
        
        return result