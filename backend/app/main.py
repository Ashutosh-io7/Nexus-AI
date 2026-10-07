from fastapi import FastAPI 

app = FastAPI(
    title="Nexus AI",
    description="Agentic customer intelligence platform",
    version="0.1.0",
) 

@app.get("/health") 
def health_check () : 
    return {"status": "ok", "service": "nexus-api"}