from flask import Flask, request, redirect, url_for, session
from datetime import datetime
from hashlib import sha256
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db")

BOOTSTRAP_HEAD = """
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
<style>
    body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
    .card { border: none; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); }
    .card-header { border-radius: 16px 16px 0 0 !important; }
    .btn { border-radius: 10px; font-weight: 600; }
    .table { margin-bottom: 0; }
    .table thead th { border-bottom: 2px solid #dee2e6; }
    .navbar { box-shadow: 0 2px 15px rgba(0,0,0,0.1); }
    .punch-btn { padding: 16px 40px; font-size: 1.15rem; letter-spacing: 0.5px; transition: transform 0.15s; }
    .punch-btn:hover { transform: translateY(-2px); }
    .badge-punch-in { background: #d4edda; color: #155724; }
    .badge-punch-out { background: #f8d7da; color: #721c24; }
    .avatar { width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.3rem; font-weight: 700; color: #fff; }
</style>
"""

BOOTSTRAP_SCRIPTS = """
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
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
    admin = c.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not admin:
        pw_hash = sha256("admin123".encode()).hexdigest()
        c.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)",
            ("admin", pw_hash),
        )
    conn.commit()
    conn.close()


def navbar_html(active="home"):
    username = session.get("username", "")
    is_admin = session.get("is_admin", 0)
    initial = username[0].upper() if username else "?"
    colors = ["#007bff", "#28a745", "#dc3545", "#fd7e14", "#6f42c1", "#e83e8c", "#20c997"]
    color = colors[sum(ord(c) for c in username) % len(colors)]

    admin_item = ""
    if is_admin:
        active_cls = "active" if active == "admin" else ""
        admin_item = f"""
        <li class="nav-item">
            <a class="nav-link {active_cls}" href="/admin">
                <i class="bi bi-shield-lock me-1"></i>Admin
            </a>
        </li>"""

    home_active = "active" if active == "home" else ""

    return f"""
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/home">
                <i class="bi bi-clock-history me-2"></i>AttendanceApp
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMenu">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navMenu">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link {home_active}" href="/home">
                            <i class="bi bi-house-door me-1"></i>Home
                        </a>
                    </li>
                    {admin_item}
                </ul>
                <div class="d-flex align-items-center">
                    <div class="avatar me-2" style="background:{color};">{initial}</div>
                    <span class="text-light me-3 fw-semibold">{username}</span>
                    <a href="/logout" class="btn btn-outline-light btn-sm">
                        <i class="bi bi-box-arrow-right me-1"></i>Logout
                    </a>
                </div>
            </div>
        </div>
    </nav>
    """


# ─── Index ───

@app.route("/", methods=["GET"])
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


# ─── Login ───

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

    alert_html = ""
    if msg:
        alert_html = f"""
        <div class="alert alert-danger d-flex align-items-center" role="alert">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>{msg}
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Login - AttendanceApp</title>
        {BOOTSTRAP_HEAD}
        <style>
            .login-wrapper {{
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
        </style>
    </head>
    <body>
        <div class="login-wrapper">
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-md-5 col-lg-4">
                        <div class="text-center mb-4">
                            <div class="bg-white d-inline-flex p-3 rounded-circle mb-3" style="box-shadow:0 4px 20px rgba(0,0,0,0.15);">
                                <i class="bi bi-clock-history text-primary" style="font-size:2.5rem;"></i>
                            </div>
                            <h2 class="text-white fw-bold">AttendanceApp</h2>
                            <p class="text-white-50">Sign in to your account</p>
                        </div>
                        <div class="card">
                            <div class="card-body p-4">
                                {alert_html}
                                <form method="POST">
                                    <div class="mb-3">
                                        <label class="form-label fw-semibold">
                                            <i class="bi bi-person me-1"></i>Username
                                        </label>
                                        <input type="text" name="username" class="form-control form-control-lg" placeholder="Enter your username" required>
                                    </div>
                                    <div class="mb-4">
                                        <label class="form-label fw-semibold">
                                            <i class="bi bi-lock me-1"></i>Password
                                        </label>
                                        <input type="password" name="password" class="form-control form-control-lg" placeholder="Enter your password" required>
                                    </div>
                                    <button type="submit" class="btn btn-primary btn-lg w-100 mb-3">
                                        <i class="bi bi-box-arrow-in-right me-2"></i>Login
                                    </button>
                                </form>
                                <div class="text-center">
                                    <span class="text-muted">Don't have an account?</span>
                                    <a href="{url_for('register')}" class="fw-semibold text-decoration-none"> Register here</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {BOOTSTRAP_SCRIPTS}
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

    alert_html = ""
    if msg:
        alert_html = f"""
        <div class="alert alert-danger d-flex align-items-center" role="alert">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>{msg}
        </div>"""
    if success:
        alert_html = f"""
        <div class="alert alert-success d-flex align-items-center" role="alert">
            <i class="bi bi-check-circle-fill me-2"></i>{success}
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Register - AttendanceApp</title>
        {BOOTSTRAP_HEAD}
        <style>
            .register-wrapper {{
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
        </style>
    </head>
    <body>
        <div class="register-wrapper">
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-md-5 col-lg-4">
                        <div class="text-center mb-4">
                            <div class="bg-white d-inline-flex p-3 rounded-circle mb-3" style="box-shadow:0 4px 20px rgba(0,0,0,0.15);">
                                <i class="bi bi-person-plus text-success" style="font-size:2.5rem;"></i>
                            </div>
                            <h2 class="text-white fw-bold">Create Account</h2>
                            <p class="text-white-50">Join AttendanceApp today</p>
                        </div>
                        <div class="card">
                            <div class="card-body p-4">
                                {alert_html}
                                <form method="POST">
                                    <div class="mb-3">
                                        <label class="form-label fw-semibold">
                                            <i class="bi bi-person me-1"></i>Username
                                        </label>
                                        <input type="text" name="username" class="form-control form-control-lg" placeholder="Choose a username" required>
                                    </div>
                                    <div class="mb-4">
                                        <label class="form-label fw-semibold">
                                            <i class="bi bi-lock me-1"></i>Password
                                        </label>
                                        <input type="password" name="password" class="form-control form-control-lg" placeholder="Choose a password" required>
                                    </div>
                                    <button type="submit" class="btn btn-success btn-lg w-100 mb-3">
                                        <i class="bi bi-person-plus me-2"></i>Register
                                    </button>
                                </form>
                                <div class="text-center">
                                    <span class="text-muted">Already have an account?</span>
                                    <a href="{url_for('login')}" class="fw-semibold text-decoration-none"> Login here</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {BOOTSTRAP_SCRIPTS}
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

    conn = get_db()
    records = conn.execute(
        "SELECT name, action, date, time FROM attendance WHERE name = ? ORDER BY id DESC",
        (username,),
    ).fetchall()
    conn.close()

    rows_html = ""
    if records:
        for idx, r in enumerate(records, 1):
            badge_cls = "badge-punch-in" if r["action"] == "Punch In" else "badge-punch-out"
            icon = "bi-box-arrow-in-right" if r["action"] == "Punch In" else "bi-box-arrow-right"
            rows_html += f"""
            <tr>
                <td class="text-muted">{idx}</td>
                <td><span class="fw-semibold">{r['name']}</span></td>
                <td><span class="badge {badge_cls} px-3 py-2"><i class="bi {icon} me-1"></i>{r['action']}</span></td>
                <td><i class="bi bi-calendar3 me-1 text-muted"></i>{r['date']}</td>
                <td><i class="bi bi-clock me-1 text-muted"></i>{r['time']}</td>
            </tr>"""
    else:
        rows_html = """
        <tr>
            <td colspan="5" class="text-center text-muted py-4">
                <i class="bi bi-inbox" style="font-size:2rem;"></i>
                <p class="mb-0 mt-2">No attendance records yet. Punch in to get started!</p>
            </td>
        </tr>"""

    today = datetime.now().strftime("%A, %B %d, %Y")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Home - AttendanceApp</title>
        {BOOTSTRAP_HEAD}
        <style>body {{ background: #f0f2f5; }}</style>
    </head>
    <body>
        {navbar_html("home")}
        <div class="container">
            <!-- Welcome Card -->
            <div class="card mb-4" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="card-body p-4 text-white">
                    <div class="row align-items-center">
                        <div class="col">
                            <h3 class="fw-bold mb-1">Hello {username}!</h3>
                            <p class="mb-0 opacity-75"><i class="bi bi-calendar-event me-1"></i>{today}</p>
                        </div>
                        <div class="col-auto d-none d-md-block">
                            <i class="bi bi-hand-wave" style="font-size:3rem; opacity:0.7;"></i>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Punch Buttons -->
            <div class="row g-3 mb-4">
                <div class="col-sm-6">
                    <form method="POST" action="{url_for('punch')}">
                        <input type="hidden" name="action" value="Punch In">
                        <button type="submit" class="btn btn-success punch-btn w-100 shadow-sm">
                            <i class="bi bi-box-arrow-in-right me-2"></i>Punch In
                        </button>
                    </form>
                </div>
                <div class="col-sm-6">
                    <form method="POST" action="{url_for('punch')}">
                        <input type="hidden" name="action" value="Punch Out">
                        <button type="submit" class="btn btn-danger punch-btn w-100 shadow-sm">
                            <i class="bi bi-box-arrow-right me-2"></i>Punch Out
                        </button>
                    </form>
                </div>
            </div>

            <!-- Records Table -->
            <div class="card">
                <div class="card-header bg-white py-3">
                    <h5 class="mb-0 fw-bold"><i class="bi bi-table me-2"></i>My Attendance Records</h5>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>#</th>
                                    <th>Name</th>
                                    <th>Action</th>
                                    <th>Date</th>
                                    <th>Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        {BOOTSTRAP_SCRIPTS}
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
        if u["is_admin"]:
            role_badge = '<span class="badge bg-danger px-3 py-2"><i class="bi bi-shield-lock me-1"></i>Admin</span>'
        else:
            role_badge = '<span class="badge bg-primary px-3 py-2"><i class="bi bi-person me-1"></i>User</span>'
        initial = u["username"][0].upper()
        colors = ["#007bff", "#28a745", "#dc3545", "#fd7e14", "#6f42c1", "#e83e8c", "#20c997"]
        color = colors[sum(ord(c) for c in u["username"]) % len(colors)]
        users_html += f"""
        <tr>
            <td>{u['id']}</td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar me-2" style="background:{color}; width:36px; height:36px; font-size:0.9rem;">{initial}</div>
                    <span class="fw-semibold">{u['username']}</span>
                </div>
            </td>
            <td>{role_badge}</td>
        </tr>"""

    # Attendance table
    rows_html = ""
    if records:
        for idx, r in enumerate(records, 1):
            badge_cls = "badge-punch-in" if r["action"] == "Punch In" else "badge-punch-out"
            icon = "bi-box-arrow-in-right" if r["action"] == "Punch In" else "bi-box-arrow-right"
            rows_html += f"""
            <tr>
                <td class="text-muted">{idx}</td>
                <td><span class="fw-semibold">{r['name']}</span></td>
                <td><span class="badge {badge_cls} px-3 py-2"><i class="bi {icon} me-1"></i>{r['action']}</span></td>
                <td><i class="bi bi-calendar3 me-1 text-muted"></i>{r['date']}</td>
                <td><i class="bi bi-clock me-1 text-muted"></i>{r['time']}</td>
            </tr>"""
    else:
        rows_html = """
        <tr>
            <td colspan="5" class="text-center text-muted py-4">
                <i class="bi bi-inbox" style="font-size:2rem;"></i>
                <p class="mb-0 mt-2">No attendance records yet.</p>
            </td>
        </tr>"""

    total_users = len(users)
    total_records = len(records)

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Admin - AttendanceApp</title>
        {BOOTSTRAP_HEAD}
        <style>body {{ background: #f0f2f5; }}</style>
    </head>
    <body>
        {navbar_html("admin")}
        <div class="container">
            <!-- Stats Cards -->
            <div class="row g-3 mb-4">
                <div class="col-md-4">
                    <div class="card border-0 shadow-sm">
                        <div class="card-body d-flex align-items-center">
                            <div class="rounded-3 p-3 me-3" style="background: #e8f5e9;">
                                <i class="bi bi-people-fill text-success" style="font-size:1.5rem;"></i>
                            </div>
                            <div>
                                <div class="text-muted small">Total Users</div>
                                <div class="fw-bold fs-4">{total_users}</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card border-0 shadow-sm">
                        <div class="card-body d-flex align-items-center">
                            <div class="rounded-3 p-3 me-3" style="background: #e3f2fd;">
                                <i class="bi bi-clipboard-data-fill text-primary" style="font-size:1.5rem;"></i>
                            </div>
                            <div>
                                <div class="text-muted small">Total Records</div>
                                <div class="fw-bold fs-4">{total_records}</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card border-0 shadow-sm">
                        <div class="card-body d-flex align-items-center">
                            <div class="rounded-3 p-3 me-3" style="background: #fce4ec;">
                                <i class="bi bi-calendar-check-fill text-danger" style="font-size:1.5rem;"></i>
                            </div>
                            <div>
                                <div class="text-muted small">Today</div>
                                <div class="fw-bold fs-6">{datetime.now().strftime("%b %d, %Y")}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Registered Users -->
            <div class="card mb-4">
                <div class="card-header bg-white py-3">
                    <h5 class="mb-0 fw-bold"><i class="bi bi-people me-2"></i>Registered Users</h5>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>ID</th>
                                    <th>Username</th>
                                    <th>Role</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- All Attendance Records -->
            <div class="card mb-4">
                <div class="card-header bg-white py-3">
                    <h5 class="mb-0 fw-bold"><i class="bi bi-table me-2"></i>All Attendance Records</h5>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>#</th>
                                    <th>Name</th>
                                    <th>Action</th>
                                    <th>Date</th>
                                    <th>Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        {BOOTSTRAP_SCRIPTS}
    </body>
    </html>
    """


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
