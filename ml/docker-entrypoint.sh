#!/bin/sh
set -eu

case "${MONGODB_URI:-}" in
  "")
    echo "MONGODB_URI is required for Docker containers. Set it to the live MongoDB connection string." >&2
    exit 1
    ;;
  mongodb://*localhost*|mongodb://*127.0.0.1*|mongodb://*0.0.0.0*|mongodb://*host.docker.internal*|mongodb://mongodb:*|mongodb://mongodb/*)
    echo "MONGODB_URI points to a local MongoDB host. Docker containers must use the live database connection string." >&2
    exit 1
    ;;
esac

exec "$@"
