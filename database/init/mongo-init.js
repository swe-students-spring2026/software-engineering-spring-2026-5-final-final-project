// Runs once on first container start with an empty data directory.
// Creates all four collections with JSON Schema validators and indexes.

db = db.getSiblingDB(process.env.MONGO_INITDB_DATABASE || "pennywise");

// ── Users ─────────────────────────────────────────────────────────────────
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["username", "email", "created_at"],
      additionalProperties: true,
      properties: {
        username:   { bsonType: "string", minLength: 3, maxLength: 50 },
        email:      { bsonType: "string" },
        created_at: { bsonType: "string" }
      }
    }
  },
  validationAction: "warn",
  validationLevel: "moderate"
});

db.users.createIndex({ username: 1 }, { unique: true });
db.users.createIndex({ email: 1 },    { unique: true });

// ── Transactions ──────────────────────────────────────────────────────────
db.createCollection("transactions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["type", "amount", "category", "date"],
      additionalProperties: true,
      properties: {
        type:        { bsonType: "string", enum: ["income", "expense"] },
        amount:      { bsonType: "double", minimum: 0 },
        category:    { bsonType: "string" },
        date:        { bsonType: "string" },
        description: { bsonType: "string" }
      }
    }
  },
  validationAction: "warn",
  validationLevel: "moderate"
});

db.transactions.createIndex({ date: -1 });
db.transactions.createIndex({ user_id: 1, date: -1 });
db.transactions.createIndex({ category: 1, date: -1 });
db.transactions.createIndex({ user_id: 1, category: 1, date: -1 });

// ── Budgets ───────────────────────────────────────────────────────────────
db.createCollection("budgets", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["category", "limit", "month"],
      additionalProperties: true,
      properties: {
        category: { bsonType: "string" },
        limit:    { bsonType: "double", minimum: 0 },
        month:    { bsonType: "string", pattern: "^\\d{4}-\\d{2}$" }
      }
    }
  },
  validationAction: "warn",
  validationLevel: "moderate"
});

db.budgets.createIndex({ month: 1, category: 1 }, { unique: true });
db.budgets.createIndex({ user_id: 1, month: 1 });

// ── Categories ────────────────────────────────────────────────────────────
db.createCollection("categories");
db.categories.createIndex({ name: 1 }, { unique: true });
