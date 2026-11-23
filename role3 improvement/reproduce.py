"""Rebuild v3 results on CPU using separate training, validation and test seeds."""
import subprocess
import sys
from pathlib import Path


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True)


if __name__ == "__main__":
    out = Path('outputs/v3')
    out.mkdir(parents=True, exist_ok=True)
    checkpoints = []
    for seed in (1, 2, 3):
        folder = out / f'train_{seed}'
        run('train_gnn.py', '--episodes', 1000, '--eval-seeds', 30, '--seed', seed, '--out', folder)
        run('train_dqn.py', '--episodes', 300, '--eval-seeds', 30, '--seed', seed, '--out', folder)
        checkpoints.extend([folder/'dqn_spike.pt', folder/'gnn_spike_observed.pt'])
    run('run_benchmark.py', '--seeds', 100, '--checkpoints', *checkpoints, '--out', out)
    run('compare_beliefs.py', '--seeds', 100, '--out', out)
    previous = [Path('outputs')/f'train_{seed}'/name for seed in (1,2,3)
                for name in ('dqn_spike.pt', 'gnn_spike_observed.pt')]
    run('run_benchmark.py', '--families', 'spike', '--seeds', 100,
        '--checkpoints', *previous, '--out', out/'previous_checkpoints')
    run('run_demo.py', '--family', 'real', '--policy', 'marginal', '--particles', 1024,
        '--out', out/'particle_demo')
    with (out/'tests.txt').open('w') as stream:
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
