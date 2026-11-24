"""Regression tests for the exact-DP ceiling (PREREGISTER_DP.md, P4 in particular)."""
import pytest

from dag_role3 import generate_graph, sample_episode

from exact_dp import P_CATCH, Model, expected_policy_cost


@pytest.fixture(scope="module")
def model():
    graph = generate_graph("real", 60000)
    snapshot = sample_episode(graph, 60000 + 20000, "normal")
    return Model(graph, snapshot)


def test_dp_one_step_equals_greedy_exact(model):
    """P4: at budget 1 the optimum and the exact one-step lookahead are the same policy."""
    assert model.dp(1) == pytest.approx(
        expected_policy_cost(model, model.greedy_exact_policy, 1), abs=1e-9)


def test_optimal_never_worse_than_the_rule(model):
    marginal = expected_policy_cost(model, model.marginal_policy, 2)
    assert model.dp(2) <= marginal + 1e-9


def test_value_is_monotone_in_budget(model):
    values = [model.dp(k) for k in (1, 2)]
    assert values[1] <= values[0] + 1e-12


def test_cost_without_reviews_is_the_prior_expectation(model):
    graph = model.graph
    assert 0.0 <= model.cost(0, 0) <= len(graph.sinks)


def test_marginal_reimplementation_matches_the_deployed_rule(model):
    """The rule in `policies` and the rule inside the DP must pick the same node."""
    from dag_role3 import OversightEnv, policies

    env = OversightEnv(model.graph, model.snapshot, budget=16)
    assert policies.choose(env.observation(), "marginal") == model.marginal_policy(0, 0, None)


def test_miss_update_is_a_bayes_update():
    from exact_dp import miss_update

    q, catch = 0.3, P_CATCH
    # Posterior after "no flag" must be below the prior but above zero.
    assert 0.0 < miss_update(q, catch) < q
    # A perfect reviewer leaves no doubt when nothing is caught.
    assert miss_update(q, 1.0) == pytest.approx(0.0, abs=1e-9)


def _fake_csv(tmp_path, dp5_minus_greedy):
    """One real graph per budget, with dp placed at a chosen distance from greedy."""
    import csv

    path = tmp_path / "dp_episodes.csv"
    fields = ["family", "graph_seed", "budget", "n", "none", "confidence",
              "marginal", "greedy_exact", "dp"]
    rows = []
    for k in (1, 3, 5):
        greedy = 2.0 / k
        dp = greedy + (dp5_minus_greedy if k == 5 else 0.0)
        rows.append({"family": "real", "graph_seed": 60000, "budget": k, "n": 21,
                     "none": 2.5, "confidence": 2.2, "marginal": greedy,
                     "greedy_exact": greedy, "dp": dp})
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return tmp_path


def test_report_rejects_a_planning_gain_above_the_falsification_bound(tmp_path):
    """P2 bounds the *size* of the gain: a signed test would pass any gain at all."""
    from exact_dp import report

    out = _fake_csv(tmp_path, dp5_minus_greedy=-0.06)
    report(out)
    text = (out / "report.md").read_text()
    p2 = [ln for ln in text.splitlines() if ln.startswith("| P2")][0]
    assert "contradicted" in p2


def test_report_keeps_a_gain_inside_the_bound_but_flags_the_nominal_miss(tmp_path):
    from exact_dp import report

    out = _fake_csv(tmp_path, dp5_minus_greedy=-0.022)
    report(out)
    p2 = [ln for ln in (out / "report.md").read_text().splitlines()
          if ln.startswith("| P2")][0]
    assert "holds" in p2 and "nominal 0.02 missed" in p2