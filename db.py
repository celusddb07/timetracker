import os
import sys
import psycopg2
import psycopg2.extras


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id          SERIAL PRIMARY KEY,
                    entry_date  DATE NOT NULL,
                    hours       NUMERIC(4,2) NOT NULL,
                    description TEXT NOT NULL,
                    created_at  TIMESTAMP DEFAULT NOW()
                )
            """)
        conn.commit()
    finally:
        conn.close()


def get_entries_for_week(week_start, week_end):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, entry_date, CAST(hours AS FLOAT) AS hours, description
                   FROM entries
                   WHERE entry_date >= %s AND entry_date <= %s
                   ORDER BY entry_date, created_at""",
                (week_start, week_end),
            )
            return cur.fetchall()
    finally:
        conn.close()


def add_entry(entry_date, hours, description):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO entries (entry_date, hours, description) VALUES (%s, %s, %s)",
                (entry_date, hours, description),
            )
        conn.commit()
    finally:
        conn.close()


def delete_entry(entry_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_db()
        print("Database initialized.")
