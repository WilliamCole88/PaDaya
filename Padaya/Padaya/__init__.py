from flask import Flask
from .models import init_db  # your DB functions, including DB_NAME

def create_app():
    app = Flask(__name__)
    app.secret_key = "your_secret_key"

    # Initialize database
    init_db()

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    return app
