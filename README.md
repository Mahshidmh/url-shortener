# URL Shortener API

[![CI](https://github.com/Mahshidmh/url-shortener/actions/workflows/ci.yml/badge.svg)](https://github.com/Mahshidmh/url-shortener/actions/workflows/ci.yml)

A REST API that turns long URLs into short codes and redirects visitors to the original address. Built with FastAPI and PostgreSQL, containerized with Docker, and tested automatically on every push.

I built it as a backend portfolio project, and I made the design decisions deliberately. The reasoning behind them is in the [design decisions](#design-decisions) section.

## Features

- **Short links:** `POST /urls` creates a 6-character code, checked for collisions before it is saved
- **Redirects:** `GET /{short_code}` returns a `307` redirect and counts the click
- **Link expiry:** an optional `expires_at` makes an expired link return `410 Gone`, distinct from `404` for a code that never existed
- **Click analytics:** `GET /urls/{short_code}/stats` reports the original URL and click count
- **Management:** list with pagination, update, and delete
- **API-key auth:** write endpoints require an `X-API-Key` header, while redirects and stats stay public
- **Rate limiting:** link creation is limited to 5 requests per minute per IP
- **Validation:** malformed URLs are rejected with `422`
- **Operations:** `/health` checks the database, logs are structured and level-configurable, and unexpected errors return a generic `500` while the details go to the logs
- **Interactive docs:** OpenAPI documentation at `/docs`

## Design decisions

- **Short codes:** 6 random hex characters (about 16.7 million possible codes), checked against the database for collisions before saving. Sequential IDs are guessable and reveal how many links exist, and a full UUID is too long for a short link. If the table ever got crowded, the fix is a longer code.
- **Migrations with Alembic:** `create_all()` only creates missing tables and never alters existing ones. Alembic records each schema change as a versioned migration, and the same migration builds the dev, test, CI, and managed databases.
- **404 vs 410:** `404` means the code never existed. `410 Gone` means it existed and has expired. Expiry is checked before the click is counted, so expired hits don't inflate the stats.
- **Auth only on writes:** redirects must work for anyone, and stats are read-only. Creating, updating, and deleting links require the `X-API-Key` header.
- **Rate limit on creation:** link creation writes rows, so it is the endpoint worth protecting. Redirects are cheap reads and are meant to be busy.
- **Fail-fast configuration:** `DATABASE_URL` and `API_KEY` are required, with no fallback values, so the app refuses to start without them. The test suite refuses to run if its database URL equals the real one, because the tests delete rows.
- **Two kinds of failure:** `/health` returns `503` when the database is unreachable, and any unexpected error returns a generic `500` to the client while the full traceback goes to the logs.
- **Containers:** the image runs as a non-root user, and the listen port comes from the `PORT` environment variable.

## Quick start

Requirements: Docker with Docker Compose.

```bash
git clone https://github.com/Mahshidmh/url-shortener.git
cd url-shortener
cp .env.example .env
```

Edit `.env`. Set `API_KEY` to a real value, for example:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Keep the `DATABASE_URL` and `TEST_DATABASE_URL` values from the example. They match the local database in `docker-compose.yml`. Then:

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
```

The API is now at `http://localhost:8080`, with interactive docs at `http://localhost:8080/docs`.

### Run the tests

The tests use a separate database, which has to be created and migrated once:

```bash
docker compose exec db psql -U shortener_user -d shortener_db -c "CREATE DATABASE shortener_test_db;"
docker compose exec -e DATABASE_URL=postgresql://shortener_user:mysecretpassword@db:5432/shortener_test_db app alembic upgrade head
docker compose exec app pytest -v
```

The passwords in `docker-compose.yml` and `.env.example` are local development defaults for a database that is only reachable inside the Docker network. Change them for anything real.

## API

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/urls` | API key | Create a short link (optional `expires_at`). Returns `201`; `401`, `422`, or `429` on failure |
| GET | `/urls` | none | List links (`skip`, `limit`) |
| PATCH | `/urls/{short_code}` | API key | Change the target URL |
| DELETE | `/urls/{short_code}` | API key | Delete a link (`204`) |
| GET | `/{short_code}` | none | Redirect (`307`); `404` unknown, `410` expired |
| GET | `/urls/{short_code}/stats` | none | URL and click count |
| GET | `/health` | none | `200` when the database is reachable, `503` otherwise |

Send the key as `X-API-Key: <your key>`. Full interactive documentation is at `/docs`.

## Deployment

The app is not hosted live. The free hosting tiers I tried either asked for a payment card or required a paid plan, and I chose not to pay for a test project.

What I did instead was run the Docker image against a managed PostgreSQL database (Supabase, with row-level security enabled) and exercise the whole API against it. The image is deployable on any platform that runs containers, with this setup:

- Environment variables: `DATABASE_URL`, `API_KEY` (and optionally `LOG_LEVEL`)
- The platform sets `PORT`, and the image listens on it
- Run `alembic upgrade head` against the production database once
- Use `/health` as the health check path

## CI

GitHub Actions builds the Docker Compose stack on a clean runner, creates and migrates a test database, and runs the full test suite on every push and pull request.

## Known limitations

- **Rate limiter:** it is an in-memory dictionary, so it is per process, resets on restart, and would not be shared across multiple instances. A Redis-backed counter is the standard fix. Behind a proxy, the client IP may also be the proxy's.
- **Auth:** one shared API key, with no per-user accounts or ownership. Stats are public to anyone who knows a short code.
- **Custom aliases:** the validation helper exists, but custom aliases are not exposed through the API, so the `409 Conflict` path is dormant.
- **Dependencies:** direct dependencies are pinned, but packages they pull in on their own can still change between builds.
- **Free-tier databases:** some free managed Postgres plans pause after a period of inactivity.
- **No live demo,** for the reason given above.
