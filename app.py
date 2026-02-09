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

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Greeting App</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: #f0f2f5;
        }}
        .container {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        h1 {{
            color: #333;
        }}
        input[type="text"] {{
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ccc;
            border-radius: 4px;
            width: 250px;
        }}
        button {{
            padding: 10px 20px;
            font-size: 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 8px;
        }}
        button:hover {{
            background: #0056b3;
        }}
        .result {{
            margin-top: 1.5rem;
            font-size: 18px;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Greeting App</h1>
        <form method="POST">
            <input type="text" name="name" placeholder="Enter your name" value="{name}" required>
            <button type="submit">Submit</button>
        </form>
        {"<div class='result'><p>Hello, <strong>" + name + "</strong>!</p><p>Current time: " + current_time + "</p></div>" if name else ""}
    </div>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
