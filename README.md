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
- Python 3.11 or higher
- 16 GB RAM minimum
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

Create `.env` file in the project root. **Minimum required:**

```bash
USE_GEMINI=true
GEMINI_API_KEY=your_gemini_api_key_here
```

**Full configuration template:**

```bash
# ===========================================
# NAU AI Assistant Backend - Змінні оточення
# ===========================================

# ===========================================
# ОСНОВНІ НАЛАШТУВАННЯ СЕРВЕРА
# ===========================================
HOST=localhost
PORT=8000
DEBUG=true
ENVIRONMENT=development

# ===========================================
# ШЛЯХИ ДО ДАНИХ
# ===========================================
VECTOR_DB_PATH=./nau_vector_db
NEWS_DATA_PATH=./naunews

# ===========================================
# AI НАЛАШТУВАННЯ (Gemini / LM Studio)
# ===========================================
# Оберіть один з варіантів:
USE_GEMINI=true

# Gemini API (рекомендується)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# LM Studio (локальна модель)
LM_STUDIO_URL=http://localhost:1234/v1/chat/completions
LM_STUDIO_TIMEOUT=300
DEFAULT_MODEL=gemma-3-4b-it

# ===========================================
# НАЛАШТУВАННЯ ГЕНЕРАЦІЇ
# ===========================================
GENERATION_TEMPERATURE=0.3
MAX_TOKENS=1000
MAX_HISTORY_MESSAGES=6
MAX_CONTEXT_TOKENS=6000

# ===========================================
# НАЛАШТУВАННЯ ПОШУКУ В БАЗІ ДАНИХ
# ===========================================
SEARCH_TOP_K=3
SEARCH_SIMILARITY_THRESHOLD=0.3
ENABLE_QUERY_EXPANSION=true
RECENT_NEWS_DAYS=30
BATCH_SIZE=100

# ===========================================
# НАЛАШТУВАННЯ РОЗКЛАДУ
# ===========================================
SCHEDULE_CACHE_ENABLED=true
SCHEDULE_REQUEST_TIMEOUT=10
NAU_PORTAL_BASE_URL=https://portal.nau.edu.ua
SEMESTER_START_DATE=2025-09-01

# ===========================================
# НАЛАШТУВАННЯ ЛОГУВАННЯ
# ===========================================
LOG_LEVEL=INFO
LOG_SYSTEM_PROMPTS=false

# ===========================================
# БЕЗПЕКА ТА ОБМЕЖЕННЯ
# ===========================================
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

**Important:** Replace `your_gemini_api_key_here` with your actual Gemini API key.

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

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_GEMINI` | Use Gemini API (true) or LM Studio (false) | `true` |
| `GEMINI_API_KEY` | Your Gemini API key | *required if USE_GEMINI=true* |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.0-flash` |

**Server Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `localhost` |
| `PORT` | Server port | `8000` |
| `DEBUG` | Debug mode | `true` |
| `ENVIRONMENT` | Environment (development/production) | `development` |

**AI Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| `LM_STUDIO_URL` | LM Studio endpoint (if not using Gemini) | `http://localhost:1234/v1/chat/completions` |
| `LM_STUDIO_TIMEOUT` | LM Studio request timeout (seconds) | `300` |
| `DEFAULT_MODEL` | Default LM Studio model name | `gemma-3-4b-it` |
| `GENERATION_TEMPERATURE` | Response temperature (0.0-1.0) | `0.3` |
| `MAX_TOKENS` | Max tokens in response | `1000` |
| `MAX_HISTORY_MESSAGES` | Max messages in conversation history | `6` |
| `MAX_CONTEXT_TOKENS` | Max tokens for context management | `6000` |

**Data Paths**

| Variable | Description | Default |
|----------|-------------|---------|
| `VECTOR_DB_PATH` | Vector database directory | `./nau_vector_db` |
| `NEWS_DATA_PATH` | News data directory | `./naunews` |

**Search Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| `SEARCH_TOP_K` | Number of search results | `3` |
| `SEARCH_SIMILARITY_THRESHOLD` | Similarity threshold for filtering | `0.3` |
| `ENABLE_QUERY_EXPANSION` | Enable query expansion | `true` |
| `RECENT_NEWS_DAYS` | Days for recent news search | `30` |
| `BATCH_SIZE` | Batch size for document processing | `100` |

**Schedule Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| `SCHEDULE_CACHE_ENABLED` | Enable schedule caching | `true` |
| `SCHEDULE_REQUEST_TIMEOUT` | Portal request timeout (seconds) | `10` |
| `NAU_PORTAL_BASE_URL` | NAU portal base URL | `https://portal.nau.edu.ua` |
| `SEMESTER_START_DATE` | Semester start date for week calculation | `2025-09-01` |

**Logging Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `LOG_SYSTEM_PROMPTS` | Show system prompts in logs | `false` |

**Security Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| `RATE_LIMIT_REQUESTS` | Max requests per period | `100` |
| `RATE_LIMIT_PERIOD` | Rate limit period (seconds) | `60` |

**Getting Gemini API Key**

1. Go to https://aistudio.google.com/app/apikey
2. Create new API key
3. Copy and paste into `.env` file

**Using LM Studio Instead**

1. Download from https://lmstudio.ai/
2. Install and load a model (e.g., Llama 3.1 8B)
3. Start local server on port 1234
4. Set `USE_GEMINI=false` in `.env`

**Production Configuration**

For production environment, update these settings:

```bash
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=WARNING
LOG_SYSTEM_PROMPTS=false
HOST=0.0.0.0
```

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
├── .env                    # Environment configuration
└── naunews/                # News data directory
    ├── global/             # University-wide news
    ├── ФКНТ/               # Faculty of Computer Science news
    │   ├── ІПЗ/            # Software Engineering department
    │   ├── КІТ/            # Computer Information Technologies
    │   └── КСМ/            # Computer Systems and Networks
    └── ФАЕТ/               # Aeronavigation Faculty news
        ├── ТКС/            # Telecommunication Systems
        └── АСУ/            # Avionics and Control Systems
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

Створіть файл `.env` у кореневій директорії. **Мінімум:**

```bash
USE_GEMINI=true
GEMINI_API_KEY=ваш_ключ_тут
```

**Повний шаблон:**

```bash
# ===========================================
# NAU AI Assistant Backend - Змінні оточення
# ===========================================

# ===========================================
# ОСНОВНІ НАЛАШТУВАННЯ СЕРВЕРА
# ===========================================
HOST=localhost
PORT=8000
DEBUG=true
ENVIRONMENT=development

# ===========================================
# ШЛЯХИ ДО ДАНИХ
# ===========================================
VECTOR_DB_PATH=./nau_vector_db
NEWS_DATA_PATH=./naunews

# ===========================================
# AI НАЛАШТУВАННЯ (Gemini / LM Studio)
# ===========================================
USE_GEMINI=true

# Gemini API (рекомендується)
GEMINI_API_KEY=ваш_ключ_тут
GEMINI_MODEL=gemini-2.0-flash

# LM Studio (локальна модель)
LM_STUDIO_URL=http://localhost:1234/v1/chat/completions
LM_STUDIO_TIMEOUT=300
DEFAULT_MODEL=gemma-3-4b-it

# ===========================================
# НАЛАШТУВАННЯ ГЕНЕРАЦІЇ
# ===========================================
GENERATION_TEMPERATURE=0.3
MAX_TOKENS=1000
MAX_HISTORY_MESSAGES=6
MAX_CONTEXT_TOKENS=6000

# ===========================================
# НАЛАШТУВАННЯ ПОШУКУ В БАЗІ ДАНИХ
# ===========================================
SEARCH_TOP_K=3
SEARCH_SIMILARITY_THRESHOLD=0.3
ENABLE_QUERY_EXPANSION=true
RECENT_NEWS_DAYS=30
BATCH_SIZE=100

# ===========================================
# НАЛАШТУВАННЯ РОЗКЛАДУ
# ===========================================
SCHEDULE_CACHE_ENABLED=true
SCHEDULE_REQUEST_TIMEOUT=10
NAU_PORTAL_BASE_URL=https://portal.nau.edu.ua
SEMESTER_START_DATE=2025-09-01

# ===========================================
# НАЛАШТУВАННЯ ЛОГУВАННЯ
# ===========================================
LOG_LEVEL=INFO
LOG_SYSTEM_PROMPTS=false

# ===========================================
# БЕЗПЕКА ТА ОБМЕЖЕННЯ
# ===========================================
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

**5. Запустіть сервер**

```bash
python main.py
```

Перший запуск займає 5-15 хвилин, наступні 10-30 секунд.

**6. Перевірте**

- http://localhost:8000 - Статус
- http://localhost:8000/health - Детальна перевірка
- http://localhost:8000/docs - Документація API

### ⚙️ Конфігурація

Повний опис налаштувань див. у [англійській версії](#configuration) вище.

**Основні налаштування:**

| Змінна | Опис | За замовчуванням |
|--------|------|------------------|
| `USE_GEMINI` | Використовувати Gemini | `true` |
| `GEMINI_API_KEY` | API ключ Gemini | обов'язково |
| `GEMINI_MODEL` | Модель Gemini | `gemini-2.0-flash` |

**Отримання ключа Gemini:**

1. Перейдіть на https://aistudio.google.com/app/apikey
2. Створіть новий API ключ
3. Скопіюйте у файл `.env`

**Для production:**

```bash
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=WARNING
LOG_SYSTEM_PROMPTS=false
HOST=0.0.0.0
```

### 📡 API ендпоінти

```
GET  /               - Перевірка здоров'я
GET  /health         - Детальний статус
POST /chat           - Основний ендпоінт діалогу
POST /group/validate - Валідація групи
GET  /stats          - Статистика системи
```

Повна документація: http://localhost:8000/docs

### 🐛 Вирішення проблем

**ModuleNotFoundError**
- Активуйте venv: `venv\Scripts\activate` (Windows) або `source venv/bin/activate` (Linux/Mac)

**Помилка підключення до LM Studio**
- Перевірте що LM Studio запущений на http://localhost:1234

**Помилки Gemini API**
- Перевірте API ключ у `.env`
- Перевірте інтернет-з'єднання

**Помилки бази даних**
- Видаліть директорію `nau_vector_db/` і перезапустіть
- Перевірте наявність 10+ ГБ вільного місця

**Помилки пам'яті**
- Зменшіть `BATCH_SIZE`
- Збільште доступну ОЗП

### 🔧 Розробка

```bash
uvicorn main:app --reload --host localhost --port 8000
```

Зміни в коді автоматично перезавантажують сервер.
