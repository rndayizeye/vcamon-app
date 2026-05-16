import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# On Streamlit Cloud the working directory isn't writable — use /tmp instead
_default_url = os.getenv("DATABASE_URL", "sqlite:///./data/vcamon.db")

if _default_url.startswith("sqlite:///./"):
    # Resolve relative path; fall back to /tmp if ./data isn't writable
    _rel_path = _default_url.replace("sqlite:///./", "")
    _abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", _rel_path)
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
        DATABASE_URL = "sqlite:////tmp/vcamon.db"
else:
    DATABASE_URL = _default_url

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def init_db():
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()