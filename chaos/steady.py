from __future__ import annotations

import operator

import httpx

from .spec import Condition

OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}


def holds(c: Condition, value: float | None) -> bool:
    """No data counts as not holding: an empty query must never look like a pass."""
    return value is not None and OPS[c.op](value, c.threshold)


class Prometheus:
    def __init__(self, base_url: str):
        self.client = httpx.Client(base_url=base_url, timeout=10)

    def value(self, query: str) -> float | None:
        r = self.client.get("/api/v1/query", params={"query": query})
        r.raise_for_status()
        result = r.json()["data"]["result"]
        if not result:
            return None
        return float(result[0]["value"][1])

    def evaluate(self, conditions: list[Condition]) -> list[tuple[Condition, float | None, bool]]:
        out = []
        for c in conditions:
            v = self.value(c.query)
            out.append((c, v, holds(c, v)))
        return out
