FROM python:3.12-slim
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 GIGBID_RUNTIME=/tmp/gigbid
COPY pyproject.toml README.md ./
COPY core core
COPY agent agent
COPY rag rag
COPY mcp_servers mcp_servers
COPY scripts scripts
COPY data/policy_pack data/policy_pack
RUN pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu && pip install . && python -m scripts.seed_data
ENV GIGBID_TENANT=local-owner
CMD ["python","-m","mcp_servers.portfolio.server"]
