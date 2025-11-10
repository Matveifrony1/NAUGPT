"""
NAU AI Assistant Backend - FastAPI Server
Основний файл сервера
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from typing import Dict

from models import ChatRequest, ChatResponse, HealthResponse, GroupValidationRequest, GroupValidationResponse
from assistant import NAUAssistant
from schedule import ScheduleManager
from database import VectorDatabase
from data_loader import DataLoader
from config import settings
from logger import get_logger

logger = get_logger(__name__)


# Глобальні об'єкти системи
system_components: Dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events для ініціалізації та очищення"""
    logger.info("Запуск NAU AI Assistant Backend...")
    
    try:
        # Ініціалізація всіх компонентів
        logger.info("Ініціалізація компонентів...")
        
        # База даних
        db = VectorDatabase(db_path=settings.VECTOR_DB_PATH)
        
        # Менеджер розкладу
        schedule_manager = ScheduleManager()
        
        # Завантажувач даних
        data_loader = DataLoader()
        
        # AI Асистент
        assistant = NAUAssistant(db, schedule_manager)
        
        # Зберігаємо компоненти глобально
        system_components.update({
            "db": db,
            "schedule_manager": schedule_manager,
            "data_loader": data_loader,
            "assistant": assistant
        })
        
        # Перевірка LM Studio
        lm_available = await assistant.check_lm_studio()
        if not lm_available:
            logger.critical("⚠️ LM Studio недоступний - сервер працює в режимі fallback")
        
        # Завантаження даних при першому запуску
        await _initial_data_load(db, data_loader)
        
        logger.info("✅ Backend готовий до роботи!")
        logger.info(f"🌐 Сервер доступний за адресою: http://{settings.HOST}:{settings.PORT}")
        logger.info(f"📚 Документація API: http://{settings.HOST}:{settings.PORT}/docs")
        
        yield
        
    except Exception as e:
        logger.critical(f"❌ Критична помилка ініціалізації: {e}")
        raise
    finally:
        logger.info("🔚 Завершення роботи backend...")


async def _initial_data_load(db: VectorDatabase, data_loader: DataLoader):
    """Завантаження ТІЛЬКИ з папки naunews"""
    stats = db.get_stats()
    
    if stats["total_documents"] == 0:
        logger.info("База даних порожня. Завантажуємо дані з папки naunews...")
        
        all_documents = data_loader.load_all_data(news_dir="./naunews")
        
        if all_documents:
            db.add_documents(all_documents)
            logger.info(f"✅ Завантажено {len(all_documents)} новин до бази даних")
        else:
            logger.error("⚠️ Не знайдено новин для завантаження. Перевірте папку ./naunews")
    else:
        logger.debug(f"База містить {stats['total_documents']} документів")


# Создание FastAPI приложения
app = FastAPI(
    title="NAU AI Assistant API",
    description="Backend API для AI-асистента Національного авіаційного університету",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware для работы с frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Корневой endpoint"""
    return HealthResponse(
        status="ok",
        message="NAU AI Assistant Backend працює",
        version="2.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Перевірка стану сервера"""
    try:
        # Перевіряємо компоненти
        assistant = system_components.get("assistant")
        if not assistant:
            raise Exception("Assistant не ініціалізовано")
        
        # Перевіряємо LM Studio
        lm_available = await assistant.check_lm_studio()
        
        # Перевіряємо базу даних
        db = system_components.get("db")
        stats = db.get_stats() if db else {"error": "DB not available"}
        
        return HealthResponse(
            status="ok",
            message="Всі компоненти працюють",
            details={
                "lm_studio": "available" if lm_available else "unavailable",
                "database_documents": stats.get("total_documents", 0),
                "components": list(system_components.keys())
            }
        )
        
    except Exception as e:
        return HealthResponse(
            status="error",
            message=f"Помилка перевірки: {str(e)}"
        )



@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Основний endpoint для чату з підтримкою контексту діалогу
    """
    try:
        assistant = system_components.get("assistant")
        if not assistant:
            raise HTTPException(status_code=500, detail="Assistant не ініціалізовано")
        
        logger.info(f"📨 CHAT REQUEST: user={request.user_name}, group={request.group_name}, history={len(request.messages or [])}")
        
        messages = [msg.dict() for msg in request.messages] if request.messages else None
        
        assistant.set_system_prompt_display(settings.LOG_SYSTEM_PROMPTS)

        # Обробляємо запит
        response_text = await assistant.process_query(
            message=request.message,
            group_name=request.group_name,
            user_name=request.user_name,
            messages=messages
        )
        
        return ChatResponse(
            response=response_text,
            status="success"
        )
        
    except Exception as e:
        print(f"❌ CHAT ERROR: {str(e)}")
        return ChatResponse(
            response=f"Вибачте, сталася помилка: {str(e)}",
            status="error"
        )


@app.post("/group/validate", response_model=GroupValidationResponse)
async def validate_group(request: GroupValidationRequest):
    """Валідація назви групи"""
    try:
        schedule_manager = system_components.get("schedule_manager")
        if not schedule_manager:
            raise HTTPException(status_code=500, detail="ScheduleManager не ініціалізовано")
        
        # Витягуємо назву групи
        extracted_group = schedule_manager.extract_group_name(request.group_name)
        
        if extracted_group:
            # Перевіряємо можливість завантаження розкладу
            schedule = schedule_manager.load_group_schedule(extracted_group)
            
            return GroupValidationResponse(
                is_valid=bool(schedule),
                extracted_name=extracted_group,
                message="Група знайдена" if schedule else "Група не знайдена або недоступна"
            )
        else:
            # Шукаємо схожі групи
            similar = schedule_manager.search_similar_groups(request.group_name)
            
            return GroupValidationResponse(
                is_valid=False,
                extracted_name=None,
                message="Неправильний формат групи",
                suggestions=similar[:5] if similar else []
            )
            
    except Exception as e:
        return GroupValidationResponse(
            is_valid=False,
            extracted_name=None,
            message=f"Помилка валідації: {str(e)}"
        )


@app.get("/stats")
async def get_stats():
    """Отримання статистики системи"""
    try:
        db = system_components.get("db")
        schedule_manager = system_components.get("schedule_manager")
        
        if not db or not schedule_manager:
            raise HTTPException(status_code=500, detail="Компоненти не ініціалізовані")
        
        # Статистика бази даних
        db_stats = db.get_stats()
        
        # Контекст часу
        time_context = schedule_manager.get_current_time_context()
        
        return {
            "database": db_stats,
            "time_context": time_context,
            "system": {
                "components_loaded": list(system_components.keys()),
                "environment": settings.ENVIRONMENT
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка отримання статистики: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Запуск NAU AI Assistant Backend...")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )