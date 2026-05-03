# Final Project

An exercise to put to practice software development teamwork, subsystem communication, containers, deployment, and CI/CD pipelines. See [instructions](./instructions.md) for details.

## Frontend Features

1. Users can enter four favorite movies to receive personalized movie recommendations.
2. The application generates recommendation results based on cosine similarity.
3. Users can search directly by movie title.
4. Users can make natural-language semantic searches, such as describing the type of movie they want to watch.
5. Each movie has a detail page with key information such as title, description, genre, year, rating, director, and cast.
6. Movie detail pages can display similar movie recommendations.
7. Users can save movies to a personal watchlist.
8. Recommendation history is stored in MongoDB for later retrieval.
9. A simple analytics dashboard summarizes recommendation and search activity.

## Description

CineMatch is a movie recommendation web app that learns your taste from just four films. Tell us your four all-time favourite movies and we'll offer a personalised list of films you're likely to love — powered by cosine similarity over pre-computed semantic embeddings from a dataset of one million movies.

You can also search the catalogue in two ways: type a title like "Gladiator" for a direct lookup, or describe what you're in the mood for — "a slow-burn psychological thriller like Christopher Nolan" — and the semantic search engine will find the closest matches based on meaning, not just keywords.
