# Multi-stage build for React frontend
# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

# Copy dependency files first for cache efficiency
COPY package.json package-lock.json ./
RUN npm ci --production=false

# Copy source and build
COPY . .
ENV REACT_APP_API_URL=""
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy custom nginx config
COPY --from=build /app/build /usr/share/nginx/html

# The main nginx.conf is mounted from the project root via docker-compose.
# This default.conf handles just the static file serving as a fallback.
RUN rm /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
