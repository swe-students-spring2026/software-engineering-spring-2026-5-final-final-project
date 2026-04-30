import numpy as np
import pandas as pd

from config import PROCESSED_311_PATH, PROCESSED_FACILITIES_PATH, CLUSTER_TOPK, TOTAL_K


class Cluster:
    def __init__(self, center):
        self.center = center
        self.facilities = []
        self.matched_complaint = 0
        self.total_complaint = 0

    def __repr__(self):
        return (
            f"center={self.center}, "
            f"matched_complaint={self.matched_complaint}, "
            f"total_complaint={self.total_complaint}"
        )


def load_311_data():
    """load cleaned csv to list"""
    complaints = pd.read_csv(
        PROCESSED_311_PATH,
        usecols=["Problem", "Problem Detail", "Longitude", "Latitude"],
    ).dropna()

    complaints["Problem"] = complaints["Problem"].astype(str).str.strip()
    complaints["Problem Detail"] = complaints["Problem Detail"].astype(str).str.strip()
    complaints["Longitude"] = pd.to_numeric(complaints["Longitude"], errors="coerce")
    complaints["Latitude"] = pd.to_numeric(complaints["Latitude"], errors="coerce")
    complaints = complaints.dropna()

    data = []
    for row in complaints.to_numpy():
        data.append(list(row))
    return data

def load_facilities_data():
    """load cleaned csv to list"""
    facilities = pd.read_csv(
        PROCESSED_FACILITIES_PATH,
        usecols=["facname","facgroup","facsubgrp","factype","boro","longitude","latitude"],
    ).dropna()

    facilities["facname"] = facilities["facname"].astype(str).str.strip()
    facilities["facgroup"] = facilities["facgroup"].astype(str).str.strip()
    facilities["facsubgrp"] = facilities["facsubgrp"].astype(str).str.strip()
    facilities["factype"] = facilities["factype"].astype(str).str.strip()
    facilities["boro"] = facilities["boro"].astype(str).str.strip()
    facilities["longitude"] = pd.to_numeric(facilities["longitude"], errors="coerce")
    facilities["latitude"] = pd.to_numeric(facilities["latitude"], errors="coerce")
    facilities = facilities.dropna()

    data = []
    for row in facilities.to_numpy():
        data.append(list(row))
    return data

def dist(a, b):
    """calculate euclidean distance square"""
    total = 0
    for x, y in zip(a, b):
        total += (x - y) ** 2
    return total


def match_set(matches):
    """set a matched category set from semantic search result"""
    matched = set()

    rows = matches[["Problem", "Problem Detail"]].dropna().to_numpy()

    for p, d in rows:
        matched.add((str(p).strip(), str(d).strip()))
    return matched


def cluster_locations(matches, k=TOTAL_K, random_state=0):
    """group each points to nearest cluster, basically a 1 iteration kmeans with only matchign info"""

    data = load_311_data()

    rng = np.random.default_rng(random_state)
    indexes = rng.choice(len(data), size=k, replace=False)

    clusters = []
    for i in indexes:
        row = data[i]
        center = [row[2], row[3]]
        clusters.append(Cluster(center))

    matched = match_set(matches)

    for d in data:
        problem = d[0]
        problem_detail = d[1]
        point = [d[2], d[3]]

        closest_clus = None
        min_dist = float('inf')

        for c in clusters:
            curr_dist = dist(point, c.center)
            if curr_dist < min_dist:
                min_dist = curr_dist
                closest_clus = c

        if (problem, problem_detail) in matched:
            closest_clus.matched_complaint += 1
            closest_clus.total_complaint += 1
        else:
            closest_clus.total_complaint += 1
    clusters.sort(key=lambda c : c.matched_complaint / c.total_complaint)
    
    data = load_facilities_data()

    for d in data:
        point = [d[5], d[6]]

        closest_clus = None
        min_dist = float('inf')

        for c in clusters:
            curr_dist = dist(point, c.center)
            if curr_dist < min_dist:
                min_dist = curr_dist
                closest_clus = c

        closest_clus.facilities.append(d[:-2])

    return clusters[:CLUSTER_TOPK]
