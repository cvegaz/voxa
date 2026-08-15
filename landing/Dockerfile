# Voxa landing — production image. Stage 1 builds the static Vite site; stage 2
# serves it with nginx. Same two-stage shape as frontend/Dockerfile: node and
# node_modules are needed to BUILD, not to SERVE, so they never reach the final
# image (~25 MB instead of ~1 GB, and no source code in a public container).
#
# Vite bakes VITE_* vars into the bundle at BUILD time, which makes every one of
# them a decision about how portable the image is:
#
#   VITE_API_BASE is deliberately NOT a build arg. It stays empty so the bundle
#   calls a RELATIVE /api/contact, which nginx proxies to the backend on the
#   internal network (see nginx.conf). The alternative — baking an absolute
#   https://app.<domain> — would hard-code a domain into the image, and this
#   project does not own one yet. Same-origin also removes CORS entirely: no
#   preflight, no LANDING_ORIGINS to keep in sync.
#
#   The link vars ARE build args: they are public, low-churn values, and any
#   left empty simply hides its button (see src/config.ts) rather than
#   rendering a dead link. Enable one later by rebuilding with --build-arg.

FROM node:20-alpine AS build
WORKDIR /app

# Manifest first, then the source: this layer is cached while you edit code.
# `npm ci` installs exactly what package-lock.json pins — reproducible builds.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_GITHUB_URL=https://github.com/cvegaz/voxa
ARG VITE_APP_URL=
ARG VITE_LINKEDIN_URL=
ARG VITE_CALENDLY_URL=
ARG VITE_CONTACT_EMAIL=
ENV VITE_GITHUB_URL=$VITE_GITHUB_URL \
    VITE_APP_URL=$VITE_APP_URL \
    VITE_LINKEDIN_URL=$VITE_LINKEDIN_URL \
    VITE_CALENDLY_URL=$VITE_CALENDLY_URL \
    VITE_CONTACT_EMAIL=$VITE_CONTACT_EMAIL

RUN npm run build

FROM nginx:alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
