from flask import Flask, request, redirect, url_for
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

USERNAME = "ai"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            action TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_records():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, action, date, time FROM attendance ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows


@app.route("/")
def home():
    records = get_records()

    rows_html = ""
    for r in records:
        rows_html += f"""
        <tr>
            <td>{r[0]}</td>
            <td>{r[1]}</td>
            <td>{r[2]}</td>
            <td>{r[3]}</td>
        </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Attendance</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 700px;
                margin: 40px auto;
                padding: 0 20px;
                background: #f5f5f5;
            }}
            h2 {{
                color: #333;
            }}
            .greeting {{
                font-size: 1.3em;
                margin-bottom: 20px;
                color: #444;
            }}
            .buttons {{
                margin: 20px 0;
            }}
            .buttons form {{
                display: inline;
            }}
            button {{
                padding: 12px 30px;
                font-size: 1em;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                color: white;
                margin-right: 10px;
            }}
            .punch-in {{
                background: #28a745;
            }}
            .punch-in:hover {{
                background: #218838;
            }}
            .punch-out {{
                background: #dc3545;
            }}
            .punch-out:hover {{
                background: #c82333;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                background: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            th, td {{
                padding: 10px 14px;
                text-align: left;
                border: 1px solid #ddd;
            }}
            th {{
                background: #343a40;
                color: white;
            }}
            tr:nth-child(even) {{
                background: #f9f9f9;
            }}
        </style>
    </head>
    <body>
        <h2>Attendance System</h2>
        <div class="greeting">Hello {USERNAME}!</div>

        <div class="buttons">
            <form method="POST" action="/punch">
                <input type="hidden" name="action" value="Punch In">
                <button type="submit" class="punch-in">Punch In</button>
            </form>
            <form method="POST" action="/punch">
                <input type="hidden" name="action" value="Punch Out">
                <button type="submit" class="punch-out">Punch Out</button>
            </form>
        </div>

        <table>
            <tr>
                <th>Name</th>
                <th>Action</th>
                <th>Date</th>
                <th>Time</th>
            </tr>
            {rows_html}
        </table>
    </body>
    </html>
    """


@app.route("/punch", methods=["POST"])
def punch():
    action = request.form.get("action", "")
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO attendance (name, action, date, time) VALUES (?, ?, ?, ?)",
        (USERNAME, action, date_str, time_str),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
