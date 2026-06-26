# ─────────────────────────────────────────────────────────────────────────────
# Frontend image in TWO stages (multi-stage build).
#
# Key idea: to BUILD React we need Node and hundreds of MB of dependencies, but
# to SERVE the result we only need a few static files (HTML/CSS/JS) and a tiny
# web server. So:
#   - "build" stage:   uses Node to compile -> produces /app/dist
#   - "runtime" stage: copies ONLY that dist into a tiny Nginx image.
# Result: a final image of ~25 MB instead of ~1 GB, with no Node or source code.
# ─────────────────────────────────────────────────────────────────────────────

# ---------- Stage 1: build ----------
FROM node:20-alpine AS build

WORKDIR /app

# Same cache trick as the backend: manifest first, then the code.
# `npm ci` installs EXACTLY what package-lock.json pins (reproducible and fast).
COPY package.json package-lock.json ./
RUN npm ci

# Now the rest of the frontend source code.
COPY . .

# Compile TypeScript + bundle with Vite. Output goes to /app/dist.
RUN npm run build

# ---------- Stage 2: serve ----------
FROM nginx:alpine AS runtime

# Our config (SPA fallback + proxy /api -> backend) replaces the default one.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy ONLY the compiled files from the previous stage.
# No Node, no node_modules, and no source code reach the final image.
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx listens on 80 inside the container.
EXPOSE 80

# The Nginx image already provides its own CMD to start the server.
