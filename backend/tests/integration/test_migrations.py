import pytest
from alembic.config import Config
from alembic import command
import os
from sqlalchemy import create_engine, inspect

@pytest.fixture
def alembic_config():
    # Provide path to alembic.ini
    config = Config("backend/alembic.ini")
    # Override the sqlalchemy.url for testing
    test_db_url = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test_migrations.db")
    config.set_main_option("sqlalchemy.url", test_db_url)
    return config

def test_upgrade_downgrade(alembic_config):
    # Ensure starting clean
    test_db_url = alembic_config.get_main_option("sqlalchemy.url")
    if "sqlite" in test_db_url and os.path.exists("./test_migrations.db"):
        os.remove("./test_migrations.db")
        
    engine = create_engine(test_db_url)
    
    try:
        # Upgrade to head
        command.upgrade(alembic_config, "head")
        
        # Verify schema
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert "users" in tables
        assert "evidence" in tables
        assert "claims" in tables
        assert "llm_calls" in tables
        
        # Check specific column introduced in 003
        evidence_columns = [c["name"] for c in inspector.get_columns("evidence")]
        assert "raw_snippet" in evidence_columns
        assert "canonical_url" in evidence_columns
        
        # Downgrade to base
        command.downgrade(alembic_config, "base")
        
        inspector = inspect(engine)
        assert "users" not in inspector.get_table_names()
    finally:
        engine.dispose()
        if "sqlite" in test_db_url and os.path.exists("./test_migrations.db"):
            os.remove("./test_migrations.db")
