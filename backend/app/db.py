from collections.abc import Generator
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./toy_marketplace.db")

engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def ensure_sqlite_product_columns() -> None:
    """Bring the local SQLite product table forward without dropping data."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    product_columns = {column["name"] for column in inspect(engine).get_columns("products")}
    variant_columns = {column["name"] for column in inspect(engine).get_columns("product_variants")}
    product_additions = {
        "vat_rate": "NUMERIC(5, 2) NOT NULL DEFAULT 20.00",
        "safety_warning": "TEXT NOT NULL DEFAULT 'Uyarı belirtilmedi.'",
        "attributes": "JSON NOT NULL DEFAULT '{}'",
    }
    variant_additions = {
        "inventory_updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    }
    missing = [
        ("products", name, definition)
        for name, definition in product_additions.items()
        if name not in product_columns
    ] + [
        ("product_variants", name, definition)
        for name, definition in variant_additions.items()
        if name not in variant_columns
    ]
    if not missing:
        return
    with engine.begin() as connection:
        for table, name, definition in missing:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
