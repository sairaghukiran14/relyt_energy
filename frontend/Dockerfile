# `build` stage: used by docker-compose, which runs the Vite dev server from it so that
# /api is proxied to the backend (single origin, like Vercel).
# Final stage: serves the static bundle only. It has NO /api proxy, so it needs the API
# reachable on the same origin (e.g. behind a reverse proxy).
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
# serve -s handles SPA routing (falls back to index.html).
CMD ["serve", "-s", "dist", "-l", "5173"]
