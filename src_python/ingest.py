import json
import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Path configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "db", "vehicle_config_db")

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

def ingest_data():
    documents = []
    
    # 1. Ingest Master Inventory (External EPA Data)
    # Metadata Schema: { source, make, model, year, price, mpg, type }
    inventory = load_json("master_inventory.json")
    if inventory:
        print("Processing Master Inventory (EPA Data)...")
        for inv in inventory:
            meta = inv.get("metadata", {})
            
            # Construct rich content for semantic search
            content = (
                f"Vehicle: {inv.get('name')}\n"
                f"Details: {inv.get('description')}\n"
                f"MPG: {meta.get('efficiency_city')} City / {meta.get('efficiency_hwy')} Hwy\n"
                f"Specs: {meta.get('engine_size')}L Engine"
            )
            
            # Strict Metadata for Filtering
            doc_meta = {
                "source": "inventory",
                "id": inv.get("id"),
                "make": meta.get("make", "Unknown"),
                "model": meta.get("model", "Unknown"),
                "year": int(meta.get("year", 0)),
                "mpg_city": float(meta.get("efficiency_city", 0)),
                "mpg_hwy": float(meta.get("efficiency_hwy", 0))
            }
            documents.append(Document(page_content=content, metadata=doc_meta))

    # 2. Ingest Technical Manual (Narratives)
    manual = load_json("technical_manual.json")
    if manual:
        print("Processing Technical Manual...")
        for entry in manual:
            content = f"Technical Guide: {entry.get('title')}\nContent: {entry.get('content')}"
            documents.append(Document(page_content=content, metadata={"source": "technical", "category": "guide"}))

    # 3. Ingest Market Pricing
    pricing = load_json("market_pricing.json")
    if pricing:
        print("Processing Market Pricing...")
        for p in pricing:
            content = f"Market Data for {p.get('model')} ({p.get('year')}): Avg Price ${p.get('avg_price')}"
            documents.append(Document(page_content=content, metadata={
                "source": "market", 
                "model": p.get('model'), 
                "year": int(p.get('year', 0)),
                "price": float(p.get('avg_price', 0))
            }))

    # 4. Ingest Vehicle Knowledge Base (Rules & Parts)
    kb = load_json("vehicle_knowledge_base.json")
    if kb:
        print("Processing Knowledge Base...")
        # Parts
        for cat, items in kb.get("parts", {}).items():
            for item in items:
                content = f"Part: {item.get('name')} ({cat})\nDescription: {item.get('description')}"
                documents.append(Document(page_content=content, metadata={"source": "parts", "category": cat}))
        # Rules
        for rule in kb.get("rules", []):
            content = f"Engineering Rule: {rule.get('message')}\nCondition: {rule.get('condition')}"
            documents.append(Document(page_content=content, metadata={"source": "rules"}))

    # Initialize Embeddings and ChromaDB
    print(f"\nCreating embeddings for {len(documents)} total knowledge chunks...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Clear old DB if exists to avoid duplication
    if os.path.exists(DB_PATH):
        import shutil
        shutil.rmtree(DB_PATH)
        
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=DB_PATH
    )
    
    print(f"Master Ingestion complete. Jarvis is now fully loaded with {len(documents)} facts.")

if __name__ == "__main__":
    ingest_data()
