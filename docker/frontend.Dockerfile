FROM node:20-alpine

WORKDIR /app/webapp/frontend

# Install deps first (layer cache)
COPY webapp/frontend/package*.json ./
RUN npm install

# Source is bind-mounted at runtime in dev
EXPOSE 5173
