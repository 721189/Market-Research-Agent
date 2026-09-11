import pytest
from sqlalchemy import create_engine, MetaData
from backend.app.db.session import Base
from alembic.config import Config
from alembic import command
import os
import sqlalchemy as sa

@pytest.fixture
def alembic_config():
    config = Config("backend/alembic.ini")
    test_db_url = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test_parity.db")
    config.set_main_option("sqlalchemy.url", test_db_url)
    return config

def test_schema_parity(alembic_config):
    test_db_url = alembic_config.get_main_option("sqlalchemy.url")
    if "sqlite" in test_db_url and os.path.exists("./test_parity.db"):
        os.remove("./test_parity.db")
        
    engine = create_engine(test_db_url)
    try:
        # Run all migrations
        command.upgrade(alembic_config, "head")
        
        # Reflect db schema
        metadata_db = MetaData()
        metadata_db.reflect(bind=engine)
        
        # Get ORM schema
        metadata_orm = Base.metadata
        
        # Compare tables
        db_tables = set(metadata_db.tables.keys())
        orm_tables = set(metadata_orm.tables.keys())
        
        # Alembic table is expected in DB but not ORM
        assert db_tables - {"alembic_version"} == orm_tables
        
        # Check columns
        for table_name in orm_tables:
            db_cols = set(c.name for c in metadata_db.tables[table_name].columns)
            orm_cols = set(c.name for c in metadata_orm.tables[table_name].columns)
            assert db_cols == orm_cols, f"Column mismatch in {table_name}"
            
    finally:
        engine.dispose()
        if "sqlite" in test_db_url and os.path.exists("./test_parity.db"):
            os.remove("./test_parity.db")
