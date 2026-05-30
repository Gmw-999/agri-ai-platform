"""
农业知识向量数据库 - 完整版
支持文档的增删改查、批量操作和日志记录
"""
import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from config.settings import VECTOR_DB_DIR, VECTOR_COLLECTION_NAME, VECTOR_EMBEDDING_MODEL


class AgriVectorDB:
    """农业知识向量数据库 - 完整版"""

    def __init__(
            self,
            collection_name: str = VECTOR_COLLECTION_NAME,
            embedding_model: str = VECTOR_EMBEDDING_MODEL,
            enable_logging: bool = True
    ):
        # 创建日志记录器
        self.logger = logging.getLogger("agri_ai.vector_db")
        if enable_logging:
            self._setup_logger()

        self.logger.info(f"初始化向量数据库: {collection_name}")

        # 创建向量数据库目录
        os.makedirs(VECTOR_DB_DIR, exist_ok=True)
        self.logger.debug(f"向量数据库目录: {os.path.abspath(VECTOR_DB_DIR)}")

        # 初始化Chroma客户端
        try:
            try:
                self.client = chromadb.PersistentClient(
                    path=VECTOR_DB_DIR,
                    settings=Settings(
                        anonymized_telemetry=False
                    )
                )
            except TypeError:
                self.client = chromadb.PersistentClient(
                    persist_directory=VECTOR_DB_DIR,
                    settings=Settings(
                        anonymized_telemetry=False
                    )
                )
            self.logger.info("Chroma客户端初始化成功")
        except Exception as e:
            self.logger.error(f"Chroma客户端初始化失败: {e}", exc_info=True)
            raise

        # 获取/创建集合
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "description": "农业知识向量数据库",
                    "created_at": datetime.now().isoformat(),
                    "embedding_model": embedding_model
                }
            )
            self.logger.info(f"集合 '{collection_name}' 初始化成功，当前文档数: {self.collection.count()}")
        except Exception as e:
            self.logger.error(f"集合初始化失败: {e}", exc_info=True)
            raise

        # 初始化嵌入模型
        try:
            self.logger.info(f"加载嵌入模型: {embedding_model}")
            self.embedding_model = SentenceTransformer(embedding_model, local_files_only=True)
            self.logger.info("嵌入模型加载成功")
        except Exception as e:
            self.logger.error(f"嵌入模型加载失败: {e}", exc_info=True)
            raise

    def _setup_logger(self):
        """配置日志记录器"""
        logger = logging.getLogger("agri_ai.vector_db")
        if not logger.handlers:
            logger.setLevel(logging.INFO)

            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_format)
            logger.addHandler(console_handler)

            # 文件处理器（可选）
            try:
                log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
                os.makedirs(log_dir, exist_ok=True)
                file_handler = logging.FileHandler(
                    os.path.join(log_dir, 'vector_db.log'),
                    encoding='utf-8'
                )
                file_handler.setLevel(logging.DEBUG)
                file_format = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_format)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"文件日志处理器创建失败: {e}")

    def add_document(
            self,
            text: str,
            metadata: Optional[Dict[str, Any]] = None,
            doc_id: Optional[str] = None
    ) -> str:
        """
        添加单个文档到向量数据库

        Args:
            text: 文档文本内容
            metadata: 元数据字典，如 {"source": "农业手册", "category": "病虫害"}
            doc_id: 自定义文档ID，不传则自动生成

        Returns:
            文档ID
        """
        try:
            if not text or not text.strip():
                self.logger.warning("尝试添加空文档")
                raise ValueError("文档内容不能为空")

            # 生成或使用提供的ID
            if doc_id is None:
                doc_id = str(uuid.uuid4())

            # 生成嵌入向量
            self.logger.debug(f"为文档生成嵌入向量: {doc_id[:8]}...")
            embedding = self.embedding_model.encode([text])[0].tolist()

            # 准备元数据
            if metadata is None:
                metadata = {}
            metadata["added_at"] = datetime.now().isoformat()
            metadata["text_length"] = len(text)

            # 添加到集合
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text]
            )

            self.logger.info(f"✅ 文档添加成功 | ID: {doc_id[:8]}... | 长度: {len(text)}字符")
            return doc_id

        except Exception as e:
            self.logger.error(f"❌ 文档添加失败: {e}", exc_info=True)
            raise

    def add_documents_batch(
            self,
            texts: List[str],
            metadatas: Optional[List[Dict[str, Any]]] = None,
            doc_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        批量添加文档

        Args:
            texts: 文档文本列表
            metadatas: 元数据列表（与texts一一对应）
            doc_ids: 文档ID列表（与texts一一对应）

        Returns:
            文档ID列表
        """
        try:
            if not texts:
                self.logger.warning("尝试批量添加空列表")
                return []

            count = len(texts)
            self.logger.info(f"开始批量添加 {count} 个文档")

            # 生成IDs
            if doc_ids is None:
                doc_ids = [str(uuid.uuid4()) for _ in range(count)]

            # 准备元数据
            if metadatas is None:
                metadatas = [{} for _ in range(count)]

            # 确保元数据包含时间戳
            for meta in metadatas:
                meta["added_at"] = datetime.now().isoformat()
                meta["text_length"] = len(meta.get("text", ""))

            # 批量生成嵌入向量
            self.logger.debug(f"批量生成 {count} 个嵌入向量")
            embeddings = self.embedding_model.encode(texts).tolist()

            # 批量添加
            self.collection.add(
                ids=doc_ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts
            )

            self.logger.info(f"✅ 批量添加成功 | 数量: {count}")
            return doc_ids

        except Exception as e:
            self.logger.error(f"❌ 批量添加失败: {e}", exc_info=True)
            raise

    def search(
            self,
            query: str,
            top_k: int = 3,
            filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        相似度搜索

        Args:
            query: 查询文本
            top_k: 返回最相似的K个结果
            filter_metadata: 元数据过滤条件，如 {"category": "病虫害"}

        Returns:
            搜索结果列表，每个结果包含 document, metadata, distance, id
        """
        try:
            if not query or not query.strip():
                self.logger.warning("搜索查询为空")
                return []

            self.logger.debug(f"执行搜索 | 查询: '{query[:50]}...' | top_k: {top_k}")

            # 生成查询向量
            query_embedding = self.embedding_model.encode([query])[0].tolist()

            # 执行搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances", "ids"]
            )

            # 格式化结果
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    result = {
                        "id": results["ids"][0][i],
                        "document": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": float(results["distances"][0][i]) if results["distances"] else None,
                        "similarity": 1 - float(results["distances"][0][i]) if results["distances"] else None
                    }
                    formatted_results.append(result)

            self.logger.info(f"🔍 搜索完成 | 返回 {len(formatted_results)} 个结果")
            return formatted_results

        except Exception as e:
            self.logger.error(f"❌ 搜索失败: {e}", exc_info=True)
            raise

    def delete_document(self, doc_id: str) -> bool:
        """
        删除指定文档

        Args:
            doc_id: 文档ID

        Returns:
            是否删除成功
        """
        try:
            self.logger.info(f"删除文档 | ID: {doc_id}")
            self.collection.delete(ids=[doc_id])
            self.logger.info(f"✅ 文档删除成功 | ID: {doc_id}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 文档删除失败: {e}", exc_info=True)
            return False

    def delete_by_filter(self, filter_metadata: Dict[str, Any]) -> int:
        """
        根据元数据过滤条件批量删除文档

        Args:
            filter_metadata: 过滤条件，如 {"category": "过时知识"}

        Returns:
            删除的文档数量
        """
        try:
            self.logger.info(f"批量删除文档 | 条件: {filter_metadata}")

            # 先查询符合条件的文档
            results = self.collection.get(where=filter_metadata)
            count = len(results["ids"]) if results["ids"] else 0

            if count > 0:
                self.collection.delete(where=filter_metadata)
                self.logger.info(f"✅ 批量删除成功 | 删除 {count} 个文档")
            else:
                self.logger.info("未找到符合条件的文档")

            return count

        except Exception as e:
            self.logger.error(f"❌ 批量删除失败: {e}", exc_info=True)
            raise

    def update_document(
            self,
            doc_id: str,
            text: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新文档

        Args:
            doc_id: 文档ID
            text: 新的文本内容（可选）
            metadata: 新的元数据（可选）

        Returns:
            是否更新成功
        """
        try:
            self.logger.info(f"更新文档 | ID: {doc_id}")

            update_kwargs = {"ids": [doc_id]}

            if text is not None:
                embedding = self.embedding_model.encode([text])[0].tolist()
                update_kwargs["embeddings"] = [embedding]
                update_kwargs["documents"] = [text]

            if metadata is not None:
                metadata["updated_at"] = datetime.now().isoformat()
                update_kwargs["metadatas"] = [metadata]

            self.collection.update(**update_kwargs)
            self.logger.info(f"✅ 文档更新成功 | ID: {doc_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ 文档更新失败: {e}", exc_info=True)
            return False

    def get_document_count(self) -> int:
        """获取文档总数"""
        try:
            count = self.collection.count()
            self.logger.debug(f"当前文档总数: {count}")
            return count
        except Exception as e:
            self.logger.error(f"获取文档数量失败: {e}")
            return 0

    def get_all_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取所有文档（用于调试或导出）

        Args:
            limit: 最大返回数量

        Returns:
            文档列表
        """
        try:
            self.logger.debug(f"获取所有文档 | 限制: {limit}")
            results = self.collection.get(limit=limit)

            documents = []
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"]):
                    documents.append({
                        "id": doc_id,
                        "document": results["documents"][i] if results["documents"] else "",
                        "metadata": results["metadatas"][i] if results["metadatas"] else {}
                    })

            self.logger.info(f"返回 {len(documents)} 个文档")
            return documents

        except Exception as e:
            self.logger.error(f"获取文档列表失败: {e}", exc_info=True)
            raise

    def clear_collection(self) -> bool:
        """清空整个集合"""
        try:
            self.logger.warning("⚠️ 清空整个向量数据库集合")
            self.collection.delete()
            self.logger.info("✅ 集合已清空")
            return True
        except Exception as e:
            self.logger.error(f"❌ 清空集合失败: {e}", exc_info=True)
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            stats = {
                "document_count": self.collection.count(),
                "collection_name": self.collection.name,
                "embedding_dimension": len(self.embedding_model.encode(["test"])[0]),
                "database_path": os.path.abspath(VECTOR_DB_DIR)
            }
            self.logger.debug(f"集合统计: {stats}")
            return stats
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}
