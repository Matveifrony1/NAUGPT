"""
NAU AI Assistant Backend - Logging Configuration
Централізована система логування з правильною ієрархією рівнів
"""

import logging
import sys
from config import settings

# ============================================================
# ІЄРАРХІЯ РІВНІВ ЛОГУВАННЯ (від найнижчого до найвищого):
# ============================================================
# DEBUG (10)    - Детальна діагностика для розробників
# INFO (20)     - Загальна інформація про роботу системи
# WARNING (30)  - Попередження про потенційні проблеми
# ERROR (40)    - Помилки, які не зупиняють роботу
# CRITICAL (50) - Критичні помилки, які зупиняють систему
# ============================================================

# Кастомні кольори для консолі (опціонально)
class ColoredFormatter(logging.Formatter):
    """Форматер з кольорами для різних рівнів"""
    
    # ANSI escape коди для кольорів
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan (блакитний)
        'INFO': '\033[32m',       # Green (зелений)
        'WARNING': '\033[33m',    # Yellow (жовтий)
        'ERROR': '\033[31m',      # Red (червоний)
        'CRITICAL': '\033[35m',   # Magenta (пурпурний)
        'RESET': '\033[0m'        # Reset (скидання)
    }
    
    def format(self, record):
        # Додаємо колір до рівня логу
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        return super().format(record)


# Створюємо форматер
formatter = ColoredFormatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Створюємо handler для консолі
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)


def get_logger(name: str) -> logging.Logger:
    """
    Отримати logger для модуля
    
    Args:
        name: Ім'я модуля (використовуйте __name__)
    
    Returns:
        logging.Logger: Налаштований logger
    
    Example:
        logger = get_logger(__name__)
        logger.debug("Детальна діагностика")
        logger.info("Загальна інформація")
        logger.warning("Попередження")
        logger.error("Помилка")
        logger.critical("Критична помилка")
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    
    # Додаємо handler тільки якщо його ще немає
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    # Не пропагуємо до root logger (щоб не дублювати)
    logger.propagate = False
    
    return logger


# Основний logger для всього проєкту
main_logger = get_logger("nau_assistant")