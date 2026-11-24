import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

def get_engine(database_url: str = None):
    db_url = database_url or settings.DATABASE_URL
    if db_url.startswith("sqlite:////data/"):
        # Check if /data exists (Docker volume); if not fallback to local ./data
        if not os.path.exists("/data") and not os.path.exists("C:\\data"):
            os.makedirs("./data", exist_ok=True)
            db_url = "sqlite:///./data/app.db"
    elif "sqlite:///" in db_url:
        db_path = db_url.replace("sqlite:///", "")
        if db_path and db_path != ":memory:":
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    return create_engine(db_url, connect_args=connect_args)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(bind_engine=None):
    target_engine = bind_engine or engine
    Base.metadata.create_all(bind=target_engine)
