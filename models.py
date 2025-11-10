"""
NAU AI Assistant Backend - Data Models
Модели данных для API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Message(BaseModel):
    """Повідомлення в діалозі"""
    role: str = Field(..., description="Роль (user/assistant)")
    content: str = Field(..., description="Вміст повідомлення")

class ChatRequest(BaseModel):
    """Запит для чату"""
    user_name: str = Field(..., description="Ім'я користувача")
    message: str = Field(..., description="Повідомлення користувача", min_length=1)
    group_name: Optional[str] = Field(None, description="Назва групи (опціонально)")
    messages: Optional[List[Message]] = Field(default=[], description="Історія діалогу")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_name": "Іван", 
                "message": "А що у мене завтра?",
                "group_name": "Б-171-22-1-ІР",
                "messages": [
                    {"role": "user", "content": "Привіт! Які у мене пари сьогодні?"},
                    {"role": "assistant", "content": "Привіт! Сьогодні у тебе 3 пари..."}
                ]
            }
        }


class ChatResponse(BaseModel):
    """Відповідь від чату"""
    response: str = Field(..., description="Відповідь асистента")
    status: str = Field(..., description="Статус обробки (success/error)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Привіт! Сьогодні у тебе 3 пари: математика о 9:50, фізика о 11:40 і програмування о 13:30.",
                "status": "success"
            }
        }


class HealthResponse(BaseModel):
    """Відповідь перевірки стану сервера"""
    status: str = Field(..., description="Статус сервера (ok/error)")
    message: str = Field(..., description="Повідомлення про стан")
    version: Optional[str] = Field(None, description="Версія API")
    details: Optional[Dict[str, Any]] = Field(None, description="Додаткова інформація")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "message": "Всі компоненти працюють",
                "version": "2.0.0",
                "details": {
                    "lm_studio": "available",
                    "database_documents": 1250,
                    "components": ["db", "schedule_manager", "data_loader", "assistant"]
                }
            }
        }


class GroupValidationRequest(BaseModel):
    """Запит на валідацію групи"""
    group_name: str = Field(..., description="Назва групи для валідації")
    
    class Config:
        json_schema_extra = {
            "example": {
                "group_name": "Б-171-22-1-ІР"
            }
        }


class GroupValidationResponse(BaseModel):
    """Відповідь валідації групи"""
    is_valid: bool = Field(..., description="Чи є група валідною")
    extracted_name: Optional[str] = Field(None, description="Витягнута назва групи")
    message: str = Field(..., description="Повідомлення про результат валідації")
    suggestions: Optional[List[str]] = Field(None, description="Пропозиції схожих груп")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": True,
                "extracted_name": "Б-171-22-1-ІР",
                "message": "Група знайдена",
                "suggestions": []
            }
        }


class SystemStats(BaseModel):
    """Статистика системи"""
    database: Dict[str, Any] = Field(..., description="Статистика бази даних")
    time_context: Dict[str, Any] = Field(..., description="Контекст часу")
    system: Dict[str, Any] = Field(..., description="Системна інформація")
    
    class Config:
        json_schema_extra = {
            "example": {
                "database": {
                    "total_documents": 1250,
                    "categories": {"education": 340, "news": 280, "schedule": 630},
                    "unique_groups": 150
                },
                "time_context": {
                    "time": "14:30",
                    "date": "21.09.2025",
                    "day": "Понедiлок",
                    "week": 1,
                    "current_lesson": "4 пара (13:30-15:05)"
                },
                "system": {
                    "components_loaded": ["db", "schedule_manager", "data_loader", "assistant"],
                    "environment": "development"
                }
            }
        }


# Додаткові моделі для розширення функціональності

class ScheduleRequest(BaseModel):
    """Запит розкладу"""
    group_name: str = Field(..., description="Назва групи")
    day: Optional[str] = Field(None, description="День тижня")
    week: Optional[int] = Field(None, description="Номер тижня (1 або 2)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "group_name": "Б-171-22-1-ІР",
                "day": "Понедiлок",
                "week": 1
            }
        }


class LessonInfo(BaseModel):
    """Інформація про заняття"""
    number: str = Field(..., description="Номер пари")
    time: str = Field(..., description="Час пари")
    subject: str = Field(..., description="Предмет")
    teacher: Optional[str] = Field(None, description="Викладач")
    room: Optional[str] = Field(None, description="Аудиторія")
    type: Optional[str] = Field(None, description="Тип заняття")


class ScheduleResponse(BaseModel):
    """Відповідь з розкладом"""
    group: str = Field(..., description="Назва групи")
    day: str = Field(..., description="День тижня")
    week: int = Field(..., description="Номер тижня")
    lessons: List[LessonInfo] = Field(..., description="Список занять")
    
    class Config:
        json_schema_extra = {
            "example": {
                "group": "Б-171-22-1-ІР",
                "day": "Понедiлок",
                "week": 1,
                "lessons": [
                    {
                        "number": "1",
                        "time": "08:00-09:35",
                        "subject": "Математичний аналіз",
                        "teacher": "Іванов І.І.",
                        "room": "ауд. 201",
                        "type": "лекція"
                    }
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Стандартна відповідь про помилку"""
    error: str = Field(..., description="Опис помилки")
    details: Optional[Dict[str, Any]] = Field(None, description="Додаткові деталі помилки")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Група не знайдена",
                "details": {
                    "group_name": "Б-999-99-9-ХХ",
                    "suggestions": ["Б-171-22-1-ІР", "Б-172-22-1-ІР"]
                }
            }
        }