from flask import Flask, render_template, request

import os
from datetime import datetime

from werkzeug.utils import secure_filename
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/topfive"))
db = client["topfive"]


def allowed_video(filename): #Ensures only videos are able to be chosen 
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/test-db")
def test_db():
    db.test.insert_one({"msg": "hello"})
    return "inserted into DB!"

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        video = request.files.get("video")
        prompt = request.form.get("prompt")
        num_clips = request.form.get("num_clips")

        if not video or video.filename == "":
            return render_template("upload.html", error="Please upload a video.")

        if not allowed_video(video.filename):
            return render_template("upload.html", error="Only video files are allowed.")

        filename = secure_filename(video.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        video.save(filepath)

        db.videos.insert_one({
            "filename": filename,
            "filepath": filepath,
            "prompt": prompt,
            "num_clips": num_clips,
            "uploaded_at": datetime.utcnow()
        })

        return render_template(
            "upload.html",
            filename=filename,
            prompt=prompt,
            num_clips=num_clips
        )

    return render_template("upload.html")

if __name__ == "__main__":
    app.run(debug=True, port=3000)


# python -m pipenv run python app.py