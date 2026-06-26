# Commands

Quick reference for running Voxa with Docker.

> Run all commands from the project root (`c:\Users\l01402933\Documents\voxa`), where `docker-compose.yml` lives.

## Start the app

| Goal | Command |
|------|---------|
| Start everything (normal use) | `docker compose up -d` |
| Start and rebuild (after code changes) | `docker compose up -d --build` |
| Check running containers | `docker compose ps` |
| Follow live logs (e.g. backend) | `docker compose logs -f backend` |

Then open 👉 **http://localhost:8080**

## Stop the app

| Goal | Command |
|------|---------|
| Stop everything (keeps the database) | `docker compose down` |
| Stop **and wipe the database** (start fresh) | `docker compose down -v` |
| Pause without removing | `docker compose stop` |
| Resume what was paused | `docker compose start` |

## Notes

- **`-d`** = *detached*: runs in the background and returns the terminal to you.
- **`down`** removes containers and the network, **but not the data** (it stays in the volumes). Bring it back with `docker compose up -d`.
- **`down -v`** also deletes the data (the database resets and re-runs migrations on the next start). Use it only when you want a clean slate.

### Daily workflow, in two lines

```bash
docker compose up -d      # start working
docker compose down       # stop working
```

## Service URLs

| Service | URL |
|---------|-----|
| Frontend (Nginx) | http://localhost:8080 |
| Backend API docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL (DB client) | `localhost:5433` |
