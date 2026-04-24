import os

from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ["MONGO_DB_NAME"]]


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "apis"})


@app.get("/classes")
def get_classes():
    term      = request.args.get("term")
    q         = request.args.get("q")
    school    = request.args.get("school")
    component = request.args.get("component")
    mode      = request.args.get("mode")
    campus    = request.args.get("campus")

    query = {}
    if term:
        query["term.code"] = term
    if school:
        query["school"] = {"$regex": school, "$options": "i"}
    if component:
        query["component"] = {"$regex": component, "$options": "i"}
    if mode:
        query["_details_raw.instructional_method"] = {"$regex": mode, "$options": "i"}
    if campus:
        query["_details_raw.campus_location"] = {"$regex": campus, "$options": "i"}
    if q:
        query["$or"] = [
            {"title":        {"$regex": q, "$options": "i"}},
            {"code":         {"$regex": q, "$options": "i"}},
            {"subject_code": {"$regex": q, "$options": "i"}},
            {"instructor":   {"$regex": q, "$options": "i"}},
        ]

    classes = list(db.classes.aggregate([
        {"$match": query},
        {"$set": {
            "clssnotes":           "$_details_raw.clssnotes",
            "instructional_method": "$_details_raw.instructional_method",
            "campus_location":     "$_details_raw.campus_location",
        }},
        {"$unset": ["_id", "_details_raw"]},
    ]))
    return jsonify(classes)


@app.get("/classes/schools")
def get_schools():
    schools = db.classes.distinct("school")
    return jsonify(sorted(s for s in schools if s))


@app.get("/classes/campuses")
def get_campuses():
    campuses = db.classes.distinct("_details_raw.campus_location")
    return jsonify(sorted(c for c in campuses if c))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ["API_INTERNAL_PORT"]))
