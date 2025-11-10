# Отключаем телеметрию ChromaDB
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import uuid
import re
from datetime import datetime
from rapidfuzz import fuzz
from logger import get_logger

logger = get_logger(__name__)

class VectorDatabase:
    """Векторна база даних з гібридним пошуком (embedding + keyword)"""
    
    def __init__(self, db_path: str = "./nau_vector_db"):
        self.db_path = db_path
        self.collection_name = "nau_knowledge_base"
        self.embedding_model = None
        self.client = None
        self.collection = None
        self.similarity_threshold = 1.0
        
        self._initialize()
    
    def _initialize(self):
        """Ініціалізація з Jina Embeddings v3"""
        logger.debug("🚀 Ініціалізація векторної бази даних...")
        
        try:
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "description": "NAU News Knowledge Base",
                    "hnsw:space": "cosine"
                }
            )
            logger.info(f"✅ База даних ініціалізована: {self.db_path}")
        except Exception as e:
            logger.critical(f"❌ Помилка ініціалізації БД: {e}")
            raise
        
        try:
            logger.debug("📦 Завантаження Jina Embeddings v3...")
            
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.debug(f"🔧 Використовується пристрій: {device}")
            if torch.cuda.is_available():
                logger.debug(f"   GPU: {torch.cuda.get_device_name(0)}")
                logger.debug(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            
            self.embedding_model = SentenceTransformer(
                'jinaai/jina-embeddings-v3',
                trust_remote_code=True,
                device=device  # ✅ ТУТ
            )
            logger.info(f"✅ Завантажено на {device}: jinaai/jina-embeddings-v3")
        except Exception as e:
            logger.critical(f"❌ Критична помилка завантаження моделі: {e}")
            raise
    
    def search_improved(self, query: str, top_k: int = 5, 
                       category_filter: Optional[str] = None) -> List[Dict]:
        """ГІБРИДНИЙ пошук: embedding + keyword search"""
        
        logger.debug(f"🔍 ГІБРИДНИЙ ПОШУК: query='{query}', top_k={top_k}")
        
        if not self.embedding_model or not self.collection:
            return []
        
        # 1. Embedding поиск
        embedding_results = self._embedding_search(query, top_k * 10, category_filter)
        logger.debug(f"🔍 EMBEDDING: {len(embedding_results)} результатів")
        
        # 2. Keyword поиск
        keyword_results = self._keyword_search(query, top_k * 5, category_filter)
        logger.debug(f"🔍 KEYWORD: {len(keyword_results)} результатів")
        
        # 3. Объединяем результаты
        combined_results = self._combine_results(embedding_results, keyword_results, top_k)
        logger.debug(f"🔍 КОМБІНОВАНИЙ: {len(combined_results)} остаточних результатів")
        
        return combined_results

    def search_with_route(self, query: str, route_decision, top_k: int = 5) -> List[Dict]:
        """
        Пошук БЕЗ дублювання keywords
        """
        logger.debug(f"🔍 SEARCH WITH ROUTE: scope={route_decision.search_scope}, entity={route_decision.target_entity}, top_k={top_k}")
        
        # 1. Будуємо фільтри
        where_filter = self._build_route_filters(route_decision)
        
        # 2. Додаємо keywords ТІЛЬКИ якщо їх немає в query
        enhanced_query = query  # Починаємо з оригінального query (який вже має keywords з assistant.py)
        
        # Перевіряємо які keywords ще не в запиті
        if route_decision.enhancement_keywords:
            query_words_lower = set(query.lower().split())
            new_keywords = [
                kw for kw in route_decision.enhancement_keywords 
                if kw.lower() not in query_words_lower
            ]
            
            # Додаємо тільки НОВІ keywords
            if new_keywords:
                enhanced_query = query + " " + " ".join(new_keywords)
                logger.debug(f"🔍 ДОДАНІ НОВІ KEYWORDS: {new_keywords}")
            else:
                logger.debug(f"🔍 ВСІ KEYWORDS ВЖЕ Є В ЗАПИТІ")
        
        logger.debug(f"🔍 ENHANCED QUERY: '{enhanced_query}'")
        
        # 3. Виконуємо пошук (збільшуємо множник для top_k=6)
        results = self._route_aware_search(enhanced_query, where_filter, top_k * 5)
        
        # 4. Переранжування з бонусами
        ranked = self._rerank_with_route_bonuses(results, route_decision)
        
        # 5. Повертаємо топ-K
        final_results = ranked[:top_k]
        
        logger.debug(f"🔍 ПОВЕРНУТО: {len(final_results)} результатів")
        for i, r in enumerate(final_results, 1):
            title = r['metadata'].get('title', 'No title')
            score = r.get('relevance_score', 0)
            logger.debug(f"  #{i}: score={score:.1f}, title='{title}...'")
        
        return final_results


    def _build_route_filters(self, route_decision) -> Dict:
        """Створення ChromaDB фільтрів з RouteDecision"""
        conditions = [{"source": {"$eq": "news"}}]
        
        # Фільтр по факультету
        if route_decision.search_scope != "global":
            conditions.append({"faculty": {"$eq": route_decision.search_scope}})
        
        # Фільтр по кафедрі
        if route_decision.target_entity:
            conditions.append({"department": {"$eq": route_decision.target_entity}})
        
        # Фільтр по intent (категорія)
        intent_to_category = {
            "schedule": "schedule",
            "news": None,  # Не фільтруємо
            "events": "conferences",
            "contacts": "contacts",
            "info": None
        }
        
        category = intent_to_category.get(route_decision.search_intent)
        if category:
            conditions.append({"category": {"$eq": category}})
        
        return {"$and": conditions} if len(conditions) > 1 else conditions[0]


    def _route_aware_search(self, query: str, where_filter: Dict, max_results: int) -> List[Dict]:
        """Пошук з route фільтрами + Jina"""
        try:
            prefixed_query = f"query: {query}"
            
            query_embedding = self.embedding_model.encode(
                [prefixed_query],
                task='retrieval.query',
                prompt_name='retrieval.query'
            )[0].tolist()
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                where=where_filter
            )
            
            formatted = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    formatted.append({
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 1.0,
                        "relevance_score": max(0, 1.0 - (results["distances"][0][i] / 4)),
                        "id": results["ids"][0][i] if results["ids"] else None,
                        "search_type": "routed"
                    })
            
            return formatted
        except Exception as e:
            logger.error(f"❌ Route search error: {e}")
            return []


    def _rerank_with_route_bonuses(self, results: List[Dict], route_decision) -> List[Dict]:
        """
        Бонуси за правильні документи
        """
        for result in results:
            meta = result["metadata"]
            base_score = result["relevance_score"]
            bonus = 0
            
            if route_decision.search_scope != "global":
                if meta.get("faculty") == route_decision.search_scope:
                    bonus += 0.1
                
                if meta.get("department") == route_decision.target_entity:
                    bonus += 0.1
            
            result["relevance_score"] = base_score + bonus
            result["route_bonus"] = bonus
        
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Логування топ-3
        for i, r in enumerate(results[:3]):
            logger.debug(f"  #{i+1}: score={r['relevance_score']:.3f} (bonus={r.get('route_bonus', 0):.3f})")
        
        return results


    def _embedding_search(self, query: str, max_results: int, category_filter: Optional[str]) -> List[Dict]:
        """Пошук через Jina embedding"""
        try:
            expanded_query = self._expand_query_improved(query)
            logger.debug(f"🔍 РОЗШИРЕНИЙ ЗАПРОС: '{expanded_query}'")
            
            # Jina prefix для запиту
            prefixed_query = f"query: {expanded_query}"
            
            query_embedding = self.embedding_model.encode(
                [prefixed_query],
                task='retrieval.query',
                prompt_name='retrieval.query'
            )[0].tolist()
            
            logger.debug(f"🔍 EMBEDDING: Створено вектор розмірності {len(query_embedding)}")
            
            where_clause = {"source": "news"}
            if category_filter:
                where_clause = {
                    "$and": [
                        {"source": {"$eq": "news"}},
                        {"category": {"$eq": category_filter}}
                    ]
                }
            
            search_count = min(max_results * 10, 500)
            logger.debug(f"🔍 EMBEDDING ПОШУК: Запрашуємо {search_count} результатів")
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=search_count,
                where=where_clause
            )
            
            found_count = len(results["documents"][0]) if results["documents"] else 0
            logger.debug(f"🔍 EMBEDDING РЕЗУЛЬТАТИ: Отримано {found_count} документів")
            
            formatted_results = []
            if results["documents"] and len(results["documents"][0]) > 0:
                for i in range(len(results["documents"][0])):
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    
                    formatted_results.append({
                        "content": results["documents"][0][i],
                        "metadata": metadata,
                        "distance": distance,
                        "relevance_score": max(0, 1.0 - (distance / 4)),
                        "id": results["ids"][0][i] if results["ids"] else None,
                        "search_type": "embedding"
                    })
                    
                    if i < 5:
                        title = metadata.get('title', 'No title')[:40]
                        logger.debug(f"🔍 EMBEDDING #{i+1}: distance={distance:.3f}, title='{title}...'")
            
            formatted_results.sort(key=lambda x: x["distance"])
            return formatted_results[:max_results]
            
        except Exception as e:
            logger.error(f"❌ Помилка embedding пошуку: {e}")
            return []
    
    def _keyword_search(self, query: str, max_results: int, category_filter: Optional[str]) -> List[Dict]:
        """Пошук за ключовими словами в змісті документів"""
        try:
            logger.debug(f"🔍 KEYWORD ПОИСК: '{query}'")
            
            # Извлекаем ключевые слова
            keywords = self._extract_keywords(query)
            logger.debug(f"🔍 КЛЮЧОВІ СЛОВА: {keywords}")
            
            # Отримуємо ВСІ документи для пошуку за змістом з правильним синтаксисом
            if category_filter:
                where_clause = {
                    "$and": [
                        {"source": {"$eq": "news"}},
                        {"category": {"$eq": category_filter}}
                    ]
                }
            else:
                where_clause = {"source": {"$eq": "news"}}
            
            all_docs = self.collection.get(where=where_clause)
            if not all_docs["documents"]:
                return []
            
            logger.debug(f"🔍 KEYWORD: Аналізуємо {len(all_docs['documents'])} документів")
            
            scored_results = []
            for i, doc_content in enumerate(all_docs["documents"]):
                metadata = all_docs["metadatas"][i] if all_docs["metadatas"] else {}
                doc_id = all_docs["ids"][i] if all_docs["ids"] else str(i)
                
                # Підраховуємо релевантність за ключовими словами
                score = self._calculate_keyword_score(doc_content, keywords, metadata)
                
                if score > 0:
                    scored_results.append({
                        "content": doc_content,
                        "metadata": metadata,
                        "distance": 1.0 - (score / 10),  # Конвертуємо score в distance
                        "relevance_score": score,
                        "id": doc_id,
                        "search_type": "keyword"
                    })
            
            # Сортуємо за релевантністю
            scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Логуємо топ-результати
            for i, result in enumerate(scored_results[:5]):
                title = result["metadata"].get('title', 'No title')[:40]
                score = result["relevance_score"]
                logger.debug(f"🔍 KEYWORD #{i+1}: score={score:.1f}, title='{title}...'")
            
            return scored_results[:max_results]
            
        except Exception as e:
            logger.error(f"❌ Помилка keyword пошуку: {e}")
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        stop_words = {
            'як', 'мені', 'для', 'на', 'в', 'з', 'по', 'і', 'а', 'але', 'або', 'те', 'що',
            'хто', 'коли', 'де', 'чому', 'який', 'яка', 'яке', 'чи', 'є', 'був', 'була',
            'розкажи', 'скажи', 'покажи', 'знайди', 'дай', 'такий', 'така', 'таке'
        }
        
        clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
        words = [w.strip() for w in clean_query.split() if len(w.strip()) > 2]
        keywords = [w for w in words if w not in stop_words]
        
        # Додаємо повний запит якщо там 1-2 значущих слова
        if len(keywords) <= 2 and keywords:
            keywords.append(' '.join(keywords))
        
        return keywords
    
    def _calculate_keyword_score(self, content: str, keywords: List[str], metadata: Dict) -> float:
        content_lower = content.lower()
        title = metadata.get('title', '').lower()
        
        score = 0.0
        
        for keyword in keywords:
            # Заголовок - максимальний пріоритет
            if keyword in title:
                score += 30.0
            
            # Точні співпадіння в ПОВНОМУ тексті
            content_count = content_lower.count(keyword)
            score += content_count * 3.0
            
            # Fuzzy для слів 4+ символи
            if len(keyword) > 3:
                # Заголовок
                for word in title.split():
                    if fuzz.ratio(keyword, word) > 85:
                        score += 8.0
                        break
                
                # Весь текст (обмежуємо перевірку для продуктивності)
                found_fuzzy = False
                for word in content_lower.split():
                    if fuzz.ratio(keyword, word) > 85:
                        score += 4.0
                        found_fuzzy = True
                        break
        
        return score
    
    def _combine_results(self, embedding_results: List[Dict], keyword_results: List[Dict], top_k: int) -> List[Dict]:
        combined = {}
        
        # Embedding з високими скорами
        for i, result in enumerate(embedding_results):
            doc_id = result["id"]
            result["embedding_rank"] = i + 1
            result["keyword_rank"] = None
            
            distance = result["distance"]
            base = max(0, (2.0 - distance) * 50)
            position_bonus = max(0, (10 - i) * 5)
            
            result["relevance_score"] = base + position_bonus
            result["search_type"] = "embedding"
            combined[doc_id] = result
        
        # Keyword як бустер або нові результати
        for i, result in enumerate(keyword_results):
            doc_id = result["id"]
            if doc_id in combined:
                # Бустимо якщо є в обох
                keyword_boost = result["relevance_score"] * 2
                combined[doc_id]["relevance_score"] += keyword_boost
                combined[doc_id]["search_type"] = "hybrid"
                combined[doc_id]["keyword_rank"] = i + 1
            else:
                # Додаємо як новий
                result["keyword_rank"] = i + 1
                result["embedding_rank"] = None
                result["relevance_score"] = result["relevance_score"] * 3
                result["search_type"] = "keyword"
                combined[doc_id] = result
        
        final = list(combined.values())
        final.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return final[:top_k]
    
    def _expand_query_improved(self, query: str) -> str:
        """ПОКРАЩЕНЕ розширення запиту з урахуванням контексту КАІ"""
        
        # Словник синонімів і пов'язаних термінів для КАІ
        synonyms = {
            # Фінанси та оплата
            "оплат": ["плат", "платіж", "платити", "заплатити", "гроші", "кошт", "вартість", "реквізит", "банк", "рахунок", "квитанц", "переказ"],
            "плат": ["оплат", "платіж", "платити", "заплатити", "гроші", "кошт"],
            "учёб": ["навчання", "освіт", "студент", "семестр", "курс", "університет", "НАУ"],
            "учеб": ["навчання", "освіт", "студент", "семестр", "курс"],
            "реквізит": ["банківськ", "рахунок", "код", "iban", "оплат", "переказ", "квитанц"],
            "реквизит": ["реквізит", "банківськ", "рахунок", "код", "оплат"],
            
            # Навчання
            "навчання": ["освіт", "лекці", "семінар", "заняття", "курс", "студент"],
            "студент": ["учн", "слухач", "курсант", "груп", "факультет"],
            "університет": ["НАУ", "виш", "інститут", "факультет", "кафедр"],
            
            # Наука
            "наук": ["дослідж", "публікац", "конференц", "симпозіум", "дисертац"],
            "співпрац": ["партнер", "угод", "проект", "ініціатив", "договір"],
            
            # События
            "новин": ["подій", "заход", "інформац", "повідомлен", "оголошен"],
            "вступ": ["абітурієнт", "прийом", "документ", "конкурс", "зарахуван"],
            "розклад": ["пар", "заняття", "час", "графік", "лекці"]
        }
        
        query_lower = query.lower()
        expanded_terms = [query]
        
        # Додаємо синоніми для знайдених ключових слів
        for key, values in synonyms.items():
            if key in query_lower:
                expanded_terms.extend(values[:5])  # Беремо топ 5 синонімів
                logger.debug(f"🔍 СИНОНИМЫ для '{key}': {values[:5]}")
            
            # Перевіряємо зворотні збіги
            for value in values:
                if value in query_lower:
                    expanded_terms.append(key)
                    expanded_terms.extend([v for v in values[:3] if v != value])
                    logger.debug(f"🔍 ОБРАТНЫЕ СИНОНИМЫ для '{value}': {key}")
                    break
        
        # Прибираємо дублікати і повертаємо
        unique_terms = list(set(expanded_terms))
        expanded_query = " ".join(unique_terms[:15])  # Збільшуємо ліміт
        
        return expanded_query
    
    def add_documents(self, documents: List[Dict], batch_size: int = 1):
        """Додавання документів з Jina embeddings"""
        if not documents:
            return
        
        logger.info(f"📝 Додавання {len(documents)} документів в базу...")
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            ids = []
            contents_full = []      # повний текст для БД
            contents_embedding = [] # обрізаний для embedding
            metadatas = []
            
            for doc in batch:
                doc_id = doc.get("id", str(uuid.uuid4()))
                ids.append(doc_id)
                
                content = doc.get("content", "")
                
                # ЗБЕРІГАЄМО ПОВНИЙ ТЕКСТ
                contents_full.append(content)
                
                # ДЛЯ EMBEDDING - ОБРІЗАЄМО ДО 10000
                if len(content) > 4000:
                    content_short = content[:4000]
                else:
                    content_short = content
                contents_embedding.append(content_short)
                
                metadata = doc.get("metadata", {})
                if "added_at" not in metadata:
                    metadata["added_at"] = datetime.now().isoformat()
                metadatas.append(metadata)
            
            try:
                # EMBEDDING З ОБРІЗАНОГО ТЕКСТУ
                prefixed_contents = [f"passage: {text}" for text in contents_embedding]
                
                embeddings = self.embedding_model.encode(
                    prefixed_contents,
                    task='retrieval.passage',
                    prompt_name='retrieval.passage'
                ).tolist()
                
                # ЗБЕРІГАЄМО ПОВНИЙ ТЕКСТ В БД
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,        # З обрізаного
                    documents=contents_full,      # ПОВНИЙ текст!
                    metadatas=metadatas
                )
                
                logger.info(f"  ✓ Додано {len(batch)} документів (батч {i//batch_size + 1})")
                
            except Exception as e:
                logger.critical(f"  ✗ Помилка додавання батчу: {e}")
    
    def search(self, query: str, top_k: int = 5, 
              category_filter: Optional[str] = None,
              source_filter: Optional[str] = None,
              metadata_filter: Optional[Dict] = None) -> List[Dict]:
        """Перенаправляємо на гібридний пошук з обробкою фільтрів"""
        # Передаємо всі фільтри в покращений пошук
        return self.search_improved(query, top_k, category_filter)
    
    def search_schedule(self, group: str, day: Optional[str] = None, 
                       week: Optional[int] = None) -> List[Dict]:
        """Спеціалізований пошук по розкладу + Jina"""
        logger.debug(f"📅 ПОШУК РОЗКЛАДУ: group='{group}', day='{day}', week={week}")
        
        where_conditions = [
            {"source": {"$eq": "news"}},
            {"category": {"$eq": "schedule"}},
            {"group": {"$eq": group}}
        ]
        
        if day:
            where_conditions.append({"day": {"$eq": day}})
        if week:
            where_conditions.append({"week": {"$eq": str(week)}})
        
        where_clause = {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0]
        
        try:
            query_text = f"query: розклад {group} {day if day else ''} {week if week else ''}"
            
            query_embedding = self.embedding_model.encode(
                [query_text],
                task='retrieval.query',
                prompt_name='retrieval.query'
            )[0].tolist()
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=20,
                where=where_clause
            )
            
            formatted_results = []
            if results["documents"] and len(results["documents"][0]) > 0:
                for i in range(len(results["documents"][0])):
                    formatted_results.append({
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 1.0,
                        "relevance_score": 1.0 - (results["distances"][0][i] if results["distances"] else 1.0),
                        "id": results["ids"][0][i] if results["ids"] else None,
                        "search_type": "schedule"
                    })
            
            logger.debug(f"📅 ПОШУК РОЗКЛАДУ РЕЗУЛЬТАТ: Знайдено {len(formatted_results)} записів")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Помилка пошуку розкладу: {e}")
            return []
    
    def search_recent_news(self, days: int = 7, category: Optional[str] = None) -> List[Dict]:
        """Пошук останніх новин"""
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        metadata_filter = {}
        if category:
            metadata_filter["category"] = category
        
        results = self.search(
            query="новини НАУ останні події",
            top_k=20,
            source_filter="news",
            metadata_filter=metadata_filter
        )
        
        # Фільтруємо за датою, якщо є
        filtered = []
        for result in results:
            news_date = result["metadata"].get("date", "")
            if news_date:
                try:
                    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                        try:
                            parsed_date = datetime.strptime(news_date, fmt)
                            if parsed_date.strftime("%Y-%m-%d") >= cutoff_date:
                                filtered.append(result)
                            break
                        except:
                            continue
                except:
                    filtered.append(result)
            else:
                filtered.append(result)
        
        return filtered
    
    def debug_search_info(self, query: str) -> Dict:
        """Налагоджувальна інформація про пошук"""
        logger.debug(f"Аналіз запиту '{query}'")
        
        try:
            # Інформація про колекцію
            collection_count = self.collection.count()
            logger.debug(f"Документів у колекції: {collection_count}")
            
            # Приклад документів з ПОВНИМ змістом
            sample = self.collection.get(limit=3)
            logger.debug(f"Приклади документів:")
            if sample["documents"]:
                for i, doc in enumerate(sample["documents"][:3]):
                    metadata = sample["metadatas"][i] if sample["metadatas"] else {}
                    title = metadata.get("title", "No title")
                    content_preview = doc[:200] if doc else "No content"
                    print(f"  {i+1}: Title: {title}")
                    print(f"      Content: {content_preview}...")
                    print(f"      Length: {len(doc)} chars")
            
            # Тестовий пошук keyword
            keywords = self._extract_keywords(query)
            logger.debug(f"Витягнуті ключові слова: {keywords}")
            
            # Тестовий пошук з дуже високим top_k
            test_results = self.collection.query(
                query_embeddings=[self.embedding_model.encode([query]).tolist()[0]],
                n_results=20,
                where={"source": "news"}
            )
            
            if test_results["distances"]:
                distances = test_results["distances"][0]
                logger.debug(f"Топ дистанції: {[f'{d:.3f}' for d in distances[:10]]}")
                logger.debug(f"Мін distance: {min(distances):.3f}")
                logger.debug(f"Макс distance: {max(distances):.3f}")
                logger.debug(f"Середній distance: {sum(distances)/len(distances):.3f}")
                
                # Перевіряємо, скільки документів проходять різні пороги
                for threshold in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
                    count = sum(1 for d in distances if d <= threshold)
                    logger.debug(f"При порозі {threshold}: {count} документів")
            
            return {
                "collection_count": collection_count,
                "sample_docs": len(sample["documents"]) if sample["documents"] else 0,
                "current_threshold": self.similarity_threshold,
                "test_results_count": len(test_results["documents"][0]) if test_results["documents"] else 0,
                "keywords_extracted": keywords
            }
            
        except Exception as e:
            logger.error(f"Ошибка debug: {e}")
            return {"error": str(e)}
    
    def get_stats(self) -> Dict:
        """Отримання статистики бази даних"""
        try:
            all_data = self.collection.get()
            
            stats = {
                "total_documents": len(all_data["ids"]) if all_data["ids"] else 0,
                "categories": {},
                "sources": {},
                "groups": set(),
                "news_count": 0,
                "schedule_count": 0,
                "similarity_threshold": self.similarity_threshold,
                "avg_content_length": 0
            }
            
            if all_data["metadatas"] and all_data["documents"]:
                total_length = 0
                for i, metadata in enumerate(all_data["metadatas"]):
                    # Категорії
                    category = metadata.get("category", "unknown")
                    stats["categories"][category] = stats["categories"].get(category, 0) + 1
                    
                    # Джерела
                    source = metadata.get("source", "unknown") 
                    stats["sources"][source] = stats["sources"].get(source, 0) + 1
                    
                    # Групи (для розкладу)
                    if metadata.get("group"):
                        stats["groups"].add(metadata["group"])
                    
                    # Лічильники за типами
                    if source == "news":
                        stats["news_count"] += 1
                    elif source == "portal" or category == "schedule":
                        stats["schedule_count"] += 1
                    
                    # Довжина контенту
                    if i < len(all_data["documents"]):
                        content_length = len(all_data["documents"][i])
                        total_length += content_length
                
                stats["avg_content_length"] = total_length // len(all_data["documents"]) if all_data["documents"] else 0
            
            stats["groups"] = list(stats["groups"])
            stats["unique_categories"] = len(stats["categories"])
            stats["unique_sources"] = len(stats["sources"])
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}
    
    def clear_collection(self, confirm: bool = False):
        """Очищення колекції"""
        if not confirm:
            logger.debug("⚠️ Для очищення бази даних передайте confirm=True")
            return
        
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "NAU Knowledge Base"}
            )
            logger.info("✅ База даних очищена")
        except Exception as e:
            logger.critical(f"❌ Помилка очищення БД: {e}")
    
    def update_document(self, doc_id: str, new_content: str = None, 
                       new_metadata: Dict = None):
        """Оновлення документа"""
        try:
            result = self.collection.get(ids=[doc_id])
            
            if not result["ids"]:
                print(f"Документ {doc_id} не знайдено")
                return False
            
            content = new_content or result["documents"][0]
            metadata = result["metadatas"][0]
            
            if new_metadata:
                metadata.update(new_metadata)
            
            metadata["updated_at"] = datetime.now().isoformat()
            
            if new_content:
                embedding = self.embedding_model.encode([content]).tolist()[0]
                self.collection.update(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[metadata]
                )
            else:
                self.collection.update(
                    ids=[doc_id],
                    metadatas=[metadata]
                )
            
            logger.debug(f"✅ Документ {doc_id} оновлено")
            return True
            
        except Exception as e:
            logger.critical(f"❌ Помилка оновлення документа: {e}")
            return False
    
    def export_to_json(self, output_path: str = "nau_db_export.json"):
        """Експорт бази даних в JSON"""
        import json
        
        try:
            all_data = self.collection.get()
            
            export_data = []
            if all_data["ids"]:
                for i in range(len(all_data["ids"])):
                    export_data.append({
                        "id": all_data["ids"][i],
                        "content": all_data["documents"][i] if all_data["documents"] else "",
                        "metadata": all_data["metadatas"][i] if all_data["metadatas"] else {}
                    })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Експортовано {len(export_data)} документів в {output_path}")
            
        except Exception as e:
            logger.critical(f"❌ Помилка експорту: {e}")