# --- Banking Copilot UI: multi-stage build ---
# Stage 1 builds the React app; Stage 2 serves the static output with nginx.
# The final image contains ONLY nginx + static files (no Node, no source).

# ---- Stage 1: build ----
FROM node:20-slim AS build
WORKDIR /app

# Install deps as a cached layer (only re-runs when lockfile changes).
COPY package.json package-lock.json ./
RUN npm ci

# Build the static bundle into /app/dist.
COPY . .
RUN npm run build

# ---- Stage 2: serve ----
FROM nginx:alpine

# Our reverse-proxy + SPA-fallback config replaces the default.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy ONLY the built static files from stage 1.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
# nginx:alpine already runs nginx in the foreground by default.
