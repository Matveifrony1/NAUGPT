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

\`\`\`bash
git clone https://github.com/yourusername/nau-ai-assistant-backend.git
cd nau-ai-assistant-backend
\`\`\`

**2. Create virtual environment**

\`\`\`bash
# Windows
python -m venv venv
venv\\Scripts\\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
\`\`\`

**3. Install dependencies**

\`\`\`bash
pip install --upgrade pip
pip install -r requirements.txt
\`\`\`

**4. Configure environment**

Create \`.env\` file in the project root. **Minimum required:**

\`\`\`bash
USE_GEMINI=true
GEMINI_API_KEY=your_gemini_api_key_here
\`\`\`

**Full configuration template:**

\`\`\`bash
# Основні налаштування
HOST=localhost
PORT=8000
DEBUG=true
ENVIRONMENT=development

# Шляхи до даних
VECTOR_DB_PATH=./nau_vector_db
NEWS_DATA_PATH=./naunews

# AI налаштування
USE_GEMINI=true
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# LM Studio (альтернатива)
LM_STUDIO_URL=http://localhost:1234/v1/chat/completions
LM_STUDIO_TIMEOUT=300
DEFAULT_MODEL=gemma-3-4b-it

# Генерація
GENERATION_TEMPERATURE=0.3
MAX_TOKENS=1000
MAX_HISTORY_MESSAGES=6
MAX_CONTEXT_TOKENS=6000

# Пошук
SEARCH_TOP_K=3
SEARCH_SIMILARITY_THRESHOLD=0.3
ENABLE_QUERY_EXPANSION=true
RECENT_NEWS_DAYS=30
BATCH_SIZE=100

# Розклад
SCHEDULE_CACHE_ENABLED=true
SCHEDULE_REQUEST_TIMEOUT=10
NAU_PORTAL_BASE_URL=https://portal.nau.edu.ua
SEMESTER_START_DATE=2025-09-01

# Логування
LOG_LEVEL=INFO
LOG_SYSTEM_PROMPTS=false

# Безпека
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
\`\`\`

**5. Run the server**

\`\`\`bash
python main.py
\`\`\`

First launch takes 5-15 minutes (downloads model, indexes news). Subsequent launches: 10-30 seconds.

**6. Verify**

- http://localhost:8000 - Should show status OK
- http://localhost:8000/health - Detailed health check
- http://localhost:8000/docs - API documentation

### ⚙️ Configuration Reference

**Essential Settings**

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| \`USE_GEMINI\` | Yes | Use Gemini (true) or LM Studio (false) | \`true\` |
| \`GEMINI_API_KEY\` | If USE_GEMINI=true | Gemini API key | - |
| \`GEMINI_MODEL\` | No | Gemini model | \`gemini-2.0-flash\` |

**Server Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| \`HOST\` | Server host | \`localhost\` |
| \`PORT\` | Server port | \`8000\` |
| \`DEBUG\` | Debug mode | \`true\` |
| \`ENVIRONMENT\` | Environment | \`development\` |

**AI Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| \`LM_STUDIO_URL\` | LM Studio endpoint | \`http://localhost:1234/v1/chat/completions\` |
| \`LM_STUDIO_TIMEOUT\` | Request timeout (sec) | \`300\` |
| \`DEFAULT_MODEL\` | LM Studio model name | \`gemma-3-4b-it\` |
| \`GENERATION_TEMPERATURE\` | Response creativity (0.0-1.0) | \`0.3\` |
| \`MAX_TOKENS\` | Max response length | \`1000\` |
| \`MAX_HISTORY_MESSAGES\` | History size | \`6\` |
| \`MAX_CONTEXT_TOKENS\` | Context window | \`6000\` |

**Data Paths**

| Variable | Description | Default |
|----------|-------------|---------|
| \`VECTOR_DB_PATH\` | Vector DB directory | \`./nau_vector_db\` |
| \`NEWS_DATA_PATH\` | News directory | \`./naunews\` |

**Search Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| \`SEARCH_TOP_K\` | Results to return | \`3\` |
| \`SEARCH_SIMILARITY_THRESHOLD\` | Relevance threshold | \`0.3\` |
| \`ENABLE_QUERY_EXPANSION\` | Expand queries | \`true\` |
| \`RECENT_NEWS_DAYS\` | Recent news range | \`30\` |
| \`BATCH_SIZE\` | Processing batch size | \`100\` |

**Schedule Settings**

| Variable | Description | Default |
|----------|-------------|---------|
| \`SCHEDULE_CACHE_ENABLED\` | Cache schedules | \`true\` |
| \`SCHEDULE_REQUEST_TIMEOUT\` | Portal timeout (sec) | \`10\` |
| \`NAU_PORTAL_BASE_URL\` | NAU portal URL | \`https://portal.nau.edu.ua\` |
| \`SEMESTER_START_DATE\` | Semester start | \`2025-09-01\` |

**Logging**

| Variable | Description | Default |
|----------|-------------|---------|
| \`LOG_LEVEL\` | Logging level | \`INFO\` |
| \`LOG_SYSTEM_PROMPTS\` | Show prompts in logs | \`false\` |

**Security**

| Variable | Description | Default |
|----------|-------------|---------|
| \`RATE_LIMIT_REQUESTS\` | Max requests/period | \`100\` |
| \`RATE_LIMIT_PERIOD\` | Period (seconds) | \`60\` |

**Getting Gemini API Key**

1. Visit https://aistudio.google.com/app/apikey
2. Create API key
3. Add to \`.env\`

**Using LM Studio**

1. Download from https://lmstudio.ai/
2. Load a model (e.g., Llama 3.1 8B)
3. Start server on port 1234
4. Set \`USE_GEMINI=false\`

**Production Setup**

\`\`\`bash
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=WARNING
LOG_SYSTEM_PROMPTS=false
HOST=0.0.0.0
\`\`\`

### 📡 API Endpoints

\`\`\`
GET  /         - Health check
GET  /health   - Detailed status
POST /chat     - Main conversation endpoint
POST /group/validate - Validate group name
GET  /stats    - System statistics
\`\`\`

See http://localhost:8000/docs for full API documentation.

### 🐛 Troubleshooting

**ModuleNotFoundError**
- Activate venv: \`venv\\Scripts\\activate\` (Windows) or \`source venv/bin/activate\` (Linux/Mac)

**LM Studio connection failed**
- Verify LM Studio is running on http://localhost:1234

**Gemini API errors**
- Check API key in \`.env\`
- Verify internet connection

**Database errors**
- Delete \`nau_vector_db/\` and restart
- Check disk space (10+ GB needed)

**Out of memory**
- Reduce \`BATCH_SIZE\`
- Increase RAM

---

## Українська версія

### 📖 Про проєкт

NAU AI Assistant Backend — готова до продакшну AI-система на FastAPI, яка допомагає студентам і співробітникам НАУ отримувати інформацію через розмовний інтерфейс. Розуміє запити українською, російською та англійською.

### 🚀 Швидкий старт

**1-3. Клонування та встановлення**

\`\`\`bash
git clone https://github.com/yourusername/nau-ai-assistant-backend.git
cd nau-ai-assistant-backend
python -m venv venv
venv\\Scripts\\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
\`\`\`

**4. Налаштування .env**

Мінімум:
\`\`\`bash
USE_GEMINI=true
GEMINI_API_KEY=ваш_ключ_тут
\`\`\`

Повний шаблон:
\`\`\`bash
# Основні налаштування
HOST=localhost
PORT=8000
DEBUG=true
ENVIRONMENT=development

# Шляхи
VECTOR_DB_PATH=./nau_vector_db
NEWS_DATA_PATH=./naunews

# AI
USE_GEMINI=true
GEMINI_API_KEY=ваш_ключ_тут
GEMINI_MODEL=gemini-2.0-flash

# LM Studio (альтернатива)
LM_STUDIO_URL=http://localhost:1234/v1/chat/completions
LM_STUDIO_TIMEOUT=300
DEFAULT_MODEL=gemma-3-4b-it

# Генерація
GENERATION_TEMPERATURE=0.3
MAX_TOKENS=1000
MAX_HISTORY_MESSAGES=6
MAX_CONTEXT_TOKENS=6000

# Пошук
SEARCH_TOP_K=3
SEARCH_SIMILARITY_THRESHOLD=0.3
ENABLE_QUERY_EXPANSION=true
RECENT_NEWS_DAYS=30
BATCH_SIZE=100

# Розклад
SCHEDULE_CACHE_ENABLED=true
SCHEDULE_REQUEST_TIMEOUT=10
NAU_PORTAL_BASE_URL=https://portal.nau.edu.ua
SEMESTER_START_DATE=2025-09-01

# Логування
LOG_LEVEL=INFO
LOG_SYSTEM_PROMPTS=false

# Безпека
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
\`\`\`

**5. Запуск**

\`\`\`bash
python main.py
\`\`\`

Перший запуск: 5-15 хвилин. Наступні: 10-30 секунд.

**6. Перевірка**

- http://localhost:8000 - Статус
- http://localhost:8000/docs - Документація API

### ⚙️ Конфігурація

**Обов'язкові налаштування**

| Змінна | Опис | За замовчуванням |
|--------|------|------------------|
| \`USE_GEMINI\` | Використовувати Gemini | \`true\` |
| \`GEMINI_API_KEY\` | API ключ Gemini | обов'язково |
| \`GEMINI_MODEL\` | Модель Gemini | \`gemini-2.0-flash\` |

Решту налаштувань див. вище в англійській версії.

**Отримання ключа Gemini**

1. https://aistudio.google.com/app/apikey
2. Створити ключ
3. Додати в \`.env\`

**Production**

\`\`\`bash
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=WARNING
HOST=0.0.0.0
\`\`\`

### 🐛 Вирішення проблем

**ModuleNotFoundError** - Активуйте venv
**LM Studio помилка** - Перевірте що запущений
**Gemini помилка** - Перевірте ключ
**База даних** - Видаліть nau_vector_db/ і перезапустіть
**Пам'ять** - Зменшіть BATCH_SIZE
