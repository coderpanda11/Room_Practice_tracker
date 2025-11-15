from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import date, datetime, timedelta

DB_PATH = "rooms.db"

app = Flask(__name__)


def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                used_writeup INTEGER NOT NULL,
                solved_at TEXT,
                redo_at TEXT,
                notes TEXT
            );
            """
        )
        conn.commit()
        conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_dmy_to_iso(value: str | None) -> str | None:
    """Convert 'DD-MM-YYYY' string to 'YYYY-MM-DD' (ISO) for DB."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%d-%m-%Y").date()
        return dt.isoformat()
    except ValueError:
        return None


def iso_to_dmy(value: str | None) -> str | None:
    """Convert 'YYYY-MM-DD' (ISO) to 'DD-MM-YYYY' for display."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%d").date()
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return None


@app.route("/")
def index():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM rooms ORDER BY redo_at IS NULL, redo_at ASC, id DESC"
    ).fetchall()
    conn.close()

    rooms = []
    for r in rows:
        r_dict = dict(r)
        r_dict["solved_at_dmy"] = iso_to_dmy(r_dict.get("solved_at"))
        r_dict["redo_at_dmy"] = iso_to_dmy(r_dict.get("redo_at"))
        rooms.append(r_dict)

    today = date.today()
    today_dmy = today.strftime("%d-%m-%Y")
    return render_template("index.html", rooms=rooms, today_dmy=today_dmy)


@app.route("/add", methods=["POST"])
def add_room():
    name = request.form.get("name", "").strip()
    platform = request.form.get("platform", "Other")
    used_writeup = 1 if request.form.get("used_writeup") == "on" else 0
    other_source = request.form.get("other_source") if platform == "Other" else None

    solved_input = request.form.get("solved_at")
    redo_input = request.form.get("redo_at")
    notes = request.form.get("notes", "").strip()

    solved_iso = parse_dmy_to_iso(solved_input)
    redo_iso = parse_dmy_to_iso(redo_input)

    # If redo date is not provided, set it to solved_at + 7 days (if solved_at exists)
    if not redo_iso and solved_iso:
        dt = datetime.strptime(solved_iso, "%Y-%m-%d").date()
        redo_iso = (dt + timedelta(days=7)).isoformat()

    if not name:
        return redirect(url_for("index"))

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO rooms (name, platform, used_writeup, solved_at, redo_at, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, platform, used_writeup, solved_iso, redo_iso, notes),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/edit/<int:room_id>", methods=["GET", "POST"])
def edit_room(room_id):
    conn = get_db_connection()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        platform = request.form.get("platform", "Other")
        used_writeup = 1 if request.form.get("used_writeup") == "on" else 0

        solved_input = request.form.get("solved_at")
        redo_input = request.form.get("redo_at")
        notes = request.form.get("notes", "").strip()

        solved_iso = parse_dmy_to_iso(solved_input)
        redo_iso = parse_dmy_to_iso(redo_input)

        # If redo date is blank, auto set to solved + 7 days
        if not redo_iso and solved_iso:
            dt = datetime.strptime(solved_iso, "%Y-%m-%d").date()
            redo_iso = (dt + timedelta(days=7)).isoformat()

        if name:
            conn.execute(
                """
                UPDATE rooms
                SET name = ?, platform = ?, used_writeup = ?, solved_at = ?, redo_at = ?, notes = ?
                WHERE id = ?
                """,
                (name, platform, used_writeup, solved_iso, redo_iso, notes, room_id),
            )
            conn.commit()
        conn.close()
        return redirect(url_for("index"))
    else:
        row = conn.execute(
            "SELECT * FROM rooms WHERE id = ?", (room_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return redirect(url_for("index"))

        room = dict(row)
        room["solved_at_dmy"] = iso_to_dmy(room.get("solved_at"))
        room["redo_at_dmy"] = iso_to_dmy(room.get("redo_at"))
        return render_template("edit.html", room=room)


@app.route("/delete/<int:room_id>", methods=["POST"])
def delete_room(room_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
