#!/usr/bin/env python3
"""Budgeted Monte Carlo greedy rollout using belief particles only."""
import copy
import numpy as np


def world_errors(base, coins, belief):
    err = base.copy()
    for i in belief.topo:
        for p, e in belief.in_edges[i]:
            err[i] |= err[p] and coins[e]
    return err


def choose(belief, available, remaining, samples=8, candidates=3, seed=0,
           paired_diagnostics=False):
    if samples < 1 or candidates < 1 or remaining < 1:
        raise ValueError('positive search budgets required')
    actions = [i for i, ok in enumerate(available) if ok]
    if len(available) != belief.N or remaining > len(actions):
        raise ValueError('remaining budget must fit available actions')
    greedy = belief.best_action(available)
    ranked = sorted(actions, key=lambda i: (-belief.gain(i), i))
    shortlist = [greedy] + [i for i in ranked if i != greedy][:candidates-1]
    rng = np.random.default_rng(seed)
    # Common sampled worlds and per-node catches across candidates.
    worlds = rng.integers(belief.M, size=samples)
    catches = rng.random((samples, belief.N)) < belief.p_catch
    values = {}
    trajectories = {}
    for action in shortlist:
        errors = []
        for trial, world in enumerate(worlds):
            posterior = copy.deepcopy(belief)
            # Identical resampling stream at each candidate's rollout start.
            posterior.rng = np.random.default_rng(seed + trial + 100000)
            base = belief.B[:, world].copy()
            coins = belief.C[:, world].copy()
            mask = list(available)
            a = action
            for step in range(remaining):
                err = world_errors(base, coins, belief)
                flag = bool(err[a] and catches[trial, a])
                if flag:
                    base[a] = False
                posterior.observe(a, flag)
                mask[a] = False
                if step+1 < remaining:
                    a = posterior.best_action(mask)
            err = world_errors(base, coins, belief)
            errors.append(sum(bool(err[i]) for i, sink in enumerate(belief.is_sink) if sink))
        values[action] = float(np.mean(errors))
        if paired_diagnostics:
            trajectories[action] = np.asarray(errors, dtype=float)
    # Keep greedy on estimated ties. No claim that finite sampling guarantees improvement.
    selected = min(shortlist, key=lambda a: values[a])
    detail = dict(candidate_values=values, samples=samples, candidates=len(shortlist),
                  simulated_reviews=len(shortlist)*samples*remaining, greedy=greedy)
    if paired_diagnostics:
        detail['paired_vs_greedy'] = {
            a: dict(mean=float(np.mean(trajectories[a]-trajectories[greedy])),
                    standard_error=(float(np.std(trajectories[a]-trajectories[greedy], ddof=1)
                                          / np.sqrt(samples)) if samples > 1 else None))
            for a in shortlist}
    return selected, detail
