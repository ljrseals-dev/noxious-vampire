import pytest

from biggieflow import search
from biggieflow.search import CadenceGrid, PlanRefused, SearchKilled, plan, run_search


def test_default_grid_size_is_108():
    # 3 x 3 x 3 x 4
    assert CadenceGrid().size() == 108


def test_plan_refuses_over_cost():
    with pytest.raises(PlanRefused):
        plan(CadenceGrid(), cost_per_eval_usd=0.10, max_cost_usd=5.0)  # $10.80


def test_plan_allows_with_confirmation():
    p = plan(CadenceGrid(), cost_per_eval_usd=0.10, max_cost_usd=5.0, confirmed_over_cap=True)
    assert p.est_cost_usd == pytest.approx(10.8)


def test_plan_ok_under_cap():
    p = plan(CadenceGrid(), cost_per_eval_usd=0.01)
    assert p.combinations == 108
    assert p.est_cost_usd == pytest.approx(1.08)


def test_node_cap():
    with pytest.raises(PlanRefused):
        plan(CadenceGrid(), cost_per_eval_usd=0.0, nodes=65)


def test_combination_cap():
    class Huge(CadenceGrid):
        def size(self):
            return 10**9 + 1

    with pytest.raises(PlanRefused):
        plan(Huge(), cost_per_eval_usd=0.0)


def test_run_requires_matching_plan():
    grid = CadenceGrid()
    with pytest.raises(PlanRefused):
        run_search(None, grid, lambda v: 0.0)
    other = plan(CadenceGrid(swing_8th=(0.1,)), cost_per_eval_usd=0.0)
    with pytest.raises(PlanRefused):
        run_search(other, grid, lambda v: 0.0)


def test_run_returns_top_k_sorted():
    grid = CadenceGrid()
    p = plan(grid, cost_per_eval_usd=0.0)
    best = run_search(p, grid, lambda v: -abs(v.swing_8th - 0.20) - abs(v.swing_16th - 0.10), top_k=3)
    assert len(best) == 3
    assert best[0][0] >= best[1][0] >= best[2][0]
    assert best[0][1].swing_8th == 0.20 and best[0][1].swing_16th == 0.10


def test_kill_stops_search():
    grid = CadenceGrid()
    p = plan(grid, cost_per_eval_usd=0.0)
    calls = {"n": 0}

    def scorer(v):
        calls["n"] += 1
        if calls["n"] == 5:
            search.kill()
        return 0.0

    with pytest.raises(SearchKilled):
        run_search(p, grid, scorer)
    assert calls["n"] == 5
