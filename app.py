from flask import Flask, request, redirect, url_for, session
from datetime import datetime
from hashlib import sha256
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db")

COMMON_STYLE = """
    body {
        font-family: Arial, sans-serif;
        max-width: 700px;
        margin: 40px auto;
        padding: 0 20px;
        background: #f5f5f5;
    }
    h2 { color: #333; }
    .msg { color: red; margin-bottom: 10px; }
    .success { color: green; margin-bottom: 10px; }
    input[type=text], input[type=password] {
        padding: 10px;
        width: 100%;
        margin: 6px 0 14px 0;
        border: 1px solid #ccc;
        border-radius: 4px;
        box-sizing: border-box;
    }
    label { font-weight: bold; }
    .btn {
        padding: 12px 30px;
        font-size: 1em;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        color: white;
        margin-right: 10px;
    }
    .btn-primary { background: #007bff; }
    .btn-primary:hover { background: #0069d9; }
    .btn-success { background: #28a745; }
    .btn-success:hover { background: #218838; }
    .btn-danger { background: #dc3545; }
    .btn-danger:hover { background: #c82333; }
    .btn-secondary { background: #6c757d; }
    .btn-secondary:hover { background: #5a6268; }
    a { color: #007bff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .nav { margin-bottom: 20px; }
    .nav a { margin-right: 15px; }
    .greeting {
        font-size: 1.3em;
        margin-bottom: 20px;
        color: #444;
    }
    .buttons { margin: 20px 0; }
    .buttons form { display: inline; }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    th, td {
        padding: 10px 14px;
        text-align: left;
        border: 1px solid #ddd;
    }
    th { background: #343a40; color: white; }
    tr:nth-child(even) { background: #f9f9f9; }
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            action TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    """)
    # Create default admin if not exists
    admin = c.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not admin:
        pw_hash = sha256("admin123".encode()).hexdigest()
        c.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)",
            ("admin", pw_hash),
        )
    conn.commit()
    conn.close()


# ─── Login ───

@app.route("/", methods=["GET"])
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("home"))

    msg = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        pw_hash = sha256(password.encode()).hexdigest()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, pw_hash),
        ).fetchone()
        conn.close()

        if user:
            session["username"] = user["username"]
            session["is_admin"] = user["is_admin"]
            return redirect(url_for("home"))
        else:
            msg = "Invalid username or password."

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Login</title><style>{COMMON_STYLE}</style></head>
    <body>
        <h2>Login</h2>
        <div class="msg">{msg}</div>
        <form method="POST">
            <label>Username</label>
            <input type="text" name="username" required>
            <label>Password</label>
            <input type="password" name="password" required>
            <button type="submit" class="btn btn-primary">Login</button>
        </form>
        <p>Don't have an account? <a href="{url_for('register')}">Register here</a></p>
    </body>
    </html>
    """


# ─── Register ───

@app.route("/register", methods=["GET", "POST"])
def register():
    if "username" in session:
        return redirect(url_for("home"))

    msg = ""
    success = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            msg = "Username and password are required."
        else:
            pw_hash = sha256(password.encode()).hexdigest()
            conn = get_db()
            try:
                conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, pw_hash),
                )
                conn.commit()
                success = "Registration successful! You can now login."
            except sqlite3.IntegrityError:
                msg = "Username already taken."
            finally:
                conn.close()

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Register</title><style>{COMMON_STYLE}</style></head>
    <body>
        <h2>Register</h2>
        <div class="msg">{msg}</div>
        <div class="success">{success}</div>
        <form method="POST">
            <label>Username</label>
            <input type="text" name="username" required>
            <label>Password</label>
            <input type="password" name="password" required>
            <button type="submit" class="btn btn-primary">Register</button>
        </form>
        <p>Already have an account? <a href="{url_for('login')}">Login here</a></p>
    </body>
    </html>
    """


# ─── Logout ───

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── Home (Punch In / Punch Out) ───

@app.route("/home")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    is_admin = session.get("is_admin", 0)

    conn = get_db()
    records = conn.execute(
        "SELECT name, action, date, time FROM attendance WHERE name = ? ORDER BY id DESC",
        (username,),
    ).fetchall()
    conn.close()

    rows_html = ""
    for r in records:
        rows_html += f"""
        <tr>
            <td>{r['name']}</td>
            <td>{r['action']}</td>
            <td>{r['date']}</td>
            <td>{r['time']}</td>
        </tr>"""

    admin_link = ""
    if is_admin:
        admin_link = f'<a href="{url_for("admin")}">Admin Panel</a>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Attendance</title><style>{COMMON_STYLE}</style></head>
    <body>
        <div class="nav">
            {admin_link}
            <a href="{url_for('logout')}">Logout</a>
        </div>
        <h2>Attendance System</h2>
        <div class="greeting">Hello {username}!</div>

        <div class="buttons">
            <form method="POST" action="{url_for('punch')}">
                <input type="hidden" name="action" value="Punch In">
                <button type="submit" class="btn btn-success">Punch In</button>
            </form>
            <form method="POST" action="{url_for('punch')}">
                <input type="hidden" name="action" value="Punch Out">
                <button type="submit" class="btn btn-danger">Punch Out</button>
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


# ─── Punch ───

@app.route("/punch", methods=["POST"])
def punch():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    action = request.form.get("action", "")
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    conn = get_db()
    conn.execute(
        "INSERT INTO attendance (name, action, date, time) VALUES (?, ?, ?, ?)",
        (username, action, date_str, time_str),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ─── Admin ───

@app.route("/admin")
def admin():
    if "username" not in session:
        return redirect(url_for("login"))
    if not session.get("is_admin", 0):
        return "Access denied", 403

    conn = get_db()
    records = conn.execute(
        "SELECT name, action, date, time FROM attendance ORDER BY id DESC"
    ).fetchall()
    users = conn.execute(
        "SELECT id, username, is_admin FROM users ORDER BY id"
    ).fetchall()
    conn.close()

    # Users table
    users_html = ""
    for u in users:
        role = "Admin" if u["is_admin"] else "User"
        users_html += f"""
        <tr>
            <td>{u['id']}</td>
            <td>{u['username']}</td>
            <td>{role}</td>
        </tr>"""

    # Attendance table
    rows_html = ""
    for r in records:
        rows_html += f"""
        <tr>
            <td>{r['name']}</td>
            <td>{r['action']}</td>
            <td>{r['date']}</td>
            <td>{r['time']}</td>
        </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Admin Panel</title><style>{COMMON_STYLE}</style></head>
    <body>
        <div class="nav">
            <a href="{url_for('home')}">Home</a>
            <a href="{url_for('logout')}">Logout</a>
        </div>
        <h2>Admin Panel</h2>

        <h3>Registered Users</h3>
        <table>
            <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Role</th>
            </tr>
            {users_html}
        </table>

        <h3>All Attendance Records</h3>
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


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
