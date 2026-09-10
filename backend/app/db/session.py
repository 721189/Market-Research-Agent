import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import settings

logger = logging.getLogger("marketai.db")

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine_kwargs = {}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def wait_for_db(max_retries: int = 5, initial_delay: float = 1.0) -> bool:
    """
    Probes database connectivity with exponential backoff on startup.
    """
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info(f"Database connection verified (attempt {attempt}/{max_retries}).")
                return True
        except Exception as e:
            logger.warning(
                f"Database startup probe attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            delay = min(delay * 2.0, 16.0)
    logger.error("Failed to connect to database after maximum retries.")
    return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
