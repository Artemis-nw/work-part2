
from database import DATABASE, get_db_connection

print("Database path:", DATABASE)

connection = get_db_connection()
tables = connection.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print("Tables found:", [row["name"] for row in tables])

connection.close()
