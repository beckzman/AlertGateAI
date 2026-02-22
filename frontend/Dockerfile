# --- Build Stage ---
FROM node:18-slim AS build

WORKDIR /app

# Abhängigkeiten kopieren
COPY package*.json ./
RUN npm install

# Quellcode kopieren
COPY . .

# App bauen
RUN npm run build

# --- Serve Stage ---
FROM nginx:stable-alpine

# Kopiere die gebauten Dateien in den Nginx-Folder
COPY --from=build /app/dist /usr/share/nginx/html

# Optionale Nginx-Config (für SPA Routing falls nötig)
RUN echo 'server { \
    listen 80; \
    location / { \
    root /usr/share/nginx/html; \
    index index.html; \
    try_files $uri $uri/ /index.html; \
    } \
    }' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
