import sqlite3
from pathlib import Path


# Store the database in the main project folder.
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "storyverse.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)

    # Allows us to access columns by name.
    connection.row_factory = sqlite3.Row

    # Enforces database relationships.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection