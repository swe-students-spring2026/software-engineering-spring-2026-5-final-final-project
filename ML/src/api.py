from flask import Flask, jsonify, request

from filter import filter_clusters, further_filter
from split import split_query

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}


@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json()
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"error": "query is required"}), 400

    reversed_attribute, place_type = split_query(query)

    clusters = filter_clusters(reversed_attribute, place_type)
    clusters = further_filter(clusters, place_type)

    results = []
    for cluster in clusters:
        for facility in cluster.facilities:
            if len(facility) == 0:
                continue
            results.append({
                "facility_name": facility[0] if len(facility) > 0 else "Unknown",
                "facility_group": facility[1] if len(facility) > 1 else "Unknown",
                "facility_subgroup": facility[2] if len(facility) > 2 else "Unknown",
                "facility_type": facility[3] if len(facility) > 3 else "Unknown",
                "borough": facility[4] if len(facility) > 4 else "Unknown",
                "latitude": facility[5] if len(facility) > 5 else None,
                "longitude": facility[6] if len(facility) > 6 else None,
                "score": round(float(facility[-1]), 4) if len(facility) > 7 else None,
                "cluster_latitude": cluster.center[0],
                "cluster_longitude": cluster.center[1],
                "complaint_ratio": round(cluster.ratio, 4),
                "matched_complaints": cluster.matched_complaint,
                "total_complaints": cluster.total_complaint,
                "cluster_rank": cluster.rank + 1,
            })

    results.sort(
        key=lambda x: x["score"] if x["score"] is not None else 0,
        reverse=True,
    )

    return jsonify({
        "reversed_attribute": reversed_attribute,
        "place_type": place_type,
        "results": results,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
