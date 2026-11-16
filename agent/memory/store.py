"""Durable LangGraph BaseStore backed by the tenant-scoped application repository."""

from datetime import datetime, timezone
from langgraph.store.base import BaseStore, GetOp, PutOp, SearchOp, ListNamespacesOp, Item, SearchItem
from core import db


class MemoryStore(BaseStore):
    def _tenant(self, namespace):
        if len(namespace) < 2 or namespace[1] not in ("style", "outcome"):
            raise ValueError("Memory namespace is (tenant, style|outcome)")
        return namespace[0]

    def batch(self, ops):
        results = []
        for op in ops:
            if isinstance(op, (GetOp, PutOp)):
                tenant = self._tenant(op.namespace)
                kind = "memory_" + op.namespace[1]
                if isinstance(op, PutOp):
                    if op.value is None:
                        db.delete(tenant, kind, op.key)
                    else:
                        db.put(tenant, kind, op.key, dict(op.value, id=op.key))
                    results.append(None)
                else:
                    value = db.get(tenant, kind, op.key)
                    now = datetime.now(timezone.utc)
                    results.append(
                        Item(value=value, key=op.key, namespace=op.namespace, created_at=now, updated_at=now)
                        if value
                        else None
                    )
            elif isinstance(op, SearchOp):
                tenant = self._tenant(op.namespace_prefix)
                rows = db.scan(tenant, "memory_" + op.namespace_prefix[1])
                if op.filter:
                    rows = [x for x in rows if all(x.get(k) == v for k, v in op.filter.items())]
                now = datetime.now(timezone.utc)
                results.append(
                    [
                        SearchItem(namespace=op.namespace_prefix, key=x["id"], value=x, created_at=now, updated_at=now)
                        for x in rows[op.offset : op.offset + op.limit]
                    ]
                )
            elif isinstance(op, ListNamespacesOp):
                raise NotImplementedError("Cross-tenant memory enumeration is deliberately disabled")
            else:
                raise TypeError(type(op))
        return results

    async def abatch(self, ops):
        return self.batch(ops)
