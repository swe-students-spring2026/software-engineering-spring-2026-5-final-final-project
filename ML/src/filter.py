from clustering import cluster_locations
from search import find_311_categories, find_facilities_categories
from config import PLACE_RESULTS_TOP_K


def facility_match_set(results):
    """Create a set to search from the semantic search output"""
    matched = set()

    rows = results[["facgroup", "facsubgrp", "factype"]].dropna().to_numpy()
    for facgroup, facsubgrp, factype in rows:
        matched.add(
            (
                str(facgroup).strip(),
                str(facsubgrp).strip(),
                str(factype).strip(),
            ),
        )

    return matched


def filter_clusters(query_311, query_facilities, debug=False):
    """Filter each cluster in clusters so only matched place are kept"""
    matched_311 = find_311_categories(query_311)
    clusters = cluster_locations(matched_311)

    if debug:
        print(matched_311)

    matched_facilities = find_facilities_categories(query_facilities, clusters)
    matched_facilities_set = facility_match_set(matched_facilities)

    if debug:
        print(matched_facilities)

    for c in clusters:
        filtered_facilities = []

        for facility in c.facilities:
            if len(facility) < 4:
                continue

            category = (
                str(facility[1]).strip(),
                str(facility[2]).strip(),
                str(facility[3]).strip(),
            )

            if category in matched_facilities_set:
                filtered_facilities.append(facility)

        c.facilities = filtered_facilities

        if debug:
            print(c)

            for i in c.facilities:
                print(i)

    return clusters


def further_filter(clusters, place_type, top_k=PLACE_RESULTS_TOP_K, debug=False):
    """Further filter each cluster's facilities by their names, and filter by topk matched places"""
    from search import find_facility_name_scores

    scored_facilities = find_facility_name_scores(place_type, clusters)
    scored_facilities.sort(key=lambda item: item["score"], reverse=True)
    scored_facilities = scored_facilities[:top_k]

    score_by_position = {}
    for item in scored_facilities:
        position = (item["cluster_index"], item["facility_index"])
        score_by_position[position] = item["score"]

    for cluster_index, c in enumerate(clusters):
        filtered_facilities = []

        for facility_index, facility in enumerate(c.facilities):
            score = score_by_position.get((cluster_index, facility_index))
            if score is None:
                continue

            scored_facility = list(facility)
            scored_facility.append(score)
            filtered_facilities.append(scored_facility)

        c.facilities = filtered_facilities

        if debug:
            print(c)

            for i in c.facilities:
                print(i)

    return clusters
