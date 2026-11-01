"""Cost-capped cadence parameter search (a local 'Brute Genius'-style contract).

This is an independent local implementation of the contract described in the
master prompt: plan() first, refuse estimates above max_cost_usd, hard caps on
nodes and combinations, and a kill switch. It does not call or depend on the
ljrseals-dev/redesigned-fiesta repository, whose interface is unverified.
"""

from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field
from typing import Callable, Iterator

from .cadence import ALLOWED_RHYME_BEATS, CadenceVector

MAX_NODES = 64
MAX_COMBINATIONS = 10**9
DEFAULT_MAX_COST_USD = 5.0


class PlanRefused(Exception):
    """plan() refused: over a hard cap or over the cost ceiling."""


class SearchKilled(Exception):
    """The kill switch was triggered mid-search."""


@dataclass(frozen=True)
class CadenceGrid:
    swing_8th: tuple[float, ...] = (0.10, 0.20, 0.30)
    swing_16th: tuple[float, ...] = (0.05, 0.10, 0.20)
    anacrusis_prob: tuple[float, ...] = (0.3, 0.6, 0.9)
    rhyme_pair_beat: tuple[float, ...] = ALLOWED_RHYME_BEATS

    def size(self) -> int:
        return (
            len(self.swing_8th)
            * len(self.swing_16th)
            * len(self.anacrusis_prob)
            * len(self.rhyme_pair_beat)
        )

    def __iter__(self) -> Iterator[CadenceVector]:
        for s8, s16, ana, beat in itertools.product(
            self.swing_8th, self.swing_16th, self.anacrusis_prob, self.rhyme_pair_beat
        ):
            yield CadenceVector(
                swing_8th=s8, swing_16th=s16, anacrusis_prob=ana, rhyme_pair_beat=beat
            )


@dataclass(frozen=True)
class Plan:
    combinations: int
    nodes: int
    est_cost_usd: float
    max_cost_usd: float


def plan(
    grid: CadenceGrid,
    cost_per_eval_usd: float,
    nodes: int = 1,
    max_cost_usd: float = DEFAULT_MAX_COST_USD,
    confirmed_over_cap: bool = False,
) -> Plan:
    """Estimate a search and refuse it if it breaks a cap. Always call before run_search."""
    if cost_per_eval_usd < 0:
        raise ValueError("cost_per_eval_usd must be >= 0")
    if nodes < 1 or nodes > MAX_NODES:
        raise PlanRefused(f"nodes must be between 1 and {MAX_NODES}")
    combos = grid.size()
    if combos > MAX_COMBINATIONS:
        raise PlanRefused(f"{combos} combinations exceeds hard cap {MAX_COMBINATIONS}")
    est = combos * cost_per_eval_usd
    if est > max_cost_usd and not confirmed_over_cap:
        raise PlanRefused(
            f"estimated ${est:.2f} exceeds max_cost_usd ${max_cost_usd:.2f}; "
            "explicit user confirmation required"
        )
    return Plan(combos, nodes, est, max_cost_usd)


@dataclass
class _Kill:
    event: threading.Event = field(default_factory=threading.Event)

    def trigger(self) -> None:
        self.event.set()


KILL = _Kill()


def kill() -> None:
    """Emergency stop for any running search."""
    KILL.trigger()


def run_search(
    approved: Plan,
    grid: CadenceGrid,
    score_fn: Callable[[CadenceVector], float],
    top_k: int = 5,
) -> list[tuple[float, CadenceVector]]:
    """Score every cadence vector in the grid and return the best top_k.

    Requires an approved Plan from plan(); the plan must match the grid size.
    """
    if not isinstance(approved, Plan) or approved.combinations != grid.size():
        raise PlanRefused("run_search requires a matching plan() result")
    KILL.event.clear()
    scored: list[tuple[float, CadenceVector]] = []
    for vector in grid:
        if KILL.event.is_set():
            raise SearchKilled("search stopped by kill()")
        scored.append((score_fn(vector), vector))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[:top_k]
