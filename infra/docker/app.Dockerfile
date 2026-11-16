FROM node:22-bookworm-slim AS web
WORKDIR /build/apps/web
COPY apps/web/package*.json ./
RUN npm ci --no-audit --no-fund
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 GIGBID_ENV=production GIGBID_RUNTIME=/var/gigbid
WORKDIR /app
COPY pyproject.toml README.md ./
COPY core core
COPY agent agent
COPY rag rag
COPY mcp_servers mcp_servers
COPY apps/api apps/api
COPY worker worker
COPY scripts scripts
COPY support support
COPY evals evals
COPY data/policy_pack data/policy_pack
RUN pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu && pip install .
RUN python -m scripts.seed_data
COPY --from=web /build/apps/web/dist /app/apps/web/dist
RUN useradd --create-home gigbid && mkdir -p /var/gigbid /home/gigbid/.cache/huggingface && chown -R gigbid:gigbid /var/gigbid /app /home/gigbid/.cache
USER gigbid
EXPOSE 8000
CMD ["uvicorn","apps.api.main:app","--host","0.0.0.0","--port","8000","--no-access-log"]
