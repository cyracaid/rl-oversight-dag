"""Simple public-observation-only reference policies (not RL)."""
import random
import numpy as np


def marginal_scores(observation, base_override=None):
    """Local derivative approximation, consistently evaluated at posterior source means.

    ``base_override`` is evaluation-only: passing the hidden source-error vector turns
    this into the oracle seen in earlier revisions. Never expose it to a learned policy.
    """
    f = observation["features"]
    n, k = len(f), f.shape[1] - 7
    # Reverse derivative of the mean-field expected number of wrong conclusions.
    base = f[:, k + 2].astype(float) if base_override is None else np.asarray(base_override, dtype=float)
    src, dst = observation["edge_index"]
    prob = observation["edge_probability"]
    effective = np.zeros(n)
    product = np.ones(n)
    parents = [[] for _ in range(n)]
    for edge, child in enumerate(dst):
        parents[child].append(edge)
    for v in observation["topological_order"]:
        for edge in parents[v]:
            product[v] *= 1 - prob[edge] * effective[src[edge]]
        effective[v] = 1 - (1 - base[v]) * product[v]
    survival = 1 - prob * effective[src]
    adjoint = np.zeros(n)
    adjoint[observation["sink_ids"]] = 1.0
    # Prefix/suffix products avoid division by zero for certain transmission.
    for v in reversed(observation["topological_order"]):
        edges = parents[v]
        left = adjoint[v] * (1 - base[v])
        partial = []
        for edge in edges:
            partial.append(left)
            left *= survival[edge]
        right = 1.0
        for edge, prefix in zip(reversed(edges), reversed(partial)):
            adjoint[src[edge]] += prefix * right * prob[edge]
            right *= survival[edge]
    score = base * product * adjoint
    return score


def choose(observation: dict, name: str, rng: random.Random | None = None) -> int:
    f = observation["features"]
    n = len(f)
    k = f.shape[1] - 7
    available = np.flatnonzero(observation["mask"])
    if len(available) == 0:
        raise ValueError("no available nodes")
    if name == "random":
        return int((rng or random.Random()).choice(available.tolist()))
    if name == "confidence":
        return int(available[np.argmin(f[available, k])])
    if name == "structural":
        # Approximate unnormalized sink reach from normalized log1p(reach).
        reach = np.expm1(f[:, k + 1] * np.log1p(n))
        score = (1.0 - f[:, k]) * (1.0 + reach)
        return int(available[np.argmax(score[available])])
    if name == "marginal":
        score = marginal_scores(observation)
        return int(available[np.argmax(score[available])])
    if name == "hub":
        src = observation["edge_index"][0]
        degree = np.bincount(src, minlength=n)
        return int(available[np.argmax(degree[available])])
    raise ValueError("unknown policy; choose random, confidence, structural, marginal or hub")


def run_public_policy(graph, snapshot, policy_name, budget, p_catch=0.9,
                      confidence_mode="normal"):
    """Run one policy for one episode.

    ``oracle`` reads the hidden source-error state and is an evaluation-only
    reference, never a deployable policy. ``type_prior`` ignores confidence and
    orders nodes by the base error rate of their type.
    """
    from .environment import OversightEnv
    env = OversightEnv(graph, snapshot, budget=budget, p_catch=p_catch,
                       confidence_mode=confidence_mode)
    rng = random.Random(snapshot.seed + 981)
    if policy_name == "none":
        return env.no_review_score(), []
    action_fn = None
    if policy_name == "type_prior":
        prior = np.asarray([graph.rates[t] for t in graph.types], dtype=float)

        def action_fn(obs):
            available = np.flatnonzero(obs["mask"])
            return int(available[np.argmax(prior[available])])
    elif policy_name == "oracle":
        def action_fn(obs):
            score = marginal_scores(obs, base_override=env._base)
            available = np.flatnonzero(obs["mask"])
            return int(available[np.argmax(score[available])])
    obs = env.observation()
    done = env.done
    actions = []
    while not done:
        if callable(policy_name):
            action = policy_name(obs)
        elif action_fn is not None:
            action = action_fn(obs)
        else:
            action = choose(obs, policy_name, rng)
        actions.append(action)
        obs, reward, done, info = env.step(action)
    return env.final_audit()["final_sink_errors"], actions
