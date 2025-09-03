# src/utils/db_utils.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
from .logger import write_log

def get_db_connection(db_config) -> psycopg2.extensions.connection:
    """
    Connect to PostgreSQL database and return connection object.
    Connection parameters are read from environment variables.
    """
    try:
        conn = psycopg2.connect(
        host=db_config.get("host"),
        port=db_config.get("port", 5433),
        dbname=db_config.get("database"),
        user=db_config.get("user"),
        password=db_config.get("password"),
        cursor_factory=RealDictCursor
    )
        
        print(f"✅ Connected to DB: {db_config.get('database')}")
        return conn
    except Exception as e:
        write_log(f"❌ DB connection error: {e}")
        raise

def fetch_all(query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return all rows as list of dicts.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or [])
                results = cur.fetchall()
                return results
    except Exception as e:
        write_log(f"❌ DB fetch_all error: {e}")
        return []

def fetch_one(query: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Execute a SELECT query and return a single row as dict.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or [])
                result = cur.fetchone()
                return result
    except Exception as e:
        write_log(f"❌ DB fetch_one error: {e}")
        return None
