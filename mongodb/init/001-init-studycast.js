db = db.getSiblingDB("studycast");

db.createCollection("users");
db.createCollection("todos");
db.createCollection("exams");
db.createCollection("preparations");
db.createCollection("study_sessions");

db.users.createIndex({ email: 1 }, { unique: true });
db.exams.createIndex({ exam_date: 1 });
db.preparations.createIndex({ preparation_date: 1 });
db.study_sessions.createIndex({ user: 1, started_at: -1 });
