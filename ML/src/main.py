from clustering import cluster_locations
from search import find_categories


def main():
    matches = find_categories("noise")
    print("Matched categories:")
    print(matches)

    clusters = cluster_locations(matches)
    print("Clusters:")

    for c in clusters:
        print(c)


if __name__ == "__main__":
    main()
