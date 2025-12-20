from sentence_transformers import CrossEncoder

class ReRanker:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        # This model is specifically trained to score (Query, Document) pairs.
        # It is much more accurate than the Bi-Encoder used for retrieval.
        print(f"Loading Cross-Encoder Re-Ranker: {model_name}...")
        self.model = CrossEncoder(model_name)

    def rank_documents(self, query, documents, top_k=3):
        if not documents:
            return []
            
        # Prepare pairs for scoring
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Predict scores (logits)
        scores = self.model.predict(pairs)
        
        # Combine docs with scores
        scored_docs = list(zip(documents, scores))
        
        # Sort by score (descending)
        ranked_docs = sorted(scored_docs, key=lambda x: x[1], reverse=True)
        
        # Return top K docs only
        return [doc for doc, score in ranked_docs[:top_k]]

if __name__ == "__main__":
    # Test
    ranker = ReRanker()
    query = "Where is the battery located?"
    docs = [
        type("Doc", (object,), {"page_content": "The battery is under the hood."})(),
        type("Doc", (object,), {"page_content": "Tires should be rotated every 5k miles."})(),
        type("Doc", (object,), {"page_content": "Battery voltage is 12V."})()
    ]
    
    top = ranker.rank_documents(query, docs, top_k=2)
    print(f"\nTop Re-Ranked Docs:")
    for d in top:
        print(f"- {d.page_content}")

