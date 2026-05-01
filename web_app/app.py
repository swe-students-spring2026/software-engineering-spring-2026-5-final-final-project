import os
import pymongo
from flask import Flask, render_template
from dotenv import load_dotenv

from routes.tasks import tasks_bp 

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DBNAME = os.getenv('DB_NAME')

app = Flask(__name__)

connection = pymongo.MongoClient(MONGO_URI)
db = connection[MONGO_DBNAME]

tasks_bp.db = db
app.register_blueprint(tasks_bp)

@app.route('/')
def show_tasks():
    all_tasks = db.tasks.find({})
    return render_template('index.html', tasks=all_tasks)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)