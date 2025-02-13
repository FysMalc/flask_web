from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
    app.config['OUTPUT_FOLDER'].mkdir(parents=True, exist_ok=True)

    from app.routes import main
    app.register_blueprint(main)

    return app
