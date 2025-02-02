import os
from sshtunnel import SSHTunnelForwarder
from psycopg2 import pool
from dotenv import load_dotenv
from telebot import types
from typing import Any
import psycopg2

load_dotenv()


if os.environ.get("ENV") == "dev":
    print("DEV: Connecting to local database")
    server = SSHTunnelForwarder(
        (os.environ.get("SSH_HOST"), 22),
        ssh_private_key=os.environ.get("SSH_KEY"),
        ssh_username=os.environ.get("SSH_USER"),
        ssh_password=(
            os.environ.get("SSH_PASSWORD") if os.environ.get("SSH_PASSWORD") else None
        ),
        remote_bind_address=("localhost", int(os.environ.get("DB_PORT"))),
    )
    server.start()

db = pool.SimpleConnectionPool(
    1,
    20,
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD"),
    host="localhost" if os.environ.get("ENV") == "dev" else os.environ.get("DB_HOST"),
    port=(
        server.local_bind_port
        if os.environ.get("ENV") == "dev"
        else os.environ.get("DB_PORT")
    ),
    database=os.environ.get("DB_NAME"),
)


def check_database():
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{os.environ.get('DB_NAME')}'"
    )
    exists = cursor.fetchone()
    if not exists:
        print("Database does not exist")
        exit(1)

    db.putconn(conn)

    return


check_database()


def into_dict(data: tuple, column_name: list[tuple]) -> dict:
    cols = [desc[0] for desc in column_name]

    return dict(zip(cols, data)) if data else None


def into_list(rows: list[tuple], column_name: list[tuple]) -> list[dict]:
    cols = [desc[0] for desc in column_name]

    return [dict(zip(cols, row)) for row in rows] if rows else []


def get_user(user_id: int) -> dict:
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    db.putconn(conn)

    return into_dict(row, cursor.description)


def new_user(
    user_id: int, username: str, firstname: str, lastname: str, phone: str
) -> None:
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (id, username, firstname, lastname, phone) VALUES (%s, %s, %s, %s, %s)",
        (user_id, username, firstname, lastname, phone),
    )
    conn.commit()
    db.putconn(conn)

    return


def new_payments(
    user_id: int,
    amount: float,
    subscription_id: int,
    payment_id: int,
) -> None:
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO payments (user_id, amount, subscription_id, payment_id) VALUES (%s, %s, %s, %s)",
        (user_id, amount, subscription_id, payment_id),
    )
    conn.commit()
    db.putconn(conn)

    return


def new_request(user_id: int, request_status: str, request_data: str) -> None:
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO requests (user_id, request_status, request_data) VALUES (%s, %s, %s)",
        (user_id, request_status, request_data),
    )
    conn.commit()
    db.putconn(conn)

    return


def new_subscription(user_id: int, start_date: str, end_date: str, price: float) -> int:
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subscriptions (user_id, start_date, end_date, price) VALUES (%s, %s, %s, %s) RETURNING id",
        (user_id, start_date, end_date, price),
    )
    subscription_id = cursor.fetchone()[0]
    conn.commit()
    db.putconn(conn)

    return subscription_id


def update_user(user_id: int, key: str, value: Any) -> None:
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET {key} = %s WHERE id = %s",
        (value, user_id),
    )
    conn.commit()
    db.putconn(conn)

    return


def update_request(request_id: int, key: str, value: Any) -> None:
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE requests SET {key} = %s WHERE id = %s",
        (value, request_id),
    )
    conn.commit()
    db.putconn(conn)

    return


def update_user(user_id: int, key: str, value: Any) -> None:
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET {key} = %s WHERE id = %s",
        (value, user_id),
    )
    conn.commit()
    db.putconn(conn)

    return


def get_subscription(user_id: int) -> dict:
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM subscriptions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    row = cursor.fetchone()
    db.putconn(conn)

    return into_dict(row, cursor.description)


def get_requests(request_status="new", request_id=None) -> list[dict]:
    conn = db.getconn()
    cursor = conn.cursor()
    if request_id:
        cursor.execute("SELECT * FROM requests WHERE id = %s", (request_id,))
    else:
        cursor.execute(
            f"SELECT * FROM requests WHERE request_status = '{request_status}'"
        )
    rows = cursor.fetchall()
    db.putconn(conn)

    return into_list(rows, cursor.description)


def get_owe():
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM subscriptions WHERE end_date < NOW() + INTERVAL '3 days' AND price != 0 ORDER BY created_at DESC LIMIT 1"
    )
    rows = cursor.fetchall()
    db.putconn(conn)

    return into_list(rows, cursor.description)


def get_users():
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    db.putconn(conn)

    return into_list(rows, cursor.description)
