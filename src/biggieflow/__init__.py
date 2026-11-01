"""BiggieFlow: consent-first cadence control and capped parameter search."""

from .cadence import CadenceVector
from .consent import ConsentError, ConsentRecord, ConsentRegistry
from .search import CadenceGrid, PlanRefused, SearchKilled, plan, run_search

__all__ = [
    "CadenceVector",
    "ConsentError",
    "ConsentRecord",
    "ConsentRegistry",
    "CadenceGrid",
    "PlanRefused",
    "SearchKilled",
    "plan",
    "run_search",
]
__version__ = "0.1.0"
