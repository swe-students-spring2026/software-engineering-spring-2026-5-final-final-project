from flask import Flask, render_template, request

#src directory needs to be on sys.path at runtime
#to be handled in Dockerfile
from filter import filter_clusters

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    """
    main search page
    user enters a 311 complaint-related query like "dangerous" or "noisy"
    and a facility query, like "study spot" or "library"
    """
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    """
    handles submission form from index.html
    sends user input into filter.clusters(),
    then passes results to results.html()
    so front end can display
    """
    query_311 = request.form.get("query_311", "").strip()
    query_facilities = request.form.get("query_facilities", "").strip()

    if not query_311 or not query_facilities:
        error = "Must enter both a complaint and facility type."
        return render_template("index.html", error=error)
    try:
        clusters = filter_clusters(query_311, query_facilities)
        #conver cluster objects into plain dictionaries
        #easier to use in html
        cluster_results = []

        for cluster in clusters:
            facilities = []

            for facility in cluster.facilities:

                facility_data = {
                    "name": facility[0] if len(facility) > 0 else "Unknown",
                    "group": facility[1] if len(facility) > 1 else "Unknown",
                    "subgroup": facility[2] if len(facility) > 2 else "Unknown",
                    "type": facility[3] if len(facility) > 3 else "Unknown",
                    "borough": facility[4] if len(facility) > 4 else "Unknown",
                }

                facilities.append(facility_data)

            total = cluster.total_complaint
            matched = cluster.matched_complaint

            if total > 0:
                complaint_ratio = matched/total
            else:
                complaint_ratio = 0

            cluster_results.append(
                {
                    "longitude": cluster.center[0],
                    "latitude": cluster.center[1],
                    "matched_complaints": matched,
                    "total_complaints": total,
                    "complaint_ratio": round(complaint_ratio, 4),
                    "facilities": facilities,
                }
            )
        return render_template(
            "results.html",
            query_311=query_311,
            query_facilities=query_facilities,
            clusters=cluster_results,
        )
    except Exception as e:
        error = f"Something went wrong while processing your search: {e}"
        return render_template("index.html", error=error)

@app.route("/health", methods=["GET"])
def health():
    """
    health check route for docker, deployment, and checking status of web app
    """
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 