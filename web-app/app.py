from flask import Flask, render_template, request

# src directory needs to be on sys.path at runtime
# to be handled in Dockerfile
from filter import filter_clusters, further_filter
from split import split_query
from config import TOTAL_K
from db import get_cached_result, save_cached_result, health_check

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    """
    Main search page.
    User enters a 311 complaint-related query like "dangerous" or "noisy"
    and a facility query, like "study spot" or "library".
    """
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    """
    Handles submission form from index.html.
    Checks MongoDB cache first — if found, returns instantly.
    Otherwise runs full ML pipeline: split_query -> filter_clusters -> further_filter,
    saves result to MongoDB, then passes results to results.html.
    """
    query_311 = request.form.get("query_311", "").strip()
    query_facilities = request.form.get("query_facilities", "").strip()

    if not query_311 or not query_facilities:
        error = "Must enter both a complaint and facility type."
        return render_template("index.html", error=error)

    try:
        # check mongodb cache first
        cached = get_cached_result(query_311, query_facilities)

        if cached is not None:
            return render_template(
                "results.html",
                query_311=query_311,
                query_facilities=query_facilities,
                clusters=cached,
                from_cache=True,
            )

        # cache miss — run full ML pipeline
        reversed_attribute, place_type = split_query(query_facilities)
        clusters = filter_clusters(query_311, reversed_attribute)
        clusters = further_filter(clusters, place_type)

        # convert cluster objects into plain dictionaries
        # easier to use in html and to store in mongodb
        cluster_results = []

        for cluster in clusters:
            facilities = []

            for facility in cluster.facilities:
                score = facility[-1] if len(facility) > 7 else None

                facility_data = {
                    "name": facility[0] if len(facility) > 0 else "Unknown",
                    "group": facility[1] if len(facility) > 1 else "Unknown",
                    "subgroup": facility[2] if len(facility) > 2 else "Unknown",
                    "type": facility[3] if len(facility) > 3 else "Unknown",
                    "borough": facility[4] if len(facility) > 4 else "Unknown",
                    "score": round(float(score), 4) if score is not None else None,
                }

                facilities.append(facility_data)

            # sort facilities by score descending
            facilities.sort(key=lambda f: f["score"] or 0, reverse=True)

            total = cluster.total_complaint
            matched = cluster.matched_complaint

            if total > 0:
                complaint_ratio = matched / total
            else:
                complaint_ratio = 0

            cluster_results.append(
                {
                    "longitude": cluster.center[0],
                    "latitude": cluster.center[1],
                    "matched_complaints": matched,
                    "total_complaints": total,
                    "complaint_ratio": round(complaint_ratio, 4),
                    "rank": cluster.rank + 1,
                    "total_k": TOTAL_K,
                    "facilities": facilities,
                }
            )

        # save to mongodb cache for next time
        save_cached_result(query_311, query_facilities, cluster_results)

        return render_template(
            "results.html",
            query_311=query_311,
            query_facilities=query_facilities,
            clusters=cluster_results,
            from_cache=False,
        )

    except Exception as e:
        error = f"Something went wrong while processing your search: {e}"
        return render_template("index.html", error=error)


@app.route("/health", methods=["GET"])
def health():
    """
    Health check route for docker, deployment, and checking status of web app.
    Also checks MongoDB connectivity.
    """
    return {
        "status": "ok",
        "mongo": "ok" if health_check() else "unavailable",
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)