# Build context is the repository root (the judge harness lives in ../runner).
FROM node:24-alpine AS build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY runner /src/runner
COPY frontend ./
# Leave empty to load Pyodide from the jsDelivr CDN, or set to /pyodide/ to self-host it.
ARG VITE_PYODIDE_URL=""
RUN if [ -n "$VITE_PYODIDE_URL" ]; then npm run pyodide:local; export VITE_PYODIDE_URL; fi && npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/frontend/dist /usr/share/nginx/html
EXPOSE 80
