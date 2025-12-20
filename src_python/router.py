import re

class SemanticRouter:
    def __init__(self):
        # No LLM initialization needed = Instant startup
        pass

    def route_query(self, query: str):
        q = query.lower().strip()
        
        # 1. Comparison Mode
        if any(x in q for x in ["compare", "vs", "versus", "better than", "difference between", "winner"]):
            return {"intent": "comparison", "confidence": 1.0}
            
        # 2. Market/Pricing Data
        if any(x in q for x in ["price", "cost", "how much", "value", "worth", "cheap", "expensive"]):
            return {"intent": "market_data", "confidence": 1.0}
            
        # 3. Technical Specs
        if any(x in q for x in ["towing", "payload", "engine", "transmission", "torque", "hp", "horsepower", "capacity", "specs", "manual", "technical"]):
            return {"intent": "technical_spec", "confidence": 0.9}
            
        # 4. Inventory Search (Buying/Browsing)
        # If they mention a year or specific make/model, it's likely a search
        if re.search(r'\b(19|20)\d{2}\b', q): # Matches years like 2018, 1999
            return {"intent": "inventory_search", "confidence": 0.9}
        if any(x in q for x in ["find", "show me", "looking for", "i want", "buy", "recommend", "suggest", "search"]):
            return {"intent": "inventory_search", "confidence": 0.8}
            
        # 5. General Chat (Fallback)
        return {"intent": "general_chat", "confidence": 0.5}

if __name__ == "__main__":
    router = SemanticRouter()
    print(router.route_query("Compare the F-150 and Silverado")) # comparison
    print(router.route_query("Find me a 2018 Ford")) # inventory
    print(router.route_query("How much is it?")) # market
