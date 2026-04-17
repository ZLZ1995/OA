# syntax=docker/dockerfile:1

FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN echo "FRONTEND_DOCKERFILE_FORCE_DIAG_V3"
RUN node -e "const p=require('./package.json'); console.log('BUILD_SCRIPT=', p.scripts.build); console.log('TYPECHECK_SCRIPT=', p.scripts.typecheck);"
RUN node -e "console.log('PWD=', process.cwd())"
RUN node -e "console.log('VITE_BIN_EXISTS=', require('fs').existsSync('./node_modules/vite/bin/vite.js'))"
RUN node ./node_modules/vite/bin/vite.js build

FROM node:20-alpine AS runtime
WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev
COPY --from=build /app/dist ./dist

EXPOSE 8080

CMD ["sh", "-c", "npm run preview -- --host 0.0.0.0 --port ${PORT:-8080}"]
