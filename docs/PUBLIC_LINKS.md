# Published submission artifacts

- [Source repository](https://github.com/SaifullahKhanSafi/Gigbid)
- [Technical write-up](https://github.com/SaifullahKhanSafi/Gigbid/blob/main/docs/TECHNICAL_WRITEUP.md)
- [Three-minute demo](https://github.com/SaifullahKhanSafi/Gigbid/blob/main/output/demo/gigbid-demo-3min.mp4)
- [R&D report](https://github.com/SaifullahKhanSafi/Gigbid/blob/main/output/pdf/GigBid_RnD_Report.pdf)
- [Portfolio MCP installation and usage](https://github.com/SaifullahKhanSafi/Gigbid/blob/main/mcp_servers/portfolio/README.md)
- Sanitized trace exports: [proposal](https://github.com/SaifullahKhanSafi/Gigbid/blob/main/docs/traces/demo-1.json), [second persona](https://github.com/SaifullahKhanSafi/Gigbid/blob/main/docs/traces/demo-2.json), [conversation](https://github.com/SaifullahKhanSafi/Gigbid/blob/main/docs/traces/demo-3.json).

These are GitHub-hosted artifacts and JSON trace exports. A public running application, hosted MCP endpoint, registry package and Phoenix trace UI are not deployed. The local application is at http://127.0.0.1:8000 on the prepared machine. Private credentials are stored in `runtime/reviewer-login.txt`; do not publish them.

Render configuration is provided under `infra/render.yaml`. It requires paid services and a reachable model endpoint; no hosting account was supplied. The prepared offline local deployment is the selected fallback.
