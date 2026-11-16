"""SDK OAuth 2.1 discovery + PKCE with encrypted per-tenant token/client storage.

The browser only receives the authorization URL. Tokens remain in server storage.
The flow is wired but cannot be verified without a user's Upwork authorization.
"""

import asyncio
import os
import secrets
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import OAuthClientMetadata, OAuthToken, OAuthClientInformationFull
from langchain_mcp_adapters.client import MultiServerMCPClient
from apps.api.auth.oauth_store import save_tokens, load_tokens

flows = {}
tasks = set()


class EncryptedTokenStorage:
    def __init__(self, tenant, provider):
        self.tenant = tenant
        self.provider = provider

    async def get_tokens(self):
        value = load_tokens(self.tenant, self.provider)
        return OAuthToken.model_validate(value) if value else None

    async def set_tokens(self, tokens):
        save_tokens(self.tenant, self.provider, tokens.model_dump(mode="json"))

    async def get_client_info(self):
        value = load_tokens(self.tenant, self.provider + "_client")
        return OAuthClientInformationFull.model_validate(value) if value else None

    async def set_client_info(self, info):
        save_tokens(self.tenant, self.provider + "_client", info.model_dump(mode="json"))


async def begin_upwork(tenant, public_base):
    key = secrets.token_urlsafe(24)
    loop = asyncio.get_running_loop()
    flow = {"tenant": tenant, "url": loop.create_future(), "callback": loop.create_future(), "status": "connecting"}
    flows[key] = flow

    async def redirect_handler(url):
        if not flow["url"].done():
            flow["url"].set_result(url)

    async def callback_handler():
        return await flow["callback"]

    provider = OAuthClientProvider(
        server_url=os.getenv("UPWORK_MCP_URL", "https://mcp.upwork.com/mcp"),
        client_metadata=OAuthClientMetadata(
            client_name="GigBid research copilot",
            redirect_uris=[public_base + "/api/oauth/upwork/callback/" + key],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="none",
        ),
        storage=EncryptedTokenStorage(tenant, "upwork"),
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
        timeout=300,
    )

    async def connect():
        try:
            client = MultiServerMCPClient(
                {
                    "upwork": {
                        "transport": "streamable_http",
                        "url": os.getenv("UPWORK_MCP_URL", "https://mcp.upwork.com/mcp"),
                        "auth": provider,
                    }
                }
            )
            async with client.session("upwork") as session:
                result = await session.list_tools()
                flow["tools"] = [t.name for t in result.tools]
                flow["status"] = "connected"
            if not flow["url"].done():
                flow["url"].set_result(None)
        except Exception:
            flow["status"] = "failed"
            if not flow["url"].done():
                flow["url"].set_result(None)
        finally:
            # No OAuth details, authorization code or credentials enter logs/audits.
            async def expire():
                await asyncio.sleep(600)
                flows.pop(key, None)

            cleanup = asyncio.create_task(expire())
            tasks.add(cleanup)
            cleanup.add_done_callback(tasks.discard)

    task = asyncio.create_task(connect())
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    try:
        url = await asyncio.wait_for(asyncio.shield(flow["url"]), timeout=30)
    except asyncio.TimeoutError:
        url = None
    return {"flow_id": key, "authorization_url": url, "status": flow["status"]}
