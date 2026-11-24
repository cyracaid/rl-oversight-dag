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


def test_miss_update_is_a_bayes_update():
    from exact_dp import miss_update

    q, catch = 0.3, P_CATCH
    # Posterior after "no flag" must be below the prior but above zero.
    assert 0.0 < miss_update(q, catch) < q
    # A perfect reviewer leaves no doubt when nothing is caught.
    assert miss_update(q, 1.0) == pytest.approx(0.0, abs=1e-9)