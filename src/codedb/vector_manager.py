import numpy as np
import chromadb
import os
from typing import List, Dict, Any
from .data_models import FunctionSnippet, SearchResult


class VectorManager:
    """向量管理器 - 负责向量编码和数据库操作"""

    def __init__(self, model_name: str = "microsoft/codebert-base", persist_dir: str = "./chroma_db"):
        self.model_name = model_name
        self.persist_dir = persist_dir
        self.tokenizer = None
        self.model = None
        self.client = None
        self.collection = None

        self.initialize_model(model_name)
        self.setup_database(persist_dir)

    def initialize_model(self, model_name: str):
        """加载预训练模型"""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            self.model.eval()
            print(f"Loaded model: {model_name}")

        except ImportError:
            print("Warning: transformers not installed. Using dummy embeddings.")
            self.tokenizer = None
            self.model = None

    def setup_database(self, persist_dir: str):
        """初始化ChromaDB数据库"""
        try:
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.collection = self.client.get_or_create_collection(
                name="code_functions",
                metadata={"description": "Code function semantic vectors"}
            )
            print(f"Database setup at: {persist_dir}")
        except Exception as e:
            print(f"Error setting up database: {e}")
            # 使用内存数据库作为fallback
            self.client = chromadb.Client()
            self.collection = self.client.create_collection(name="code_functions")

    def encode_functions(self, functions: List[FunctionSnippet]) -> List[np.ndarray]:
        """批量编码函数为向量"""
        if not self.model:
            return self._create_dummy_embeddings(len(functions))

        import torch

        vectors = []

        for function in functions:
            try:
                # 准备输入
                inputs = self.tokenizer(
                    function.code,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_attention_mask=True
                )

                # 生成嵌入
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    embedding = self._mean_pooling(outputs, inputs['attention_mask'])
                    embedding = embedding.cpu().numpy().flatten()

                vectors.append(embedding)
            except Exception as e:
                print(f"Error encoding function {function.name}: {e}")
                # 使用零向量作为fallback
                vectors.append(np.zeros(768))

        return vectors

    def encode_single_function(self, function: FunctionSnippet) -> np.ndarray:
        """编码单个函数"""
        return self.encode_functions([function])[0]

    def store_functions(self, functions: List[FunctionSnippet], vectors: List[np.ndarray]):
        """存储函数向量到数据库"""
        if not self.collection:
            print("Database not initialized")
            return

        try:
            # 规范化文件路径
            for func in functions:
                func.file_path = self._normalize_file_path(func.file_path)

            ids = [func.id for func in functions]
            embeddings = [vec.tolist() for vec in vectors]
            metadatas = [{
                'name': func.name,
                'file_path': func.file_path,
                'language': func.language,
                'start_line': func.start_line,
                'end_line': func.end_line
            } for func in functions]
            documents = [func.code for func in functions]

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            print(f"Stored {len(functions)} functions")

        except Exception as e:
            print(f"Error storing functions: {e}")

    def update_functions(self, functions: List[FunctionSnippet], vectors: List[np.ndarray]):
        """更新已有的函数向量"""
        if not self.collection:
            return

        try:
            # 规范化文件路径
            for func in functions:
                func.file_path = self._normalize_file_path(func.file_path)

            # 先删除已存在的记录
            existing_ids = [func.id for func in functions]
            self.delete_functions(existing_ids)

            # 重新添加
            self.store_functions(functions, vectors)
            print(f"Updated {len(functions)} functions")

        except Exception as e:
            print(f"Error updating functions: {e}")

    def delete_functions(self, function_ids: List[str]):
        """删除函数记录"""
        if not self.collection:
            return

        try:
            if function_ids:
                self.collection.delete(ids=function_ids)
                print(f"Deleted {len(function_ids)} functions")
        except Exception as e:
            print(f"Error deleting functions: {e}")

    def search_similar_functions(self, query_vector: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        """搜索相似函数"""
        if not self.collection:
            return []

        try:
            results = self.collection.query(
                query_embeddings=[query_vector.tolist()],
                n_results=top_k,
                include=['metadatas', 'documents', 'distances']
            )

            search_results = []
            seen_functions = set()  # 避免重复结果

            for i in range(len(results['ids'][0])):
                function_id = results['ids'][0][i]
                metadata = results['metadatas'][0][i]
                document = results['documents'][0][i]
                distance = results['distances'][0][i]

                # 创建FunctionSnippet对象
                function = FunctionSnippet(
                    id=function_id,
                    name=metadata.get('name', 'unknown'),
                    code=document,
                    file_path=metadata.get('file_path', ''),
                    start_line=metadata.get('start_line', 0),
                    end_line=metadata.get('end_line', 0),
                    language=metadata.get('language', 'unknown'),
                    metadata={}
                )

                # 避免重复结果
                function_key = f"{function.file_path}:{function.name}"
                if function_key in seen_functions:
                    continue
                seen_functions.add(function_key)

                # 计算相似度得分（将距离转换为相似度）
                similarity_score = 1.0 / (1.0 + distance)

                search_results.append(SearchResult(
                    function=function,
                    similarity_score=similarity_score,
                    vector_distance=distance,
                    match_reason="semantic_similarity"
                ))

            return search_results

        except Exception as e:
            print(f"Error searching functions: {e}")
            return []

    def search_by_function(self, function: FunctionSnippet, top_k: int = 5) -> List[SearchResult]:
        """直接通过函数对象搜索"""
        query_vector = self.encode_single_function(function)
        return self.search_similar_functions(query_vector, top_k)

    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if not self.collection:
            return {'count': 0}

        try:
            count = self.collection.count()
            return {
                'function_count': count,
                'collection_name': self.collection.name
            }
        except:
            return {'function_count': 0}

    def clear_database(self):
        """清空数据库"""
        if not self.collection:
            return

        try:
            # 直接删除整个集合并重新创建
            self.client.delete_collection("code_functions")
            self.collection = self.client.get_or_create_collection(
                name="code_functions",
                metadata={"description": "Code function semantic vectors"}
            )
            print("Database cleared and recreated")
        except Exception as e:
            print(f"Error clearing database: {e}")

    def close(self):
        """关闭数据库连接，释放资源"""
        try:
            if self.client:
                # ChromaDB的PersistentClient通常不需要显式关闭
                # 但我们可以设置引用为None来帮助垃圾回收
                self.collection = None
                self.client = None
                print("Database connections released")
        except Exception as e:
            print(f"Error closing database: {e}")

    def _mean_pooling(self, model_output, attention_mask):
        """均值池化实现"""
        import torch
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def _create_dummy_embeddings(self, count: int) -> List[np.ndarray]:
        """创建虚拟嵌入（用于测试）"""
        return [np.random.randn(768) for _ in range(count)]

    def _normalize_file_path(self, file_path: str) -> str:
        """规范化文件路径格式"""
        # 统一使用相对路径和正斜杠
        normalized = file_path.replace('\\', '/')
        if normalized.startswith('./'):
            normalized = normalized[2:]
        return normalized