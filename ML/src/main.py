from filter import filter_clusters, further_filter
from split import split_query
from config import TOTAL_K


def main():
    my_debug = False
    query = "a quiet place to study where it's also safe"
    reversed_attribure, place_type = split_query(query, debug=my_debug)
    clusters = further_filter(
        filter_clusters(reversed_attribure, place_type, debug=my_debug),
        place_type,
        debug=my_debug,
    )
    results = []

    for c in clusters:
        for facility in c.facilities:
            if len(facility) == 0:
                continue

            score = facility[-1]
            results.append((score, facility, c))

    results.sort(key=lambda item: item[0], reverse=True)

    for score, facility, cluster in results:
        print("Facility")
        print(f"  Facility name: {facility[0]}")
        print(f"  Facility Group: {facility[1]}")
        print(f"  Facility Subgroup: {facility[2]}")
        print(f"  Facility Type: {facility[3]}")
        print(f"  Borough: {facility[4]}")
        print(f"  Location: {facility[5]}, {facility[6]}")

        print(f"  score: {score}")
        print("Cluster")
        print(f"  Matched Complaints Ratio: {cluster.ratio}")
        print(f"  Cluster Rank: {cluster.rank + 1}/{TOTAL_K}")
        print()


if __name__ == "__main__":
    main()
