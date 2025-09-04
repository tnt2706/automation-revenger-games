import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
from .logger import write_log
from config.entities import get_table_name_entity


def get_db_connection(db_config: Dict[str, Any]) -> psycopg2.extensions.connection:
    try:
        conn = psycopg2.connect(
            host=db_config.get("host"),
            port=db_config.get("port", 5432),
            dbname=db_config.get("database"),
            user=db_config.get("user"),
            password=db_config.get("password"),
            cursor_factory=RealDictCursor,
        )
        return conn
    except Exception as e:
        write_log(f"❌ DB connection error: {e}")
        raise


def _fetch_all(
    query: str, params: Optional[List[Any]] = None, db_config: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    if db_config is None:
        raise ValueError("db_config is required")
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or [])
                return cur.fetchall()
    except Exception as e:
        write_log(f"❌ DB fetch_all error: {e}")
        return []


def _fetch_one(
    query: str, params: Optional[List[Any]] = None, db_config: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    if db_config is None:
        raise ValueError("db_config is required")
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or [])
                return cur.fetchone()
    except Exception as e:
        write_log(f"❌ DB fetch_one error: {e}")
        return None


def get_game_info(db_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get all active games from 'games' table.
    """
    query = """
    SELECT game_code, provider, language, game_url
    FROM games
    WHERE active = TRUE
    """
    return _fetch_all(query, db_config=db_config)


def get_all_game_by_code(
    game_code: str, db_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    game_table_name = get_table_name_entity("games")
    query = f"""
    SELECT name, code
    FROM {game_table_name}
    WHERE code LIKE %s AND status = 'ACTIVE'
    """
    return _fetch_all(query, params=[f"{game_code}%"], db_config=db_config)
