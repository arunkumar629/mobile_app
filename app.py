import os
from flask import Flask, redirect, url_for, render_template, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Database config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'app.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Login manager
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ── Models ──────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    name = db.Column(db.String(256))

class OAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_user_id = db.Column(db.String(256), nullable=False)
    token = db.Column(db.JSON, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ── Google OAuth blueprint ──────────────────────────────────────────────────

google_bp = make_google_blueprint(
    client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email",
           "https://www.googleapis.com/auth/userinfo.profile"],
    storage=SQLAlchemyStorage(OAuth, db.session, user=current_user),
    redirect_url="/google-login/callback",
)
app.register_blueprint(google_bp, url_prefix="/google-login")

# Handle the OAuth authorized signal – create or log in the user
@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    if not token:
        flash("Failed to sign in with Google.", "danger")
        return False

    resp = blueprint.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return False

    info = resp.json()
    google_user_id = info["id"]
    email = info.get("email", "")
    name = info.get("name", "")

    # Find existing OAuth record
    oauth_entry = OAuth.query.filter_by(provider="google", provider_user_id=google_user_id).first()

    if oauth_entry:
        # Existing user – update token
        oauth_entry.token = token
        user = oauth_entry.user
    else:
        # Check if a user with this email already exists
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, name=name)
            db.session.add(user)
            db.session.flush()

        oauth_entry = OAuth(provider="google", provider_user_id=google_user_id,
                            token=token, user_id=user.id)
        db.session.add(oauth_entry)

    db.session.commit()
    login_user(user)
    flash(f"Welcome, {user.name or user.email}!", "success")

    # Return False so Flask-Dance doesn't try to store the token again
    return False

# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def hello():
    return render_template("home.html", user=current_user)

@app.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("hello"))
    return render_template("login.html")

@app.route("/register")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("hello"))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# ── Bootstrap DB ────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
