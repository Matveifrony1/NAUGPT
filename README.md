# 🎓 NAU AI Assistant Backend

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5.23-orange.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Intelligent backend system for National Aviation University (NAU). Enables students and staff to get information about schedules, news, and university events through natural language conversations.

[🇺🇦 Українська версія](#українська-версія) | [🇬🇧 English version](#english-version)

---

## English Version

### 📖 About

NAU AI Assistant Backend is a production-ready AI-powered system built with FastAPI that helps students and staff of the National Aviation University access information through conversational interface. The system understands natural language queries in Ukrainian, Russian, and English.

The backend handles complex query processing, semantic search through university news and information, real-time schedule parsing from the university portal, and generates context-aware responses using large language models.

### ✨ What Can It Do

**Information Retrieval**
- Search through university news and announcements
- Find information about faculties and departments
- Get details about events, conferences, and activities
- Access contact information and administrative data

**Schedule Management**
- Parse schedules directly from NAU portal
- Determine current and next classes
- Calculate academic week numbers
- Support for alternating schedule weeks

**Intelligent Conversations**
- Understand context from conversation history
- Route queries to relevant information sources
- Validate search results for relevance
- Reformulate queries automatically for better results
- Generate natural, friendly responses

### 🛠 Technology Stack

**Core Framework**
- FastAPI 0.115.0 - Modern async web framework
- Uvicorn 0.30.6 - ASGI server
- Pydantic 2.10.0 - Data validation

**AI/ML Components**
- Google Gemini 2.0 Flash / LM Studio - Response generation
- ChromaDB 0.5.23 - Vector database
- Jina Embeddings v3 - Multilingual text embeddings
- Sentence-Transformers 3.3.1 - Embedding framework

**Data Processing**
- BeautifulSoup4 4.12.3 - HTML parsing
- Pandas 2.2.3 - Data manipulation
- RapidFuzz 3.10.1 - Fuzzy string matching

### 📋 Prerequisites

**System Requirements**
- Python 3.10 or higher
- 8 GB RAM minimum (16 GB recommended)
- 10 GB free disk space (20 GB recommended)
- Internet connection

### 🚀 Quick Start

**1. Clone the repository**

```bash
git clone https://github.com/yourusername/nau-ai-assistant-backend.git
cd nau-ai-assistant-backend
```

**2. Create virtual environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**4. Configure environment**

Copy the example environment file and edit it:

```bash
# Linux/Mac
cp .env.example .env

# Windows
copy .env.example .env
```

Edit `.env` file with your settings. See [Configuration](#configuration) section for details.

**5. Run the server**

```bash
python main.py
```

On first run, the system will download Jina Embeddings v3 model (~1.5 GB), load and index all news, initialize vector database, and start the server. First launch takes 5-15 minutes, subsequent launches 10-30 seconds.

**6. Verify installation**

Open http://localhost:8000 in your browser. You should see:

```json
{
  "status": "ok",
  "message": "NAU AI Assistant Backend працює",
  "version": "2.0.0"
}
```

Check health status: http://localhost:8000/health

View API documentation: http://localhost:8000/docs

### ⚙️ Configuration

The system is configured through environment variables in `.env` file.

**Required Settings**

| Variable | Description | Example |
|----------|-------------|---------|
| `USE_GEMINI` | Use Gemini (true) or LM Studio (false) | `true` |
| `GEMINI_API_KEY` | Your Gemini API key (if USE_GEMINI=true) | `AIza...` |
| `LM_STUDIO_URL` | LM Studio endpoint (if USE_GEMINI=false) | `http://localhost:1234/v1/chat/completions` |

**Optional Settings**

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `localhost` | Server host |
| `PORT` | `8000` | Server port |
| `DEBUG` | `true` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `GENERATION_TEMPERATURE` | `0.3` | LLM temperature (0.0-1.0) |
| `MAX_TOKENS` | `10000` | Max tokens in response |
| `SEARCH_TOP_K` | `3` | Number of search results |

See `.env.example` for complete list of available settings.

**Getting Gemini API Key**

1. Go to https://aistudio.google.com/app/apikey
2. Create new API key
3. Copy and paste into `.env` file

**Using LM Studio Instead**

1. Download from https://lmstudio.ai/
2. Install and load a model (e.g., Llama 3.1 8B)
3. Start local server on port 1234
4. Set `USE_GEMINI=False` in `.env`

### 📡 API Endpoints

**Base URL:** `http://localhost:8000`

#### `GET /`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "message": "NAU AI Assistant Backend працює",
  "version": "2.0.0"
}
```

#### `GET /health`

Detailed health status of all system components.

**Response:**
```json
{
  "status": "ok",
  "message": "Всі компоненти працюють",
  "details": {
    "lm_studio": "available",
    "database_documents": 347,
    "components": ["db", "schedule_manager", "data_loader", "assistant"]
  }
}
```

#### `POST /chat`

Main endpoint for conversational queries.

**Request:**
```json
{
  "user_name": "Ivan",
  "message": "What classes do I have today?",
  "group_name": "Б-171-22-1-ІР",
  "messages": [
    {
      "role": "user",
      "content": "Hello!"
    },
    {
      "role": "assistant",
      "content": "Hello! How can I help you?"
    }
  ]
}
```

**Response:**
```json
{
  "response": "Today you have 3 classes: Math at 9:50, Physics at 11:40, and Programming at 13:30.",
  "status": "success"
}
```

#### `POST /group/validate`

Validate group name format and check schedule availability.

**Request:**
```json
{
  "group_name": "Б-171-22-1-ІР"
}
```

**Response:**
```json
{
  "is_valid": true,
  "extracted_name": "Б-171-22-1-ІР",
  "message": "Група знайдена",
  "suggestions": []
}
```

#### `GET /stats`

System statistics and database information.

**Response:**
```json
{
  "database": {
    "total_documents": 347,
    "categories": {"education": 120, "news": 95, "events": 132}
  },
  "time_context": {
    "time": "14:30",
    "date": "10.11.2025",
    "day": "Понеділок",
    "week": 1
  },
  "system": {
    "components_loaded": ["db", "schedule_manager", "data_loader", "assistant"]
  }
}
```

### 📁 Project Structure

```
nau-ai-assistant-backend/
├── main.py                 # FastAPI server entry point
├── assistant.py            # AI assistant coordinator
├── database.py             # Vector database (ChromaDB + Jina)
├── query_router.py         # Intelligent query routing
├── result_validator.py     # Search result validation
├── schedule.py             # Schedule parsing and management
├── data_loader.py          # News loading and metadata enrichment
├── config.py               # Configuration and constants
├── utils.py                # Utility functions
├── nau_structure.py        # University structure (faculties, departments)
├── models.py               # Pydantic models for API
├── logger.py               # Centralized logging
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment configuration
└── naunews/               # News data directory
    ├── global/            # University-wide news
    ├── ФКНТ/             # Faculty of Computer Science news
    │   ├── ІПЗ/          # Software Engineering department
    │   ├── КІТ/          # Computer Information Technologies
    │   └── КСМ/          # Computer Systems and Networks
    └── ФАЕТ/             # Aeronavigation Faculty news
        ├── ТКС/          # Telecommunication Systems
        └── АСУ/          # Avionics and Control Systems
```

### 🔄 How It Works

**Request Processing Flow**

1. **Client sends query** → FastAPI receives POST request at `/chat`

2. **Request validation** → Pydantic models validate input data

3. **Query routing** → QueryRouter analyzes the query:
   - Determines search scope (global/faculty/department)
   - Identifies intent (info/schedule/news/events)
   - Generates enhancement keywords
   - Decides if database search is needed

4. **Database search** (if needed):
   - Creates query embedding using Jina Embeddings v3
   - Performs vector search in ChromaDB with filters
   - Returns top-K results

5. **Result validation**:
   - LLM validates if results are relevant
   - If not relevant: reformulates query and retries (up to 3 attempts)
   - Returns validated results

6. **Response generation**:
   - Formats search results as context
   - Creates system prompt with university info and schedule
   - Sends to LLM (Gemini or LM Studio)
   - Receives natural language response

7. **Return to client** → Formatted ChatResponse with answer

**Example Query Flow**

```
User: "What are the latest news from Software Engineering department?"
  ↓
QueryRouter: scope=ФКНТ, entity=ІПЗ, intent=news, keywords=["новини", "іпз", "software engineering"]
  ↓
Database: vector search with filters → 15 results
  ↓
Validator: check relevance → PASS (3 relevant results)
  ↓
LLM: generate natural response with context
  ↓
Response: "Here are the latest news from SE department:
          1. Open Day on October 15th...
          2. Students won hackathon...
          3. New computer lab opened..."
```

### 🧪 Testing

**Test with curl**

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "Test User",
    "message": "Hello!",
    "group_name": null,
    "messages": []
  }'
```

### 🐛 Troubleshooting

**"ModuleNotFoundError" when running**

Make sure virtual environment is activated:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

**LM Studio connection failed**

- Verify LM Studio is running
- Check it's listening on http://localhost:1234
- Test: `curl http://localhost:1234/v1/models`

**Gemini API errors**

- Verify API key is correct in `.env`
- Check internet connection
- Ensure you haven't exceeded quota

**Database initialization errors**

- Delete `nau_vector_db/` directory and restart
- Check you have write permissions
- Ensure enough disk space (10+ GB)

**Out of memory errors**

- Increase available RAM
- Reduce `BATCH_SIZE` in config
- Use smaller embedding model
- Reduce number of documents

### 🔧 Development

**Running in development mode**

```bash
uvicorn main:app --reload --host localhost --port 8000
```

Changes to code will automatically reload the server.

---

## Українська версія

### 📖 Про проєкт

NAU AI Assistant Backend — це готова до продакшну AI-система, побудована на FastAPI, яка допомагає студентам і співробітникам Національного авіаційного університету отримувати інформацію через розмовний інтерфейс. Система розуміє запити природною мовою українською, російською та англійською.

Бекенд обробляє складні запити, виконує семантичний пошук по новинах та інформації університету, парсить розклад у реальному часі з порталу НАУ та генерує контекстно-залежні відповіді за допомогою великих мовних моделей.

### ✨ Що вміє система

**Пошук інформації**
- Пошук по новинах та оголошеннях університету
- Інформація про факультети та кафедри
- Деталі про події, конференції та заходи
- Доступ до контактної та адміністративної інформації

**Управління розкладом**
- Парсинг розкладу безпосередньо з порталу НАУ
- Визначення поточних та наступних занять
- Розрахунок номерів навчальних тижнів
- Підтримка чергування тижнів розкладу

**Інтелектуальні діалоги**
- Розуміння контексту з історії розмови
- Маршрутизація запитів до релевантних джерел
- Валідація результатів пошуку на релевантність
- Автоматичне переформулювання запитів для кращих результатів
- Генерація природних, дружніх відповідей

### 🛠 Технологічний стек

**Основний фреймворк**
- FastAPI 0.115.0 - Сучасний async веб-фреймворк
- Uvicorn 0.30.6 - ASGI сервер
- Pydantic 2.10.0 - Валідація даних

**AI/ML компоненти**
- Google Gemini 2.0 Flash / LM Studio - Генерація відповідей
- ChromaDB 0.5.23 - Векторна база даних
- Jina Embeddings v3 - Багатомовні текстові ембеддінги
- Sentence-Transformers 3.3.1 - Фреймворк для ембеддінгів

**Обробка даних**
- BeautifulSoup4 4.12.3 - Парсинг HTML
- Pandas 2.2.3 - Маніпуляція даними
- RapidFuzz 3.10.1 - Нечітке порівняння рядків

### 📋 Вимоги

**Системні вимоги**
- Python 3.10 або вище
- Мінімум 8 ГБ ОЗП (рекомендовано 16 ГБ)
- 10 ГБ вільного місця на диску (рекомендовано 20 ГБ)
- Інтернет-з'єднання

### 🚀 Швидкий старт

**1. Клонуйте репозиторій**

```bash
git clone https://github.com/yourusername/nau-ai-assistant-backend.git
cd nau-ai-assistant-backend
```

**2. Створіть віртуальне середовище**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

**3. Встановіть залежності**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**4. Налаштуйте середовище**

Скопіюйте приклад файлу середовища та відредагуйте його:

```bash
# Linux/Mac
cp .env.example .env

# Windows
copy .env.example .env
```

Відредагуйте файл `.env` з вашими налаштуваннями. Дивіться розділ [Конфігурація](#конфігурація-1) для деталей.

**5. Запустіть сервер**

```bash
python main.py
```

При першому запуску система завантажить модель Jina Embeddings v3 (~1.5 ГБ), завантажить і проіндексує всі новини, ініціалізує векторну базу даних та запустить сервер. Перший запуск займає 5-15 хвилин, наступні запуски 10-30 секунд.

**6. Перевірте встановлення**

Відкрийте http://localhost:8000 у браузері. Ви повинні побачити:

```json
{
  "status": "ok",
  "message": "NAU AI Assistant Backend працює",
  "version": "2.0.0"
}
```

Перевірте статус здоров'я: http://localhost:8000/health

Перегляньте документацію API: http://localhost:8000/docs

### ⚙️ Конфігурація

Система налаштовується через змінні середовища у файлі `.env`.

**Обов'язкові налаштування**

| Змінна | Опис | Приклад |
|--------|------|---------|
| `USE_GEMINI` | Використовувати Gemini (true) або LM Studio (false) | `true` |
| `GEMINI_API_KEY` | Ваш API ключ Gemini (якщо USE_GEMINI=true) | `AIza...` |
| `LM_STUDIO_URL` | Ендпоінт LM Studio (якщо USE_GEMINI=false) | `http://localhost:1234/v1/chat/completions` |

**Опціональні налаштування**

| Змінна | За замовчуванням | Опис |
|--------|------------------|------|
| `HOST` | `localhost` | Хост сервера |
| `PORT` | `8000` | Порт сервера |
| `DEBUG` | `true` | Режим відладки |
| `LOG_LEVEL` | `INFO` | Рівень логування (DEBUG/INFO/WARNING/ERROR) |
| `GENERATION_TEMPERATURE` | `0.3` | Температура LLM (0.0-1.0) |
| `MAX_TOKENS` | `10000` | Максимум токенів у відповіді |
| `SEARCH_TOP_K` | `3` | Кількість результатів пошуку |

Дивіться `.env.example` для повного списку доступних налаштувань.

**Отримання API ключа Gemini**

1. Перейдіть на https://aistudio.google.com/app/apikey
2. Створіть новий API ключ
3. Скопіюйте та вставте у файл `.env`

**Використання LM Studio замість Gemini**

1. Завантажте з https://lmstudio.ai/
2. Встановіть та завантажте модель (наприклад, Llama 3.1 8B)
3. Запустіть локальний сервер на порті 1234
4. Встановіть `USE_GEMINI=False` у `.env`

### 📡 API ендпоінти

**Базова URL:** `http://localhost:8000`

#### `GET /`

Ендпоінт перевірки здоров'я.

**Відповідь:**
```json
{
  "status": "ok",
  "message": "NAU AI Assistant Backend працює",
  "version": "2.0.0"
}
```

#### `GET /health`

Детальний статус здоров'я всіх компонентів системи.

**Відповідь:**
```json
{
  "status": "ok",
  "message": "Всі компоненти працюють",
  "details": {
    "lm_studio": "available",
    "database_documents": 347,
    "components": ["db", "schedule_manager", "data_loader", "assistant"]
  }
}
```

#### `POST /chat`

Основний ендпоінт для розмовних запитів.

**Запит:**
```json
{
  "user_name": "Іван",
  "message": "Які пари в мене сьогодні?",
  "group_name": "Б-171-22-1-ІР",
  "messages": [
    {
      "role": "user",
      "content": "Привіт!"
    },
    {
      "role": "assistant",
      "content": "Привіт! Чим можу допомогти?"
    }
  ]
}
```

**Відповідь:**
```json
{
  "response": "Сьогодні у вас 3 пари: Математика о 9:50, Фізика о 11:40 та Програмування о 13:30.",
  "status": "success"
}
```

#### `POST /group/validate`

Валідація формату назви групи та перевірка доступності розкладу.

**Запит:**
```json
{
  "group_name": "Б-171-22-1-ІР"
}
```

**Відповідь:**
```json
{
  "is_valid": true,
  "extracted_name": "Б-171-22-1-ІР",
  "message": "Група знайдена",
  "suggestions": []
}
```

#### `GET /stats`

Статистика системи та інформація про базу даних.

**Відповідь:**
```json
{
  "database": {
    "total_documents": 347,
    "categories": {"education": 120, "news": 95, "events": 132}
  },
  "time_context": {
    "time": "14:30",
    "date": "10.11.2025",
    "day": "Понеділок",
    "week": 1
  },
  "system": {
    "components_loaded": ["db", "schedule_manager", "data_loader", "assistant"]
  }
}
```

### 📁 Структура проєкту

```
nau-ai-assistant-backend/
├── main.py                 # Точка входу FastAPI сервера
├── assistant.py            # Координатор AI асистента
├── database.py             # Векторна база даних (ChromaDB + Jina)
├── query_router.py         # Інтелектуальна маршрутизація запитів
├── result_validator.py     # Валідація результатів пошуку
├── schedule.py             # Парсинг та управління розкладом
├── data_loader.py          # Завантаження новин та збагачення метаданими
├── config.py               # Конфігурація та константи
├── utils.py                # Допоміжні функції
├── nau_structure.py        # Структура університету (факультети, кафедри)
├── models.py               # Pydantic моделі для API
├── logger.py               # Централізоване логування
├── requirements.txt        # Python залежності
├── .env.example           # Приклад конфігурації середовища
└── naunews/               # Директорія з новинами
    ├── global/            # Загальноуніверситетські новини
    ├── ФКНТ/             # Новини факультету комп'ютерних наук
    │   ├── ІПЗ/          # Кафедра інженерії програмного забезпечення
    │   ├── КІТ/          # Комп'ютерні інформаційні технології
    │   └── КСМ/          # Комп'ютерні системи та мережі
    └── ФАЕТ/             # Факультет аеронавігації
        ├── ТКС/          # Телекомунікаційні системи
        └── АСУ/          # Авіоніка та системи управління
```

### 🔄 Як це працює

**Потік обробки запиту**

1. **Клієнт надсилає запит** → FastAPI отримує POST запит на `/chat`

2. **Валідація запиту** → Pydantic моделі валідують вхідні дані

3. **Маршрутизація запиту** → QueryRouter аналізує запит:
   - Визначає область пошуку (глобальна/факультет/кафедра)
   - Ідентифікує намір (інформація/розклад/новини/події)
   - Генерує ключові слова для покращення
   - Вирішує, чи потрібен пошук у базі даних

4. **Пошук у базі даних** (якщо потрібно):
   - Створює ембеддінг запиту за допомогою Jina Embeddings v3
   - Виконує векторний пошук у ChromaDB з фільтрами
   - Повертає топ-K результатів

5. **Валідація результатів**:
   - LLM валідує, чи релевантні результати
   - Якщо нерелевантні: переформульовує запит і повторює (до 3 спроб)
   - Повертає валідовані результати

6. **Генерація відповіді**:
   - Форматує результати пошуку як контекст
   - Створює системний промпт з інформацією про університет та розкладом
   - Надсилає до LLM (Gemini або LM Studio)
   - Отримує відповідь природною мовою

7. **Повернення клієнту** → Форматована ChatResponse з відповіддю

**Приклад потоку запиту**

```
Користувач: "Які останні новини з кафедри ІПЗ?"
  ↓
QueryRouter: scope=ФКНТ, entity=ІПЗ, intent=news, keywords=["новини", "іпз", "software engineering"]
  ↓
База даних: векторний пошук з фільтрами → 15 результатів
  ↓
Валідатор: перевірка релевантності → PASSED (3 релевантні результати)
  ↓
LLM: генерація природної відповіді з контекстом
  ↓
Відповідь: "Ось останні новини з кафедри ІПЗ:
          1. День відкритих дверей 15 жовтня...
          2. Студенти виграли хакатон...
          3. Відкрито нову комп'ютерну лабораторію..."
```

### 🧪 Тестування

**Тест за допомогою curl**

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "Тестовий користувач",
    "message": "Привіт!",
    "group_name": null,
    "messages": []
  }'
```

### 🐛 Вирішення проблем

**"ModuleNotFoundError" при запуску**

Переконайтеся, що віртуальне середовище активоване:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

**Помилка підключення до LM Studio**

- Переконайтеся, що LM Studio запущено
- Перевірте, що він слухає на http://localhost:1234
- Тест: `curl http://localhost:1234/v1/models`

**Помилки Gemini API**

- Переконайтеся, що API ключ правильний у `.env`
- Перевірте інтернет-з'єднання
- Переконайтеся, що не перевищено квоту

**Помилки ініціалізації бази даних**

- Видаліть директорію `nau_vector_db/` та перезапустіть
- Перевірте, що у вас є права на запис
- Переконайтеся, що достатньо місця на диску (10+ ГБ)

**Помилки нестачі пам'яті**

- Збільште доступну ОЗП
- Зменшіть `BATCH_SIZE` в конфігурації
- Використовуйте меншу модель ембеддінгів
- Зменшіть кількість документів

### 🔧 Розробка

**Запуск у режимі розробки**

```bash
uvicorn main:app --reload --host localhost --port 8000
```

Зміни в коді автоматично перезавантажать сервер.