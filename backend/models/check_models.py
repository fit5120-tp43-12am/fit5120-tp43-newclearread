from __future__ import annotations

from sqlalchemy import create_engine

from core.database import build_database_url
from models import Base  # noqa: F401
from models import entities  # noqa: F401


def main() -> None:
    engine = create_engine(build_database_url(), future=True)
    # Only verifies metadata can be built & DDL can be emitted without errors.
    Base.metadata.create_all(engine)
    print("OK: models imported and metadata.create_all succeeded.")


if __name__ == "__main__":
    main()

