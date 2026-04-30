from clustering import cluster_locations
from search import find_311_categories, find_facilities_categories


def facility_match_set(results):
    """create a set to search from the semantic search output"""
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


def filter_clusters(query_311, query_facilities):
    """filter each cluster in clusters so only matched place are kept"""
    matched_311 = find_311_categories(query_311)
    clusters = cluster_locations(matched_311)

    print(matched_311)

    matched_facilities = find_facilities_categories(query_facilities, clusters)
    matched_facilities_set = facility_match_set(matched_facilities)

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

        print(c)

        for i in range(5):
            print(c.facilities[i])

    return clusters
