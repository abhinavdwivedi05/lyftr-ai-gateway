from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db, engine
from app.routes.chat import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables created
    init_db()
    yield
    # Shutdown

app = FastAPI(
    title="Lyftr AI LLM Gateway",
    description="LLM Chatbot with Key Failover and Response Caching",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
origins = settings.allowed_origins_list
has_wildcard = "*" in origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if not has_wildcard else ["*"],
    allow_credentials=not has_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
