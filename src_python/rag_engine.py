import os
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Import our new components
from router import SemanticRouter
from retriever import AdvancedRetriever
from reranker import ReRanker
from prompts.jarvis_persona import build_jarvis_persona
from prompts.system_logic import build_system_logic

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "vehicle_config_db")

class JarvisEngine:
    def __init__(self):
        print("Initializing Semantic Router...")
        self.router = SemanticRouter()
        
        print("Initializing Advanced Retrieval System...")
        self.retriever = AdvancedRetriever(DB_PATH)
        
        print("Initializing Re-Ranker...")
        self.reranker = ReRanker()
        
        print("Initializing Cognitive Layer (Mistral)...")
        self.llm = OllamaLLM(model="mistral")
        
        # Build the Prompt
        self.prompt = ChatPromptTemplate.from_template(f"""
{build_jarvis_persona()}

{build_system_logic()}

# RETRIEVED INTELLIGENCE
{{context}}

# USER QUERY
{{question}}

# OUTPUT INSTRUCTIONS
Your response MUST be divided into two distinct sections:

SECTION 1: --- INTERNAL REASONING ---
Provide a strictly valid JSON object reflecting your logic and the CURRENT state of the vehicle build. 
CRITICAL: You must update the "active_build" object based on the latest user input and previous context.
{{{{
  "intent": "{{intent}}",
  "confidence": 0.0 to 1.0,
  "reasoning": "Brief technical explanation...",
  "active_build": {{{{
    "model": "The specific vehicle model name or 'None'",
    "engine": "Selected engine or 'None'",
    "transmission": "Selected transmission or 'None'",
    "trim": "Selected trim level or 'None'",
    "mpg": "Combined MPG value or 'N/A'",
    "status": "Incomplete | Valid | Invalid"
  }}}},
  "comparison": {{{{
    "vehicle_a": "Name of first vehicle or 'None'",
    "vehicle_b": "Name of second vehicle or 'None'",
    "efficiency_winner": "Vehicle A | Vehicle B | Tie | None",
    "power_winner": "Vehicle A | Vehicle B | Tie | None",
    "summary": "Brief engineering comparison or 'None'"
  }}}}
}}}}

SECTION 2: --- JARVIS RESPONSE ---
Provide your conversational response as Jarvis.
""")

    def process_query(self, query: str):
        # 1. Route the Query
        route = self.router.route_query(query)
        intent = route.get("intent", "general")
        print(f"DEBUG: Intent Detected -> {intent}")

        # 2. Retrieve Context (Hybrid + Self-Query)
        if intent == "general_chat":
            # Skip expensive retrieval for simple chats
            context_text = "User is greeting or asking a general question. No technical data needed."
        else:
            # Fetch candidates (Hybrid)
            raw_docs = self.retriever.hybrid_search(query, k=15)
            
            # Re-Rank (Cross-Encoder)
            top_docs = self.reranker.rank_documents(query, raw_docs, top_k=5)
            
            context_text = "\n\n".join([d.page_content for d in top_docs])
            print(f"DEBUG: Retrieved {len(top_docs)} optimized documents.")

        # 3. Generate Response
        chain = (
            {"context": lambda x: context_text, "question": lambda x: query, "intent": lambda x: intent}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        
        return chain.invoke(query)

# Singleton Instance for app.py import
_engine_instance = None

def get_rag_chain():
    """
    Adapter function to maintain compatibility with app.py.
    Returns a callable that behaves like the old chain.invoke()
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = JarvisEngine()
        
    class ChainAdapter:
        def invoke(self, query):
            return _engine_instance.process_query(query)
            
    return ChainAdapter()

if __name__ == "__main__":
    engine = JarvisEngine()
    print(engine.process_query("Compare the F-150 and Silverado"))
