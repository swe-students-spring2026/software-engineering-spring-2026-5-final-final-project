This directory contains the Python web application subsystem.

## Routes

- [`GET /`](./app.py) - `home` page
- [`GET, POST /login`](./app.py) - `login` page
- [`GET, POST /register`](./app.py) - `register` page
- [`GET, POST /setup`](./app.py) - `setup` profile details and puzzle-answer editor
- [`GET, POST /dashboard`](./app.py) - `dashboard` daily challenge page
- [`GET /matches`](./app.py) - `matches_page` matched users list
- [`GET /matches/<match_id>`](./app.py) - `match_detail` matched user details
- [`GET, POST /profile`](./app.py) - `profile` compatibility redirect to settings
- [`GET, POST /setting`](./app.py) - `settings` account and profile settings
- [`GET, POST /settings`](./app.py) - `settings` compatibility alias
- [`GET, POST /setting/puzzle-questions`](./app.py) - `puzzle_questions` compatibility redirect to setup
- [`GET, POST /settings/puzzle-questions`](./app.py) - `puzzle_questions` compatibility redirect to setup
- [`GET /users/<user_id>/profile-image`](./app.py) - `profile_image` MongoDB-backed profile image
- [`GET /logout`](./app.py) - `logout` clear session and return to login
