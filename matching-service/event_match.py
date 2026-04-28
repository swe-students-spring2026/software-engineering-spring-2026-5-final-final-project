import math
from typing import List, Tuple


def compute_match_score(user, event) -> float:
    """
    Calculates match score between a user and an event.

    user = {
        "age": int,
        "interests": List[str],
        "location": (lat, lon),
        "preferred_group_ranges": List[(min, max)]
    }

    event = {
        "interests": List[str],
        "location": (lat, lon),
        "members": List[user]
    }
    """

    # Event Score

    interest_event = list_similarity(user["interests"], event["interests"])
    dist_score = distance_score(user["location"], event["location"])



    event_score = (
        0.6 * interest_event +
        0.4 * dist_score
    )

    # Group Score

    members = event["members"]

    interest_group = sum(
        list_similarity(user["interests"], m["interests"])
        for m in members
    ) / len(members)

    group_ages = [m["age"] for m in members]
    age_comp = age_score(user["age"], group_ages)

    group_score = (
        0.5 * interest_group +
        0.5 * age_comp
    )

    # Size Score

    ranges = user.get("preferred_group_ranges", [(3, 10)])
    event_size = len(event["members"]) + 1
    size_score1 = size_score(event_size, ranges)

    # Final Score

    final_score = 0.3 * event_score + 0.5 * group_score + 0.3 * size_score1

    return final_score


def list_similarity(a: List[str], b: List[str]) -> float:
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 1.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def haversine_distance_km(loc1: Tuple[float, float], loc2: Tuple[float, float]) -> float:
    lat1, lon1 = loc1
    lat2, lon2 = loc2

    R = 6371 #Radius of earth

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2)**2 + \
        math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def distance_score(user_loc, event_loc) -> float:
    d = haversine_distance_km(user_loc, event_loc)
    d = min(d, 50)
    return math.exp(-d / 10)


def distance_to_range(n: int, r_min: int, r_max: int) -> int:
    if r_min <= n <= r_max:
        return 0
    return min(abs(n - r_min), abs(n - r_max))


def size_score(n: int, ranges: List[Tuple[int, int]]) -> float:
    if not ranges:
        return 0.5

    best_distance = min(distance_to_range(n, r[0], r[1]) for r in ranges)
    return math.exp(-best_distance / 3)


def age_score(user_age: int, group_ages: List[int]) -> float:
    mean = sum(group_ages) / len(group_ages)
    variance = sum((a - mean) ** 2 for a in group_ages) / len(group_ages)
    std = math.sqrt(variance)

    return math.exp(-((user_age - mean) ** 2) / (2 * (std ** 2 + 4)))
