import os
import secrets
from flask import Flask, render_template, request, session
from dotenv import load_dotenv
from pymongo import MongoClient
load_dotenv()
app = Flask(__name__)

mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client[os.getenv("MONGO_DB_NAME")]
clips_collection = db["clips"]
# MONGO_URI = mongodb+srv://<username>:<db_password>@clips.rhosezz.mongodb.net/?appName=Clips
# MONGO_DB_NAME = clips
app.secret_key = os.getenv("SECRET_KEY")
# SECRET_KEY = generate string with {python -c "import secrets; print(secrets.token_hex(32))"}
# set SECRET_KEY in your local for testing --> when deployed the server must use one unversal shared key

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}

def allowed_video(filename): #Ensures only videos are able to be chosen 
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("index.html")

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

        if "user_id" not in session:
            session["user_id"] = secrets.token_hex(16)

        file_data = video.read()

        # TODO: use AI to derive an array of clips
        ai_clips = []  # placeholde

        stored_clips = []
        for clip in ai_clips:
            doc = {
                "user_id": session["user_id"],
                "filename": video.filename,
                "prompt": prompt,
                "video": clip["data"],
                "rating": clip["rating"],
                "length": clip["length"],
            }
            result = clips_collection.insert_one(doc)
            stored_clips.append({
                "id": str(result.inserted_id),
                "rating": clip["rating"],
                "length": clip["length"],
            })

        return render_template(
            "upload.html",
            filename=video.filename,
            prompt=prompt,
            num_clips=num_clips,
            clips=stored_clips
        )

    return render_template("upload.html")

if __name__ == "__main__":
    app.run(debug=True, port=3000)


# python -m pipenv run python app.py