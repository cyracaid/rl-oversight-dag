#!/usr/bin/env python3
"""Particle-world rollouts with integrated catches or matched sampled catches."""
import copy
import hashlib
import numpy as np
from sampled_planning import world_errors


def choose(belief, available, remaining, samples=128, seed=0, averaged=True):
    if len(available) != belief.N or samples < 1 or remaining < 1:
        raise ValueError('valid mask and positive budgets required')
    actions = [i for i, ok in enumerate(available) if ok]
    if remaining > len(actions):
        raise ValueError('remaining budget exceeds available actions')
    greedy = belief.best_action(available)
    order = [greedy]+[a for a in actions if a != greedy]
    worlds = np.random.default_rng(seed).integers(belief.M, size=samples)
    catches = np.random.default_rng(seed+20000000).random((samples, belief.N)) < belief.p_catch
    reviews = updates = copies = 0
    max_mass_error = 0.
    values = {}
    for first in order:
        costs = []
        for trial, world in enumerate(worlds):
            posterior = copy.deepcopy(belief); copies += 1
            posterior.rng = np.random.default_rng(seed+trial+100000)
            base = belief.B[:, world].copy(); edges = belief.C[:, world].copy()

            def visit(base, posterior, mask, action, left, mass):
                nonlocal reviews, updates, copies
                reviews += 1
                wrong = bool(world_errors(base, edges, belief)[action])
                if averaged:
                    flagged_prob = belief.p_catch if wrong else 0.
                    branches = [(False, 1.-flagged_prob), (True, flagged_prob)]
                else:
                    branches = [(bool(wrong and catches[trial, action]), 1.)]
                cost = leaf_mass = 0.
                for flag, probability in branches:
                    if probability == 0.:
                        continue
                    child = copy.deepcopy(posterior); copies += 1
                    child_base = base.copy()
                    if flag:
                        child_base[action] = False
                    child.observe(action, flag); updates += 1
                    child_mask = list(mask); child_mask[action] = False
                    weight = mass*probability
                    if left == 1:
                        terminal = world_errors(child_base, edges, belief)
                        cost += weight*sum(bool(terminal[i]) for i, sink in enumerate(belief.is_sink) if sink)
                        leaf_mass += weight
                    else:
                        next_action = child.best_action(child_mask)
                        child_cost, child_mass = visit(child_base, child, child_mask,
                                                       next_action, left-1, weight)
                        cost += child_cost; leaf_mass += child_mass
                return cost, leaf_mass

            value, mass = visit(base, posterior, list(available), first, remaining, 1.)
            max_mass_error = max(max_mass_error, abs(mass-1.))
            if abs(mass-1.) > 1e-12:
                raise AssertionError('rollout catch mass not conserved')
            costs.append(value)
        values[first] = float(np.mean(costs))
    bound = len(actions)*samples*(2**remaining-1 if averaged else remaining)
    if reviews > bound:
        raise AssertionError('simulated review bound exceeded')
    detail = dict(candidate_values=values, samples=samples, averaged=averaged,
                  candidates=len(actions), greedy=greedy, simulated_reviews=reviews,
                  posterior_updates=updates, posterior_copies=copies,
                  max_mass_error=max_mass_error, review_bound=bound,
                  world_indices_sha256=hashlib.sha256(worlds.astype('<i8').tobytes()).hexdigest(),
                  posterior_seed_base=seed+100000)
    return min(order, key=values.get), detail


def selector(belief, available, remaining, step, seed, method):
    if method not in ['averaged', 'sampled-control']:
        raise ValueError('unknown outcome-averaged study method')
    action, detail = choose(belief, available, remaining, 128,
                            9100000+seed*100000+step*1000000,
                            method == 'averaged')
    return action, dict(search=detail, simulated_reviews=detail['simulated_reviews'])
