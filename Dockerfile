# ---- Stage 1: build the React frontend ----
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend + built frontend ----
FROM python:3.11-slim
WORKDIR /app

# Install backend dependencies first (better layer caching - this layer
# only rebuilds when requirements.txt actually changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY main.py entity.py start_all.py ./
COPY agents/ ./agents/
COPY mcp_servers/ ./mcp_servers/

# Copy the frontend build output from stage 1 - main.py serves this
# directly via StaticFiles once it exists.
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# main.py listens on $PORT if set, defaulting to 8000
ENV PORT=8000
EXPOSE 8000

# start_all.py launches all 4 MCP servers plus main.py together in this
# single container - see that file's comments for why.
CMD ["python", "start_all.py"]
