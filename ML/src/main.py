from filter import filter_clusters
from split import split_query


def main():
    query = "I want to find a quiet place to study where it's also safe"
    (reversed_attribure, place_type) = split_query(query, debug=True)
    clusters = filter_clusters(reversed_attribure, place_type, debug=True)


if __name__ == "__main__":
    main()
