# Database

MongoDB database for the SplitRing Splitwise clone. Tracks users, friendships, expenses, and settlement payments. Balances are **derived** at query time from `expenses` and `payments` rather than stored, keeping writes simple and avoiding cache invalidation bugs.

## Running

The MongoDB server itself runs from the official `mongo` image (no custom Dockerfile needed for it). The `Dockerfile` in this folder is for a small one-shot **init container** that creates collections and indexes.

From the project root:

```bash
docker compose up --build
```

This brings up `mongodb`, then runs `db-init` once (which creates collections + indexes and exits), then starts `web-app` and `backend`.


## Environment variables

| Variable | Purpose |
| --- | --- |
| `MONGO_URI` | Full Mongo connection string used by every service |
| `MONGO_DBNAME` | Database name (default `splitring`) |

See `.env.example` at the repo root.

## Collections

### `users`

User accounts.

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | ObjectId | Primary key |
| `username` | string | Unique, used for login |
| `password_hash` | string | werkzeug-hashed password |
| `full_name` | string | Display name |
| `email` | string | Unique, sparse (optional) |
| `created_at` | datetime | UTC |

Indexes: `username` (unique), `email` (unique, sparse).

### `friendships`

Pairwise friendship records. Each pair is stored **once** with `user1_id` always being the lexicographically smaller ObjectId — this prevents `(A, B)` and `(B, A)` duplicates and is what the unique compound index enforces.

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | ObjectId | Primary key |
| `user1_id` | ObjectId | Smaller of the two user IDs |
| `user2_id` | ObjectId | Larger of the two user IDs |
| `status` | string | `pending` or `accepted` |
| `requested_by` | ObjectId | Who sent the friend request |
| `requested_at` | datetime | UTC |
| `accepted_at` | datetime | UTC, null until accepted |

Indexes: `(user1_id, user2_id)` unique, `user1_id`, `user2_id`, `status`.

### `expenses`

Each row represents one bill where one friend paid and the other owes a share. Even-split is just `amount_owed = total_amount / 2`, but the schema also supports uneven splits.

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | ObjectId | Primary key |
| `payer_id` | ObjectId | Who paid the bill |
| `debtor_id` | ObjectId | The friend who owes a share |
| `total_amount` | number | Total bill (for display) |
| `amount_owed` | number | What `debtor_id` owes `payer_id` |
| `description` | string | e.g. "Dinner at Joe's" |
| `category` | string | e.g. `food`, `transport`, `rent` |
| `date` | datetime | When the expense happened |
| `created_at` | datetime | When the row was inserted |
| `created_by` | ObjectId | User who logged the expense |

Indexes: `payer_id`, `debtor_id`, `(payer_id, debtor_id)`, `date`, `created_at` desc.

### `payments`

Settlement records — one friend paying the other back outside the app (Venmo, cash, etc.). Subtracted from the running balance.

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | ObjectId | Primary key |
| `from_user_id` | ObjectId | Who paid |
| `to_user_id` | ObjectId | Who received |
| `amount` | number | Amount paid |
| `note` | string | Optional |
| `date` | datetime | When the settlement happened |
| `created_at` | datetime | When the row was inserted |

Indexes: `from_user_id`, `to_user_id`, `date`, `created_at` desc.