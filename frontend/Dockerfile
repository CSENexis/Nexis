FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package*.json ./
COPY --from=build /app/vite.config.ts ./vite.config.ts

EXPOSE 3000
CMD ["./node_modules/.bin/vite", "preview", "--outDir", "dist", "--port", "3000", "--host", "0.0.0.0"]
