import os
import pymongo
from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager
from bson.objectid import ObjectId
from routes.auth import User, auth_bp
from routes.tasks import tasks_bp 

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DBNAME = os.getenv('DB_NAME')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

connection = pymongo.MongoClient(MONGO_URI)
db = connection[MONGO_DBNAME]

tasks_bp.db = db
auth_bp.db = db
app.register_blueprint(tasks_bp)
app.register_blueprint(auth_bp)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({"_id": ObjectId(user_id)})
    return User(user_data) if user_data else None

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)