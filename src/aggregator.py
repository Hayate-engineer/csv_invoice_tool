from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .normalizer import NormalizedRow


@dataclass
class AggregationResult:
    by_store: dict[str, int]
    by_item: dict[str, int]


def aggregate(rows: Iterable[NormalizedRow]) -> AggregationResult:
    by_store: dict[str, int] = defaultdict(int)
    by_item: dict[str, int] = defaultdict(int)

    for r in rows:
        by_store[r.store] += r.amount
        by_item[r.item] += r.amount

    return AggregationResult(by_store=dict(by_store), by_item=dict(by_item))