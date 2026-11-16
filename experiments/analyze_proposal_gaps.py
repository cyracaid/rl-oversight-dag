"""Frozen development contrasts; reads completed artifacts, never trains models."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

METHODS = ('reinforce', 'ac', 'nstep3', 'nstep5')
CANDIDATES = tuple(f'{v}/{m}' for v in ('observed', 'gain') for m in METHODS)


def validate(data, directory):
    if data.get('status') != 'completed':
        raise ValueError('run is incomplete')
    config = data['config']
    if (config['seeds'] != [1, 2, 3, 4, 5]
            or config['episodes'] != 20000
            or data['graph_seeds'] != list(range(1000, 1200))):
        raise ValueError('run does not match frozen development design')
    if not data['provenance'].get('source_sha256'):
        raise ValueError('missing source hash manifest')
    for confidence in ('normal', 'noise', 'oracle'):
        for schedule in ('matched', 'linear_odds_1_to_2'):
            condition = f'{confidence}/{schedule}'
            rows = data['conditions'][condition]
            if set(rows) != set(CANDIDATES) | {'belief greedy'}:
                raise ValueError(f'missing or unexpected cells: {condition}')
            for name, raw in rows.items():
                shape = (200,) if name == 'belief greedy' else (5, 200)
                array = np.asarray(raw, dtype=float)
                deg = np.asarray(data['degeneracies'][condition][name], dtype=float)
                if (array.shape != shape or not np.isfinite(array).all()
                        or (array < 0).any() or (array != np.floor(array)).any()
                        or deg.shape != shape or not np.isfinite(deg).all()
                        or (deg < 0).any() or (deg != np.floor(deg)).any()):
                    raise ValueError(f'invalid outcomes/degeneracies: {condition}/{name}')
        for candidate in CANDIDATES:
            for seed in config['seeds']:
                stem = f"{confidence}_{candidate.replace('/', '_')}_{seed}"
                name = stem + '.pt'
                expected = data['checkpoints'][name]
                if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                    raise ValueError(f'checkpoint hash mismatch: {name}')
                curve = np.asarray(data['training'][stem]['sink_errors'], dtype=float)
                if (curve.shape != (20000,) or not np.isfinite(curve).all()
                        or (curve < 0).any() or (curve != np.floor(curve)).any()):
                    raise ValueError(f'invalid training curve: {stem}')


def bootstrap(delta, family_size, draws=100000):
    """Crossed seed/graph resampling of already paired differences, in batches."""
    delta = np.asarray(delta, dtype=float)
    if delta.ndim != 2 or not np.isfinite(delta).all() or draws < 1:
        raise ValueError('finite seed-by-graph differences and positive draws required')
    rng = np.random.default_rng(20261112)
    s, g = delta.shape
    samples = np.empty(draws)
    for start in range(0, draws, 512):
        n = min(512, draws-start)
        seeds = rng.integers(s, size=(n, s))
        graphs = rng.integers(g, size=(n, g))
        samples[start:start+n] = delta[seeds[:, :, None], graphs[:, None, :]].mean((1, 2))
    alpha = .05 / family_size
    return {'mean': float(delta.mean()),
            'ci95': np.quantile(samples, [.025, .975]).tolist(),
            'adjusted_ci': np.quantile(samples, [alpha/2, 1-alpha/2]).tolist(),
            'family_size': family_size}


def analyze(data):
    rows = data['conditions']['normal/matched']
    primary = {name: bootstrap(np.asarray(rows[name])-rows['belief greedy'], 8)
               for name in CANDIDATES}
    for result in primary.values():
        result['development_superiority'] = result['adjusted_ci'][1] < 0
    contrasts = [(f'gain/{m}', f'observed/{m}') for m in METHODS]
    contrasts += [(f'{v}/{m}', f'{v}/reinforce')
                  for v in ('observed', 'gain') for m in METHODS[1:]]
    secondary = {f'{a} minus {b}': bootstrap(np.asarray(rows[a])-rows[b], 10)
                 for a, b in contrasts}
    exploratory = {}
    for condition, policies in data['conditions'].items():
        exploratory[condition] = {}
        for name, raw in policies.items():
            array = np.atleast_2d(np.asarray(raw))
            exploratory[condition][name] = {
                'mean': float(array.mean()), 'seed_means': array.mean(1).tolist(),
                'delta_vs_greedy': float((array-policies['belief greedy']).mean()),
                'degeneracy_total': int(np.sum(data['degeneracies'][condition][name])),
                'chronological_means': [float(array[:, a:b].mean())
                                        for a, b in ((0, 50), (50, 150), (150, 200))]}
    selected = min(CANDIDATES, key=lambda name: np.mean(rows[name]))
    return {'primary': primary, 'secondary': secondary, 'all_cells': exploratory,
            'exploratory_candidate': selected, 'confirmation': 'not performed',
            'training_curves': 'Preserved in input results.json; all seeds, all episodes.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    raw = args.results.read_bytes()
    data = json.loads(raw)
    validate(data, args.results.parent)
    report = analyze(data)
    report['input_sha256'] = hashlib.sha256(raw).hexdigest()
    report['protocol_sha256'] = hashlib.sha256(Path(__file__).with_name(
        'PROPOSAL_GAPS_ANALYSIS_PROTOCOL.md').read_bytes()).hexdigest()
    with args.out.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
