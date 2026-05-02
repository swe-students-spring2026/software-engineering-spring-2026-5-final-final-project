# CatCh

Instructions: See [instructions](./instructions.md) for details.

CatCh is a gamified programming practice platform where users solve coding problems, earn fishing chances, catch fish, collect medals, trade fish, and compete on leaderboards.

In this project, programmers are represented as **kittens**, teachers are represented as **cats**, and classrooms are represented as **fish ponds**. Instead of only completing coding problems for scores, users complete problems to unlock fishing chances. Each fishing chance gives the user an opportunity to catch a fish with a certain rarity level.

CatCh combines coding practice, classroom management, collection-based gameplay, and a player marketplace into one learning platform.

---

## Team Members

- [Celia Liang](https://github.com/liangchuxin)
- [Grace Yin](https://github.com/gy28611)
- [Hollan Yuan](https://github.com/hwyuanzi)
- [Jonas Chen](https://github.com/JonasChenJusFox)
- [Meili Liang](https://github.com/ml8397)

---

## Installation and Launch Guide

This project is a monorepo with multiple subsystems:

- `game-service`: main FastAPI backend for quiz, fishing, inventory, and gameplay APIs
- `grader-service`: Python code checking service
- `auth-service`: email verification and authentication service
- `teacher-service`: teacher and fish pond management service
- `integration`: integration layer
- `mongo`: MongoDB database
- `frontend/quiz`: quiz frontend
- `frontend/fishing`: fishing frontend

### Prerequisites

Install:

- Python 3.12
- Pipenv
- Node.js 18 or newer
- npm
- Docker Desktop
- Git

Install Pipenv if needed:

```bash
pip install pipenv
```

or:

```bash
brew install pipenv
```

### Clone the Repository

```bash
git clone <your-repository-url>
cd SWE_Final_Project
```

### Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

For local development, the default values are enough for most backend features.

Important environment variables include:

```env
DB_BACKEND=mock
MONGO_URL=mongodb://localhost:27017
MONGO_DB=fish_likes_cat
GRADER_SERVICE_URL=http://localhost:8001
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
JWT_SECRET=change-me-for-local-dev
```

---

## Option A: Run Backend Services with Docker Compose

From the project root:

```bash
docker compose up --build
```

This starts:

- MongoDB
- game-service
- grader-service
- auth-service
- teacher-service
- integration service

After startup, open:

```text
http://localhost:8000/docs
```

Useful backend URLs:

```text
game-service:      http://localhost:8000
auth-service:      http://localhost:8002
teacher-service:   http://localhost:8003
integration:       http://localhost:8004
MongoDB:           mongodb://localhost:27017
```

To stop the backend:

```bash
docker compose down
```

To remove the MongoDB volume as well:

```bash
docker compose down -v
```

---

## Option B: Run Services Locally for Development

Use separate terminal windows.

### Terminal 1: Grader Service

```bash
cd grader-service
pipenv install --dev
pipenv run uvicorn app.main:app --reload --port 8001
```

### Terminal 2: Game Service

```bash
cd game-service
pipenv install --dev
cp .env.example .env
pipenv run uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000/docs
```

### Terminal 3: Quiz Frontend

```bash
cd frontend/quiz
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

### Terminal 4: Fishing Frontend

```bash
cd frontend/fishing
npm install
npm run dev
```

Open:

```text
http://localhost:5174
```

---

## Fishing Dataset

The fish dataset is committed to the repository.

Main dataset files:

```text
data/fish_species.json
data/fish_images/
```

The dataset currently contains 50 fish species.

Each fish record includes:

- Fish name
- Species
- Rarity
- Catch probability
- Image path
- Description
- Sell value
- Marketplace eligibility

The fishing images are transparent PNG files in:

```text
data/fish_images/
```

The backend serves them through:

```text
/fish_images/<species_id>.png
```

To regenerate the fish catalog metadata:

```bash
python3 scripts/build_fish_catalog.py
```

No external dataset download is required for normal development.

---

## Quick Fishing Demo

The fishing frontend may show no available chances at first. A user must earn fishing chances by solving quiz problems.

Grant a fishing chance by submitting a correct quiz answer:

```bash
curl -X POST "http://localhost:8000/quiz/problems/leap/submit" \
  -H "Content-Type: application/json" \
  -d '{"code":"def leap_year(y): return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)","user_id":"demo_user"}'
```

Cast a fish:

```bash
curl -X POST "http://localhost:8000/fishing/cast?user_id=demo_user"
```

View inventory:

```bash
curl "http://localhost:8000/fishing/inventory/demo_user"
```

List all fish species:

```bash
curl "http://localhost:8000/fishing/species"
```

---

## Running Tests

### Game Service Tests

```bash
cd game-service
pipenv install --dev
pipenv run pytest --cov=app --cov-report=term-missing
```

### Fishing Tests Only

```bash
cd game-service
pipenv run pytest tests/test_fishing.py -v
```

### Grader Service Tests

```bash
cd grader-service
pipenv install --dev
pipenv run pytest --cov=app --cov-report=term-missing
```

---

## Frontend Build Check

### Quiz Frontend

```bash
cd frontend/quiz
npm install
npm run build
```

### Fishing Frontend

```bash
cd frontend/fishing
npm install
npm run build
```

---

## Project Overview

CatCh is designed to make programming practice more interactive and rewarding.

A kitten solves coding problems to earn fishing chances. After earning a fishing chance, the kitten can fish from a pond and catch different types of fish. Some fish are common and can be sold directly for tokens, while rare fish are more valuable and can be collected, displayed, or traded with other users.

A cat creates classrooms and coding problems. Cats cannot solve problems for fishing chances, but they can earn fishing chances by creating problems and receiving support from students on their fish ponds.

The platform includes public fish ponds, private fish ponds, a marketplace, a medal wall, wrong-answer review, pond feedback, and leaderboards.

---

## User Roles

CatCh has two main user roles:

1. **Kitten**
2. **Cat**

---

## Kitten Role

A **kitten** is a programmer or student user.

Kittens can:

- Join public fish ponds.
- Join private fish ponds using a room code.
- Solve coding problems.
- Earn fishing chances by answering problems correctly.
- Use fishing chances to catch fish.
- Review missed problems in the “Uncaught Fish” history.
- Support or not support public fish ponds.
- Sell common fish for Cat Can Tokens.
- Trade rare fish with other users.
- Collect fish medals.
- View their medal wall.
- Compete on the token leaderboard.
- Compete on the medal collection leaderboard.

Kittens are the main problem-solving users of the platform.

---

## Cat Role

A **cat** is a teacher or problem creator.

Cats can:

- Create public fish ponds.
- Create private fish ponds.
- Add coding problems to fish ponds.
- Edit coding problems.
- Delete coding problems.
- Invite students to private fish ponds using room codes.
- Earn fishing chances by creating problems.
- Earn fishing chances from support votes on their fish ponds.
- Enter the marketplace.
- Sell fish.
- Buy fish.
- Collect fish medals.
- Compete on leaderboards.

Cats cannot solve coding problems to earn fishing chances.

---

## Main Features

CatCh includes the following main features:

- Public fish ponds
- Private fish ponds
- Coding problem solving
- Judge0-based code checking
- Fishing chance system
- Fish rarity system
- Cat Can Token economy
- Fish marketplace
- Medal wall
- Wrong-answer review history
- Teacher-created classrooms
- Email-based room code invitation
- Fish pond support and not-support system
- Public fish pond ranking
- Token leaderboard
- Medal collection leaderboard

---

## Fish Ponds

In CatCh, a classroom is called a **fish pond**.

Fish ponds contain coding problems. Kittens enter fish ponds to solve problems and earn fishing chances.

There are two types of fish ponds:

1. **Public fish ponds**
2. **Private fish ponds**

Both public and private fish ponds can be created by cats.

---

## Public Fish Ponds

Public fish ponds are visible to all kitten users.

Any kitten can join a public fish pond and solve the problems inside it.

Cats can create public fish ponds. These public ponds are shown on the public fish pond page, where any kitten can view and join them.

The main public fish pond is called:

```text
CatCh Fish Pond
```

The CatCh Fish Pond is pinned at the top of the public fish pond page. It contains the platform’s main coding problem set and acts as the default public question bank.

Other public fish ponds are ranked based on student feedback.

---

## Public Fish Pond Ranking

Public fish ponds are ranked by user feedback.

Kittens can support or not support an entire public fish pond. This feedback applies to the full problem set inside the pond, not to individual questions.

The ranking score for a public fish pond is calculated as:

```text
Ranking score = number of support votes - number of not-support votes
```

Public fish ponds with higher ranking scores appear higher on the public fish pond page.

This allows useful and high-quality teacher-created problem sets to become more visible when they receive positive feedback from students.

---

## Private Fish Ponds

Private fish ponds are created by cats.

Each private fish pond has a randomly generated room code.

Cats can invite kittens by sending the room code through email. Only users with the correct room code can join the private fish pond.

Private fish ponds are useful for teachers who want to create custom problem sets for specific students or classes.

---

## Problem Solving Rules for Kittens

Each kitten can attempt a coding problem up to **5 times**.

Each attempt is checked by the system.

If the kitten submits a correct answer within 5 checks:

- The problem is marked as completed.
- The kitten earns 1 fishing chance.
- The kitten can use the fishing chance to catch a fish.

If the kitten fails after 5 checks:

- The correct answer is shown.
- The problem is added to the kitten’s “Uncaught Fish” history.
- The kitten does not earn a fishing chance.
- The kitten loses 1 Cat Can Token.

---

## Uncaught Fish

The **Uncaught Fish** page is the wrong-answer review page.

When a kitten fails a problem after all 5 attempts, that problem is saved to the Uncaught Fish history.

This page helps kittens review problems they could not solve before.

This page may include:

- The missed problem
- The correct answer
- The kitten’s previous attempts
- The problem topic
- The fish pond where the problem came from

Cats do not have an Uncaught Fish review page because cats do not solve coding problems.

---

## Code Checking

CatCh uses a Judge0-based code checking system.

When a kitten submits code, the system sends the code and test cases to the judging service. The judging service runs the code and returns the result.

The platform then decides whether the answer is correct.

Possible results may include:

- Correct answer
- Wrong answer
- Runtime error
- Compilation error
- Time limit exceeded

Only correct answers allow kittens to earn fishing chances.

---

## Fishing Chance System

Fishing chances are earned through learning actions.

Kittens earn fishing chances by solving coding problems correctly.

Cats earn fishing chances by creating coding problems.

One fishing chance allows the user to fish one time.

```text
1 fishing chance = 1 fishing attempt
```

Fishing attempts can produce fish with different rarity levels.

---

## Fish Rarity System

Different fish have different rarity levels.

Example rarity levels include:

- Common
- Uncommon
- Rare
- Epic
- Legendary

Common fish are easier to catch.

Legendary fish are much harder to catch.

Each fish type has its own probability. The rarer the fish, the lower the chance of catching it.

Example probability structure:

- Common: 60%
- Uncommon: 25%
- Rare: 10%
- Epic: 4%
- Legendary: 1%

These numbers can be adjusted in the project configuration.

---

## Cat Can Tokens

The in-game currency is called **Cat Can Token**.

Cat Can Tokens are used for marketplace trading and teacher classroom creation.

Users can use Cat Can Tokens to:

- Buy fish from other users.
- Sell common fish.
- Create additional fish ponds.
- Trade rare fish.
- Build their collection.

Kittens can lose Cat Can Tokens if they fail a coding problem after all 5 attempts.

Cats can lose Cat Can Tokens if their fish ponds remain inactive or if their fish ponds receive too much negative feedback.

---

## Fish Selling Rules

Fish can be sold in two main ways:

1. Direct sale to the system market
2. Player-to-player marketplace sale

Low-level fish can be sold directly to the system market for Cat Can Tokens.

High-level fish cannot be sold directly to the system market. They must be traded between users in the marketplace.

This makes rare fish more valuable because their price depends on user demand.

---

## Marketplace

The marketplace is open to both kittens and cats.

Users can enter the marketplace to buy and sell fish.

In the marketplace, users can:

- List fish for sale.
- Set a price in Cat Can Tokens.
- Buy fish from other users.
- Remove their own listings.
- View available fish.
- Filter fish by rarity.
- Filter fish by price.
- Filter fish by species.

The marketplace creates a player-driven economy around rare fish collection.

---

## Medal Wall

Each user has a medal wall.

When a user catches a new fish species, the medal for that fish is unlocked.

The medal wall shows the user’s fish collection progress.

The medal wall may display:

- Fish already collected
- Fish not yet collected
- Fish rarity
- Collection percentage
- Recently unlocked medals

The medal wall encourages users to keep solving problems, fishing, and trading.

---

## Medal Collection Progress

Each fish species counts toward collection progress.

For example, if the platform has 100 fish species and a user has collected 25 unique species, the user’s collection progress is **25%**.

The medal collection percentage is used for the medal collection leaderboard.

---

## Leaderboards

CatCh has two main leaderboards:

1. Token leaderboard
2. Medal collection leaderboard

---

## Token Leaderboard

The token leaderboard ranks users by the number of Cat Can Tokens they own.

Users with more Cat Can Tokens appear higher on the leaderboard.

This leaderboard rewards users who solve problems, sell fish, trade well, and manage their resources carefully.

---

## Medal Collection Leaderboard

The medal collection leaderboard ranks users by their fish collection progress.

Users who collect more unique fish species appear higher on the leaderboard.

This leaderboard rewards long-term participation and collection progress.

---

## Teacher Fish Pond Rules

Cats can create and manage fish ponds.

Each cat receives **1 free fish pond creation chance**.

After the free fish pond is used, each additional fish pond costs **50 Cat Can Tokens**.

Each fish pond can contain up to **100 problems**.

Cats can edit, add, or remove problems from their fish ponds.

Cats can create both public and private fish ponds.

Public fish ponds created by cats can receive support and not-support votes from kittens.

---

## Teacher Problem Creation Rules

Cats earn fishing chances by creating coding problems.

For every coding problem created, the cat earns **1 fishing chance**.

This gives teachers a way to participate in the collection system without solving student problems.

---

## Teacher Activity Rules

If a fish pond has fewer than 100 problems, the cat must continue adding problems to keep the pond active.

If a fish pond has fewer than 100 problems and the cat does not create a new problem in that pond for more than **10 days**, the cat loses **1 Cat Can Token**.

If a fish pond already contains 100 problems, this 10-day activity rule no longer applies.

This rule encourages teachers to keep incomplete fish ponds active.

---

## Fish Pond Feedback Rules

Kittens can give feedback to an entire public fish pond.

A kitten can either support or not support a public fish pond.

This feedback applies to the pond as a whole, not to individual questions.

For every 10 support votes received by a cat’s fish ponds, the cat earns **1 fishing chance**.

For every 10 not-support votes received by a cat’s fish ponds, the cat loses **1 Cat Can Token**.

This feedback system rewards useful fish ponds, discourages low-quality problem sets, and helps better public ponds appear higher in the public fish pond list.

---

## Login and Email Verification

CatCh uses email-based login verification.

When a user logs in or registers, the system sends a verification email using SMTP.

This helps confirm that the user owns the email address.

Email is also used for private fish pond invitations. When a cat creates a private fish pond, the cat can send the room code to students through email.

---

## Example Kitten Gameplay Flow

A kitten enters the platform and joins the public CatCh Fish Pond.

The kitten chooses a coding problem.

The kitten submits code for the problem.

The system checks the code using the judging service.

If the answer is correct, the kitten earns one fishing chance.

The kitten uses the fishing chance to fish from the pond.

The kitten catches a fish.

If the fish is common, the kitten can sell it for Cat Can Tokens.

If the fish is rare, the kitten can keep it for the medal wall or list it in the marketplace.

The kitten can also support or not support the public fish pond based on the quality of the problem set.

The kitten’s medal wall and leaderboard ranking are updated.

---

## Example Cat Gameplay Flow

A cat creates a private fish pond for a class.

The system generates a random room code.

The cat sends the room code to students through email.

The cat creates coding problems inside the fish pond.

For each problem created, the cat earns one fishing chance.

Kittens join the pond, solve problems, and may give feedback to the pond.

If the cat’s ponds receive enough support votes, the cat earns extra fishing chances.

If the cat’s ponds receive too many not-support votes, the cat loses Cat Can Tokens.

---

## Core Game Rules Summary

### Kitten Rules

- Correctly solve 1 problem = earn 1 fishing chance
- 1 fishing chance = 1 fishing attempt
- Each problem has 5 check attempts
- Failing after 5 attempts = no fishing chance
- Failing after 5 attempts = lose 1 Cat Can Token
- Failed problems are saved to Uncaught Fish history
- Kittens can support or not support public fish ponds

### Cat Rules

- Create 1 problem = earn 1 fishing chance
- Cats can create both public and private fish ponds
- First fish pond creation = free
- Each additional fish pond = 50 Cat Can Tokens
- Each fish pond can contain up to 100 problems
- Public fish ponds are ranked by support votes minus not-support votes
- Inactive unfinished pond after 10 days = lose 1 Cat Can Token
- Full pond with 100 problems = no 10-day activity penalty
- 10 support votes on the cat’s fish ponds = earn 1 fishing chance
- 10 not-support votes on the cat’s fish ponds = lose 1 Cat Can Token

### Public Pond Ranking Rules

- Ranking score = support votes - not-support votes
- Higher ranking score = higher position on the public fish pond page
- The CatCh Fish Pond is pinned at the top as the default public pond
- Other public ponds are sorted by ranking score

### Marketplace Rules

- Common fish can be sold directly for Cat Can Tokens
- Rare fish must be traded between users
- Both kittens and cats can use the marketplace
- Users can list, buy, and sell fish

### Medal Rules

- Catching a new fish species unlocks its medal
- Medal wall records collection progress
- Collection progress affects the medal collection leaderboard