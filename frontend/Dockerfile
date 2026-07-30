# Drum Pattern Generator — web (Vue build served by nginx, proxies /api to the API)
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# The browser calls the API at this base. Default "/api" is proxied to the
# backend by nginx (same origin, no CORS). Vite bakes this in at build time.
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
