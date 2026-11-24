# Stage 1: Build React static assets
FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

COPY . .

# Build argument for API base URL
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Stage 2: Serve with lightweight Nginx
FROM nginx:alpine AS runner

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
