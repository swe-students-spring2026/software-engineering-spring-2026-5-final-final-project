from flask import Flask, render_template, request

from filter import filter_clusters, further_filter
from split import split_query
from db import get_cached_result, save_cached_result, health_check


app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    user_query = request.form.get("query", "").strip()

    if not user_query:
        return render_template(
            "index.html",
            error="Please enter a search query.",
        )

    try:
        cache_type = "natural_language"

        cached = get_cached_result(user_query, cache_type)

        if cached is not None:
            return render_template(
                "results.html",
                user_query=cached["user_query"],
                reversed_attribute=cached["reversed_attribute"],
                place_type=cached["place_type"],
                results=cached["results"],
                from_cache=True,
            )

        reversed_attribute, place_type = split_query(user_query, debug=False)

        clusters = filter_clusters(
            reversed_attribute,
            place_type,
            debug=False,
        )

        clusters = further_filter(
            clusters,
            place_type,
            debug=False,
        )

        results = []

        for cluster in clusters:
            for facility in cluster.facilities:
                if len(facility) == 0:
                    continue

                result = {
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
                }

                results.append(result)

        results.sort(
            key=lambda item: item["score"] if item["score"] is not None else 0,
            reverse=True,
        )

        cache_payload = {
            "user_query": user_query,
            "reversed_attribute": reversed_attribute,
            "place_type": place_type,
            "results": results,
        }

        save_cached_result(user_query, cache_type, cache_payload)

        return render_template(
            "results.html",
            user_query=user_query,
            reversed_attribute=reversed_attribute,
            place_type=place_type,
            results=results,
            from_cache=False,
        )

    except Exception as e:
        return render_template(
            "index.html",
            error=f"Something went wrong while processing your search: {e}",
        )


@app.route("/health", methods=["GET"])
def health():
    return {
        "status": "ok",
        "mongo": "ok" if health_check() else "unavailable",
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)