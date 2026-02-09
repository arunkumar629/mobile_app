import sqlite3
import hashlib
import os
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Flask, request, g, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.urandom(24)
DATABASE = "greetings.db"
IST = timezone(timedelta(hours=5, minutes=30))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS greetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL
        )"""
    )
    db.commit()
    db.close()


def hash_password(password):
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + hashed.hex()


def verify_password(stored, provided):
    salt_hex, hash_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    hashed = hashlib.pbkdf2_hmac("sha256", provided.encode(), salt, 100000)
    return hashed.hex() == hash_hex


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# --- Auth Pages ---

@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""
    success = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        else:
            db = get_db()
            existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                error = "Username already taken."
            else:
                db.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, hash_password(password)),
                )
                db.commit()
                success = "Registration successful! You can now log in."

    alert_html = ""
    if error:
        alert_html = f'<div class="alert alert-danger">{error}</div>'
    if success:
        alert_html = f'<div class="alert alert-success">{success}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - Greeting App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-transparent">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Greeting App</a>
        </div>
    </nav>

    <div class="container d-flex justify-content-center align-items-center" style="min-height: 80vh;">
        <div class="col-md-6 col-lg-5">
            <div class="card border-0 shadow-lg rounded-4">
                <div class="card-body p-5">
                    <h2 class="text-center fw-bold mb-2">Register</h2>
                    <p class="text-center text-muted mb-4">Create a new account</p>
                    {alert_html}
                    <form method="POST">
                        <div class="mb-3">
                            <label for="username" class="form-label fw-semibold">Username</label>
                            <input type="text" class="form-control form-control-lg" id="username" name="username"
                                   placeholder="Choose a username" required>
                        </div>
                        <div class="mb-3">
                            <label for="password" class="form-label fw-semibold">Password</label>
                            <input type="password" class="form-control form-control-lg" id="password" name="password"
                                   placeholder="Create a password" required>
                        </div>
                        <div class="mb-3">
                            <label for="confirm" class="form-label fw-semibold">Confirm Password</label>
                            <input type="password" class="form-control form-control-lg" id="confirm" name="confirm"
                                   placeholder="Confirm your password" required>
                        </div>
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary btn-lg">Register</button>
                        </div>
                    </form>
                    <div class="text-center mt-4">
                        Already have an account? <a href="/login" class="text-decoration-none">Login &rarr;</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and verify_password(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("hello"))
        else:
            error = "Invalid username or password."

    alert_html = ""
    if error:
        alert_html = f'<div class="alert alert-danger">{error}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Greeting App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-transparent">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Greeting App</a>
        </div>
    </nav>

    <div class="container d-flex justify-content-center align-items-center" style="min-height: 80vh;">
        <div class="col-md-6 col-lg-5">
            <div class="card border-0 shadow-lg rounded-4">
                <div class="card-body p-5">
                    <h2 class="text-center fw-bold mb-2">Login</h2>
                    <p class="text-center text-muted mb-4">Sign in to your account</p>
                    {alert_html}
                    <form method="POST">
                        <div class="mb-3">
                            <label for="username" class="form-label fw-semibold">Username</label>
                            <input type="text" class="form-control form-control-lg" id="username" name="username"
                                   placeholder="Enter your username" required>
                        </div>
                        <div class="mb-3">
                            <label for="password" class="form-label fw-semibold">Password</label>
                            <input type="password" class="form-control form-control-lg" id="password" name="password"
                                   placeholder="Enter your password" required>
                        </div>
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary btn-lg">Login</button>
                        </div>
                    </form>
                    <div class="text-center mt-4">
                        Don't have an account? <a href="/register" class="text-decoration-none">Register &rarr;</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- Protected Pages ---

@app.route("/", methods=["GET", "POST"])
@login_required
def hello():
    username = session.get("username", "")
    status = ""
    current_date = ""
    current_time = ""
    if request.method == "POST":
        status = request.form.get("status", "")
        now_ist = datetime.now(IST)
        current_date = now_ist.strftime("%Y-%m-%d")
        current_time = now_ist.strftime("%I:%M:%S %p IST")
        db = get_db()
        db.execute(
            "INSERT INTO greetings (name, date, time, status) VALUES (?, ?, ?, ?)",
            (username, current_date, current_time, status),
        )
        db.commit()

    result_html = ""
    if status:
        badge_class = "bg-success" if status == "In" else "bg-danger"
        result_html = f"""
        <div class="card border-0 shadow-sm mt-4">
            <div class="card-body text-center py-4">
                <h4 class="card-title mb-3">
                    <span class="badge {badge_class} fs-5">{status}</span>
                </h4>
                <p class="text-muted mb-0">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clock me-1" viewBox="0 0 16 16">
                        <path d="M8 3.5a.5.5 0 0 0-1 0V8a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 7.71z"/>
                        <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0"/>
                    </svg>
                    {current_date} | {current_time}
                </p>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Greeting App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-transparent">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Greeting App</a>
            <div class="d-flex align-items-center gap-3">
                <span class="text-white">Hi, {username}</span>
                <a href="/logout" class="btn btn-outline-light btn-sm">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container d-flex justify-content-center align-items-center" style="min-height: 80vh;">
        <div class="col-md-6 col-lg-5">
            <div class="card border-0 shadow-lg rounded-4">
                <div class="card-body p-5">
                    <h2 class="text-center fw-bold mb-2">Welcome, {username}</h2>
                    <p class="text-center text-muted mb-4">Mark your attendance with current time</p>
                    <div class="d-flex gap-3">
                        <form method="POST" class="flex-fill">
                            <input type="hidden" name="status" value="In">
                            <button type="submit" class="btn btn-success btn-lg w-100">In</button>
                        </form>
                        <form method="POST" class="flex-fill">
                            <input type="hidden" name="status" value="Out">
                            <button type="submit" class="btn btn-danger btn-lg w-100">Out</button>
                        </form>
                    </div>
                    {result_html}
                    <div class="text-center mt-4">
                        <a href="/admin" class="text-decoration-none">Go to Admin Panel &rarr;</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""


@app.route("/admin")
@login_required
def admin():
    db = get_db()
    rows = db.execute("SELECT id, name, date, time, status FROM greetings ORDER BY id DESC").fetchall()

    table_rows = ""
    for row in rows:
        badge = '<span class="badge bg-success">In</span>' if row["status"] == "In" else '<span class="badge bg-danger">Out</span>'
        table_rows += f"""
            <tr>
                <td>{row["id"]}</td>
                <td>{row["name"]}</td>
                <td>{row["date"]}</td>
                <td>{row["time"]}</td>
                <td>{badge}</td>
            </tr>"""

    if not rows:
        table_rows = """
            <tr>
                <td colspan="5" class="text-center text-muted py-4">No entries yet</td>
            </tr>"""

    username = session.get("username", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - Greeting App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-transparent">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Greeting App</a>
            <div class="d-flex align-items-center gap-3">
                <span class="text-white">Hi, {username}</span>
                <a href="/logout" class="btn btn-outline-light btn-sm">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container py-5">
        <div class="card border-0 shadow-lg rounded-4">
            <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h3 class="fw-bold mb-0">All Submissions</h3>
                    <span class="badge bg-primary fs-6">{len(rows)} entries</span>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>#</th>
                                <th>Name</th>
                                <th>Date</th>
                                <th>Time (IST)</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
