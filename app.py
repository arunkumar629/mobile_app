from datetime import datetime

from flask import Flask, request

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def hello():
    name = ""
    current_time = ""
    if request.method == "POST":
        name = request.form.get("name", "")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
                    {current_time}
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
            <span class="navbar-brand fw-bold">Greeting App</span>
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
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
