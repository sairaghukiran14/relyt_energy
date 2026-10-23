# Build the static site, then serve it with a tiny static server that proxies
# /api to the backend (so the browser sees a single origin, like Vercel).
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

FROM node:20-slim
WORKDIR /app
RUN npm install -g serve@14.2.4
COPY --from=build /app/dist ./dist
EXPOSE 5173
# serve handles SPA routing; the compose file sets the API proxy via nginx-style
# rewrite is not needed because Vite dev proxy is only for local dev. In compose
# the frontend talks to the backend service directly through the browser's /api
# requests, which the reverse proxy (see docker-compose) routes.
CMD ["serve", "-s", "dist", "-l", "5173"]
