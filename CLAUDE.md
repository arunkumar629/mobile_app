# CLAUDE.md

## Project Overview

Flask web application with Google SSO authentication. Users must sign in with Google to access the home page.

## Running the App

```bash
pip install -r requirements.txt
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export SECRET_KEY="your-secret-key"
python app.py
```

The app runs on `http://0.0.0.0:80`.

## Project Structure

- `app.py` - Main Flask application with Google SSO, SQLite DB, and route protection
- `templates/` - HTML templates (base, login, register, home)
- `requirements.txt` - Python dependencies
- `app.db` - SQLite database (auto-created on first run)
- `README.md` - Project documentation
