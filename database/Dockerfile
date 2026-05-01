FROM mongo:7.0

COPY init/mongo-init.js /docker-entrypoint-initdb.d/mongo-init.js

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD mongosh --quiet --eval "db.adminCommand('ping')" || exit 1

EXPOSE 27017
