import json
import os
import sqlite3
import stat
import threading
from datetime import datetime, timedelta, timezone

db_path = os.path.abspath(f"./dbnya.db")

class DatabaseClient:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._initialize_database()
        self._set_permissions()

    def _initialize_database(self):
        with self._connection as conn:
            cursor = conn.cursor()
            # Creating tables
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_prefixes (
                    user_id INTEGER PRIMARY KEY,
                    prefix TEXT
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS floods (
                    gw INTEGER,
                    user_id INTEGER,
                    flood TEXT,
                    PRIMARY KEY (gw, user_id)
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS variabel (
                    _id INTEGER PRIMARY KEY,
                    vars TEXT
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS expired (
                    _id INTEGER PRIMARY KEY,
                    expire_date TEXT
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS userdata (
                    user_id INTEGER PRIMARY KEY,
                    depan TEXT,
                    belakang TEXT,
                    username TEXT,
                    mention TEXT,
                    full TEXT,
                    _id INTEGER
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ubotdb (
                    user_id TEXT PRIMARY KEY,
                    api_id TEXT,
                    api_hash TEXT,
                    session_string TEXT
                )
            """
            )

    def _set_permissions(self):
        try:
            # Ubah izin file menjadi 666 (rw-rw-rw-)
            os.chmod(
                self.db_path,
                stat.S_IRUSR
                | stat.S_IWUSR
                | stat.S_IRGRP
                | stat.S_IROTH
                | stat.S_IWGRP
                | stat.S_IWOTH,
            )
            print(f"Permissions for {self.db_path} set to 666.")
        except Exception as e:
            print(f"Failed to set permissions: {e}")

    def close(self):
        if self._connection:
            self._connection.close()
            print("Database connection closed.")

    def _check_connection(self):
        if not self._connection:
            raise sqlite3.ProgrammingError("Database connection is closed.")

    def set_var(self, bot_id, vars_name, value, query="vars"):
        self._check_connection()
        json_value = json.dumps(value)  # Convert dictionary to JSON string
        with self.lock:
            with self._connection as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO variabel (_id, vars)
                    VALUES (?, json_set(COALESCE((SELECT vars FROM variabel WHERE _id = ?), '{}'), ?, ?))
                    """,
                    (
                        bot_id,
                        bot_id,
                        f"$.{query}.{vars_name}",
                        json_value,
                    ),  # Use JSON string
                )

        # Method to get a variable (with JSON deserialization)

    def get_var(self, bot_id, vars_name, query="vars"):
        self._check_connection()
        with self._connection as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vars FROM variabel WHERE _id = ?", (bot_id,))
            document = cursor.fetchone()

            if document:
                data = json.loads(document[0])  # Parse JSON string to dictionary
                value = data.get(query, {}).get(vars_name)
                # Check if the value is a JSON string and try to decode it
                try:
                    return json.loads(value) if isinstance(value, str) else value
                except json.JSONDecodeError:
                    return value  # If decoding fails, return the value as is
            return None

    # Replacing remove_var
    def remove_var(self, bot_id, vars_name, query="vars"):
        self._check_connection()
        with self._connection as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE variabel SET vars = json_remove(vars, ?) WHERE _id = ?
            """,
                (f"$.{query}.{vars_name}", bot_id),
            )

    # Replacing all_var
    def all_var(self, user_id, query="vars"):
        self._check_connection()
        with self._connection as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vars FROM variabel WHERE _id = ?", (user_id,))
            result = cursor.fetchone()

            return json.loads(result[0]).get(query) if result else None

    # Replacing rm_all
    def rm_all(self, bot_id):
        self._check_connection()
        with self._connection as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM variabel WHERE _id = ?", (bot_id,))

    # Replacing get_list_from_var
    def get_list_from_var(self, user_id, vars_name, query="vars"):
        self._check_connection()
        vars_data = self.get_var(user_id, vars_name, query)
        return [int(x) for x in str(vars_data).split()] if vars_data else []

    # Replacing add_to_var
    def add_to_var(self, user_id, vars_name, value, query="vars"):
        self._check_connection()
        vars_list = self.get_list_from_var(user_id, vars_name, query)
        vars_list.append(value)
        self.set_var(user_id, vars_name, " ".join(map(str, vars_list)), query)

    # Replacing remove_from_var
    def remove_from_var(self, user_id, vars_name, value, query="vars"):
        self._check_connection()
        vars_list = self.get_list_from_var(user_id, vars_name, query)
        if value in vars_list:
            vars_list.remove(value)
            self.set_var(user_id, vars_name, " ".join(map(str, vars_list)), query)

dB = DatabaseClient(db_path)