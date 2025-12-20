from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import re

# Add the root src_python directory to path so we can import our RAG engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src_python')))
from rag_engine import get_rag_chain

app = FastAPI(title="Jarvis AI Backend")

# Enable CORS so your Frontend can talk to this Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the RAG chain
print("Initializing Jarvis RAG Engine...")
chain = get_rag_chain()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    reasoning: str

def is_simple_greeting(text: str) -> bool:
    """Check if the text is a simple greeting to skip RAG for speed."""
    greetings = [
        r"^hi[\s!\.]*$", r"^hello[\s!\.]*$", r"^hey[\s!\.]*$", 
        r"^how are you[\s\?]*$", r"^good morning[\s!\.]*$", 
        r"^good afternoon[\s!\.]*$", r"^good evening[\s!\.]*$",
        r"^what's up[\s\?]*$", r"^sup[\s\?]*$"
    ]
    text = text.lower().strip()
    return any(re.match(pattern, text) for pattern in greetings)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # FAST PATH: If it's a greeting, skip the expensive RAG retrieval and LLM processing
        if is_simple_greeting(request.message):
            return ChatResponse(
                response="Hello! I'm Jarvis, your expert truck configuration specialist. Based on my experience with Ford, RAM, and GMC fleets, I'm here to help you build the perfect truck. What can I help you configure today?",
                reasoning="{\n  \"intent\": \"greeting\",\n  \"confidence\": 1.0,\n  \"reasoning\": \"Simple greeting detected. Fast-path triggered to bypass RAG/LLM for instant response.\",\n  \"active_build\": {\n    \"model\": \"None\",\n    \"engine\": \"None\",\n    \"transmission\": \"None\",\n    \"trim\": \"None\",\n    \"mpg\": \"N/A\",\n    \"status\": \"Incomplete\"\n  }\n}"
            )

        full_response = chain.invoke(request.message)
        
        # Parse the response using our delimiters
        if "--- JARVIS RESPONSE ---" in full_response:
            parts = full_response.split("--- JARVIS RESPONSE ---")
            reasoning = parts[0].replace("--- INTERNAL REASONING ---", "").strip()
            jarvis_speech = parts[1].strip()
            return ChatResponse(response=jarvis_speech, reasoning=reasoning)
        else:
            return ChatResponse(response=full_response, reasoning="No structured reasoning available.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status():
    return {"status": "online", "model": "Mistral 7B (via Ollama)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

