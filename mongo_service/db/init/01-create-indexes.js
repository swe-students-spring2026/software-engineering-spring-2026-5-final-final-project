const dbName = process.env.MONGO_INITDB_DATABASE || process.env.MONGODB_DB_NAME || 'stocks_app';
const target = db.getSiblingDB(dbName);

target.createCollection('tickers');
target.createCollection('sessions');

target.tickers.createIndex({ Ticker: 1 }, { unique: true });
target.sessions.createIndex({ run: 1 });
