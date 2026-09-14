"""Pydantic schemas and the SQL queries behind them.

Every value is passed as a %s parameter with a tuple. Never build SQL with
f-strings -- that is the difference between a query and an SQL injection.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .db import pool


class MessageIn(BaseModel):
    author: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=500)


class Message(MessageIn):
    id: int
    created_at: datetime


def list_messages() -> list[Message]:
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT id, author, content, created_at "
            "FROM messages ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [
        Message(id=r[0], author=r[1], content=r[2], created_at=r[3])
        for r in rows
    ]


def create_message(data: MessageIn) -> Message:
    with pool.connection() as conn:
        row = conn.execute(
            "INSERT INTO messages (author, content) VALUES (%s, %s) "
            "RETURNING id, author, content, created_at",
            (data.author, data.content),
        ).fetchone()
    return Message(id=row[0], author=row[1], content=row[2], created_at=row[3])


def delete_message(message_id: int) -> bool:
    with pool.connection() as conn:
        cur = conn.execute("DELETE FROM messages WHERE id = %s", (message_id,))
    return cur.rowcount > 0
