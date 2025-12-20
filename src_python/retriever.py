import os
import time
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class AdvancedRetriever:
    def __init__(self, db_path):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = Chroma(persist_directory=db_path, embedding_function=self.embeddings)
        
        # Initialize Self-Query LLM
        self.llm = OllamaLLM(model="mistral")
        self.self_query_prompt = ChatPromptTemplate.from_template("""
        You are a Metadata Filter Generator.
        Translate the user's query into a valid Metadata Dictionary for filtering.
        
        ALLOWED FIELDS:
        - "make" (string)
        - "year" (integer)
        - "mpg_city" (float, use for efficiency queries)
        - "price" (float)
        
        USER QUERY: {question}
        
        EXAMPLES:
        "Find 2018 Fords" -> {{ "year": 2018, "make": "Ford" }}
        "Trucks under $20000" -> {{ "price": {{ "$lt": 20000 }} }}
        "High efficiency trucks" -> {{ "mpg_city": {{ "$gt": 20 }} }}
        
        OUTPUT:
        Return ONLY the JSON object. If no filters apply, return {{}}.
        """)
        self.filter_chain = self.self_query_prompt | self.llm | StrOutputParser()

        # Build In-Memory BM25 Index from VectorStore Documents
        # Note: In production, you would persist this index separately.
        # For now, we fetch all docs to build the keyword index.
        print("Building BM25 Keyword Index (Hybrid Search)...")
        try:
            # ChromaDB v0.4+ method to get all docs
            all_docs = self.vectorstore.get() 
            self.docs_map = all_docs['documents']
            self.metadatas_map = all_docs['metadatas']
            self.ids_map = all_docs['ids']
            
            tokenized_corpus = [doc.lower().split() for doc in self.docs_map]
            self.bm25 = BM25Okapi(tokenized_corpus)
            print("BM25 Index Built.")
        except Exception as e:
            print(f"BM25 Build Error: {e}")
            self.bm25 = None

    def _generate_filters(self, query: str):
        try:
            # Mistral might be chatty, so we strip markdown code blocks if present
            raw = self.filter_chain.invoke({"question": query})
            clean = raw.replace("```json", "").replace("```", "").strip()
            import json
            filters = json.loads(clean)
            return filters if filters else None
        except:
            return None

    def hybrid_search(self, query: str, k=5):
        # 1. Self-Query: Generate Filters (OPTIMIZED)
        # Only call the LLM if we detect filterable keywords to save time
        filters = None
        trigger_keywords = ["year", "make", "model", "price", "cost", "mpg", "efficiency", "city", "hwy", "201", "202", "199", "$"]
        if any(w in query.lower() for w in trigger_keywords):
            print("Complex query detected. Engaging Self-Query Filter...")
            filters = self._generate_filters(query)
            print(f"Generated Filters: {filters}")
        else:
            print("Simple query detected. Skipping Self-Query Filter.")
        
        # ChromaDB requires "$and" wrapper for multiple conditions
        chroma_filter = filters
        if filters and len(filters) > 1:
            chroma_filter = { "$and": [ {k: v} for k, v in filters.items() ] }

        # 2. Vector Search (Semantic)
        try:
            semantic_results = self.vectorstore.similarity_search(
                query, 
                k=k, 
                filter=chroma_filter
            )
        except Exception as e:
            print(f"Semantic Search Error (Filter issue?): {e}")
            # Fallback to unfiltered search
            semantic_results = self.vectorstore.similarity_search(query, k=k)
        
        # 3. Keyword Search (BM25)
        keyword_results = []
        if self.bm25:
            tokenized_query = query.lower().split()
            # Get top N scores
            doc_scores = self.bm25.get_scores(tokenized_query)
            top_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:k]
            
            for idx in top_indices:
                # Reconstruct Document object
                if doc_scores[idx] > 0.0: # Only relevant matches
                    doc = Document(
                        page_content=self.docs_map[idx],
                        metadata=self.metadatas_map[idx]
                    )
                    keyword_results.append(doc)

        # 4. Deduplicate & Combine
        # We prefer Semantic results, but add unique Keyword results
        combined_docs = semantic_results
        seen_contents = {doc.page_content for doc in semantic_results}
        
        for doc in keyword_results:
            if doc.page_content not in seen_contents:
                combined_docs.append(doc)
                seen_contents.add(doc.page_content)
        
        return combined_docs

if __name__ == "__main__":
    # Test
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "db", "vehicle_config_db")
    
    retriever = AdvancedRetriever(db_path)
    results = retriever.hybrid_search("Find me a 2015 Ford F-150")
    print(f"\nRetrieved {len(results)} documents.")
    for i, doc in enumerate(results):
        print(f"[{i}] {doc.page_content[:100]}...")

