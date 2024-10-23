from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os

db = SQLAlchemy()
migrate = Migrate()




UPLOAD_FOLDER = 'uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")

    #postgresql://amolnil:grpSdeJWu2d6YQ4Dfzaf2eLRw5fiiPit@dpg-csb9olu8ii6s7384led0-a/consultancy_s7xs

    # postgresql://amolnil:hCdMUqgxI7y6cmzqV3MccNNBSWWKa3ts@dpg-csbucnhu0jms73filge0-a/consultancydb
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)

    from .routes import main
    app.register_blueprint(main)
    app.secret_key = os.urandom(24)

    return app
