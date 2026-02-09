import sqlite3
from datetime import datetime, timezone, timedelta

from flask import Flask, request, g

app = Flask(__name__)
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
        """CREATE TABLE IF NOT EXISTS greetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )"""
    )
    db.commit()
    db.close()


@app.route("/", methods=["GET", "POST"])
def hello():
    name = ""
    current_date = ""
    current_time = ""
    if request.method == "POST":
        name = request.form.get("name", "")
        now_ist = datetime.now(IST)
        current_date = now_ist.strftime("%Y-%m-%d")
        current_time = now_ist.strftime("%I:%M:%S %p IST")
        db = get_db()
        db.execute(
            "INSERT INTO greetings (name, date, time) VALUES (?, ?, ?)",
            (name, current_date, current_time),
        )
        db.commit()

    result_html = ""
    if name:
        result_html = f"""
        <div class="card border-0 shadow-sm mt-4">
            <div class="card-body text-center py-4">
                <h4 class="card-title text-primary mb-3">Hello, <strong>{name}</strong>!</h4>
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
        </div>
    </nav>

    <div class="container d-flex justify-content-center align-items-center" style="min-height: 80vh;">
        <div class="col-md-6 col-lg-5">
            <div class="card border-0 shadow-lg rounded-4">
                <div class="card-body p-5">
                    <h2 class="text-center fw-bold mb-2">Welcome</h2>
                    <p class="text-center text-muted mb-4">Enter your name to get a greeting with the current time</p>
                    <form method="POST">
                        <div class="mb-3">
                            <label for="name" class="form-label fw-semibold">Your Name</label>
                            <input type="text" class="form-control form-control-lg" id="name" name="name"
                                   placeholder="e.g. John Doe" value="{name}" required>
                        </div>
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary btn-lg">
                                Submit
                            </button>
                        </div>
                    </form>
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
def admin():
    db = get_db()
    rows = db.execute("SELECT id, name, date, time FROM greetings ORDER BY id DESC").fetchall()

    table_rows = ""
    for row in rows:
        table_rows += f"""
            <tr>
                <td>{row["id"]}</td>
                <td>{row["name"]}</td>
                <td>{row["date"]}</td>
                <td>{row["time"]}</td>
            </tr>"""

    if not rows:
        table_rows = """
            <tr>
                <td colspan="4" class="text-center text-muted py-4">No entries yet</td>
            </tr>"""

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
            <a href="/admin" class="btn btn-outline-light btn-sm">Admin Panel</a>
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
