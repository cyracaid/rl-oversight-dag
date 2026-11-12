"""Simple public-observation-only reference policies (not RL)."""
import random
import numpy as np


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
        # Reverse derivative of the mean-field expected number of wrong conclusions.
        base, effective = f[:, k + 2].astype(float), f[:, k + 3].astype(float)
        src, dst = observation["edge_index"]
        prob = observation["edge_probability"]
        survival = 1 - prob * effective[src]
        product = np.ones(n)
        np.multiply.at(product, dst, survival)
        adjoint = np.zeros(n)
        adjoint[observation["sink_ids"]] = 1.0
        # Prefix/suffix products avoid division by zero for certain transmission.
        parents = [[] for _ in range(n)]
        for edge, child in enumerate(dst):
            parents[child].append(edge)
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
        return int(available[np.argmax(score[available])])
    if name == "hub":
        src = observation["edge_index"][0]
        degree = np.bincount(src, minlength=n)
        return int(available[np.argmax(degree[available])])
    raise ValueError("name must be random, confidence, structural or hub")


def run_public_policy(graph, snapshot, policy_name, budget, p_catch=0.9,
                      confidence_mode="normal"):
    from .environment import OversightEnv
    env = OversightEnv(graph, snapshot, budget=budget, p_catch=p_catch,
                       confidence_mode=confidence_mode)
    rng = random.Random(snapshot.seed + 981)
    if policy_name == "none":
        return env.no_review_score(), []
    obs = env.observation()
    done = env.done
    actions = []
    while not done:
        action = policy_name(obs) if callable(policy_name) else choose(obs, policy_name, rng)
        actions.append(action)
        obs, reward, done, info = env.step(action)
    return env.final_audit()["final_sink_errors"], actions
