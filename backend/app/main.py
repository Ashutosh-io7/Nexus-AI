from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db 

import logging 

logger = logging.getLogger("nexus") 

app = FastAPI(
    title="Nexus AI",
    description="Agentic customer intelligence platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
) 


@app.get("/health") 
def health_check (db: Session = Depends(get_db)): 
    try: 
        db.execute(text("SELECT 1"))
        database = "up" 
    except SQLAlchemyError as exc: 
        logger.error("Database health check failed : %s" , exc) 
        database = "down" 

    body = {
        "status": "ok" if database == "up" else "degraded",
        "service": "nexus-api",
        "environment": settings.app_env, 
        "database": database,
    } 
    status_code = 200 if database == "up" else 503 
    return JSONResponse(status_code=status_code, content=body) 