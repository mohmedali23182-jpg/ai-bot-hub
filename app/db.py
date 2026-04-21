import sqlite3
from pathlib import Path
from typing import Dict, List
from .config import settings


def conn() -> sqlite3.Connection:
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db


def init_db() -> None:
    db = conn()
    db.executescript(
        '''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            mode TEXT DEFAULT 'text',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            text TEXT,
            kind TEXT DEFAULT 'text',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS stats (
            key TEXT PRIMARY KEY,
            value INTEGER NOT NULL DEFAULT 0
        );
        '''
    )
    db.commit()
    db.close()


def ensure_chat(chat_id: int) -> None:
    db = conn()
    db.execute('INSERT OR IGNORE INTO chats(chat_id) VALUES (?)', (chat_id,))
    db.commit()
    db.close()


def get_mode(chat_id: int) -> str:
    ensure_chat(chat_id)
    db = conn()
    row = db.execute('SELECT mode FROM chats WHERE chat_id=?', (chat_id,)).fetchone()
    db.close()
    return row['mode'] if row else 'text'


def set_mode(chat_id: int, mode: str) -> None:
    ensure_chat(chat_id)
    db = conn()
    db.execute('UPDATE chats SET mode=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?', (mode, chat_id))
    db.commit()
    db.close()


def add_message(chat_id: int, role: str, text: str, kind: str = 'text') -> None:
    db = conn()
    db.execute('INSERT INTO messages(chat_id, role, text, kind) VALUES (?, ?, ?, ?)', (chat_id, role, text, kind))
    db.commit()
    db.close()


def get_history(chat_id: int, turns: int) -> List[sqlite3.Row]:
    db = conn()
    rows = db.execute(
        'SELECT role, text, kind, created_at FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?',
        (chat_id, turns * 2)
    ).fetchall()
    db.close()
    return list(reversed(rows))


def clear_history(chat_id: int) -> None:
    db = conn()
    db.execute('DELETE FROM messages WHERE chat_id=?', (chat_id,))
    db.commit()
    db.close()


def bump_stat(key: str, amount: int = 1) -> None:
    db = conn()
    db.execute(
        'INSERT INTO stats(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = value + ?',
        (key, amount, amount),
    )
    db.commit()
    db.close()


def get_stats() -> Dict[str, int]:
    db = conn()
    rows = db.execute('SELECT key, value FROM stats ORDER BY key').fetchall()
    db.close()
    return {row['key']: row['value'] for row in rows}


def recent_messages(limit: int = 20):
    db = conn()
    rows = db.execute(
        'SELECT chat_id, role, text, kind, created_at FROM messages ORDER BY id DESC LIMIT ?',
        (limit,),
    ).fetchall()
    db.close()
    return rows
