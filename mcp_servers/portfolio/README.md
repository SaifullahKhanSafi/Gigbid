# GigBid Portfolio MCP

A read-only, evidence-focused MCP server built with the official Python SDK. Tools: `search_evidence`, `get_case_study`, `list_skills`, and an opt-in `rank_team`. Resources: `portfolio://case/{id}` and `portfolio://proposal/{id}`. Prompt: `answer_screening_question`.

Run from the repository:

```sh
pip install .
python -m scripts.seed_data
GIGBID_TENANT=local-owner python -m mcp_servers.portfolio.server
```

On PowerShell, use `$env:GIGBID_TENANT='local-owner'` before the Python command. Stdio is for the owner-selected local host. For authenticated HTTP set `MCP_HTTP=1`; the app issues tenant-scoped service JWTs. Do not expose anonymous HTTP.

Documented Docker installation:

```sh
git clone https://github.com/SaifullahKhanSafi/Gigbid.git
cd Gigbid
docker build -f infra/docker/portfolio.Dockerfile -t gigbid-portfolio .
docker run --rm -i -e GIGBID_TENANT=local-owner gigbid-portfolio
```

The image seeds explicitly fictional example portfolios. For your own evidence, use GigBid's authenticated portfolio upload, preserve provenance, and point your host at the same tenant/data environment. Do not pass fictional case studies off as real credentials. See `docs/TOOLS.md` and `docs/DATA_CARD.md` for contracts, annotations, trust and limitations.

Package/image publication and installation from a public repository require the actual repository push. The local source is installable; no PyPI release or registry image is claimed.
