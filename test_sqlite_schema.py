from pathlib import Path
from autoclean.infrastructure.persistence.sqlite.db_session import initialize_database

db_path = Path.home() / "test_autoclean.db"

conn = initialize_database(db_path)

tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print("Database:", db_path)
print("Tables:")

for table in tables:
    print(table[0])

conn.close()