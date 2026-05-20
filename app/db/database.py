import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

# On Streamlit Cloud the working directory isn't writable — use /tmp instead
_default_url = os.getenv("DATABASE_URL", "sqlite:///./data/vcamon_v2.db")

if _default_url.startswith("sqlite:///./"):
    # Resolve relative path; fall back to /tmp if ./data isn't writable
    _rel_path = _default_url.replace("sqlite:///./", "")
    _abs_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", _rel_path
    )
    _abs_path = os.path.normpath(_abs_path)
    _data_dir = os.path.dirname(_abs_path)
    try:
        os.makedirs(_data_dir, exist_ok=True)
        # Test writability
        _test = os.path.join(_data_dir, ".write_test")
        open(_test, "w").close()
        os.remove(_test)
        DATABASE_URL = f"sqlite:///{_abs_path}"
    except OSError:
        # Fall back to /tmp for Streamlit Cloud
        DATABASE_URL = "sqlite:////tmp/vcamon_v2.db"
else:
    DATABASE_URL = _default_url

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def init_db():
    from app.db import models  # noqa: F401
    try:
        inspector = inspect(engine)
        if inspector.has_table("cases"):
            columns = [col['name'] for col in inspector.get_columns("cases")]
            required_columns = ['initial_contact_date', 'symptom_classification']
            
            if not all(col in columns for col in required_columns):
                print("⚠️  Database schema mismatch - recreating tables...")
                Base.metadata.drop_all(bind=engine)
    except Exception as e:
        print(f"Schema check failed: {e}")
        # On error, drop and recreate to be safe
        Base.metadata.drop_all(bind=engine)
    
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()