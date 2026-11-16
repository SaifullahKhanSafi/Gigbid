"""Instructor API adapter; route map must match the API spec supplied by the TA."""

import json
import os
import httpx


class GigSimAdapter:
    def __init__(self):
        self.url = os.environ["GIGSIM_URL"].rstrip("/")
        path = os.getenv("GIGSIM_ROUTE_MAP")
        if not path:
            raise RuntimeError("Official GigSim spec missing: configure GIGSIM_ROUTE_MAP; no endpoints are guessed")
        self.routes = json.loads(open(path, encoding="utf-8").read())

    async def call(self, name, arguments):
        route = self.routes[name]
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.request(
                route["method"],
                self.url + route["path"],
                headers={"Authorization": "Bearer " + os.environ["GIGSIM_TOKEN"]},
                **({"params": arguments} if route["method"] == "GET" else {"json": arguments}),
            )
            r.raise_for_status()
            return r.json()

    def __getattr__(self, name):
        async def invoke(*args, **kwargs):
            # Named arguments are required to avoid ambiguity with the official schema.
            return await self.call(name, kwargs or (args[0] if len(args) == 1 and isinstance(args[0], dict) else {}))

        return invoke
