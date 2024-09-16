from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.config import DATABASE_URL
from sqlalchemy.exc import OperationalError


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

try:
    with engine.connect() as connection:
        print("Connection success!")
except OperationalError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Error: {e}")


def init_db():
    Base.metadata.create_all(bind=engine)
