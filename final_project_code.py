import pyscipopt as scip
import numpy as np
import time
import csv
import os
import argparse
from collections import defaultdict


class PseudocostTracker:
    def __init__(self):
        self.pscost_up = defaultdict(list)
        self.pscost_down = defaultdict(list)
        self.branch_count = defaultdict(int)

    def update(self, var_idx, direction, gain):
        if direction == 'up':
            self.pscost_up[var_idx].append(gain)
        else:
            self.pscost_down[var_idx].append(gain)
        self.branch_count[var_idx] += 1

    def score(self, var_idx, frac_val):
        f = frac_val - int(frac_val)
        avg_up = np.mean(self.pscost_up[var_idx]) if self.pscost_up[var_idx] else 1.0
        avg_down = np.mean(self.pscost_down[var_idx]) if self.pscost_down[var_idx] else 1.0
        score_up = avg_up * (1 - f)
        score_down = avg_down * f
        return max(score_up, 1e-6) * max(score_down, 1e-6)

    def is_reliable(self, var_idx, threshold=8):
        return self.branch_count[var_idx] >= threshold


def get_fractional_vars(model):
    candidates = []
    for var in model.getVars():
        if var.vtype() in ('I', 'B'):
            val = model.getSolVal(None, var)
            frac = val - int(val)
            if 1e-4 < frac < 1 - 1e-4:
                candidates.append((var.getIndex(), var, val))
    return candidates


class RandomBrancher(scip.Branchrule):
    def __init__(self):
        self.log = []

    def branchexeclp(self, allowaddcons):
        model = self.model
        self.log.append((model.getNNodes(), model.getDualbound(), model.getPrimalbound()))
        candidates = get_fractional_vars(model)
        if not candidates:
            return {"result": scip.SCIP_RESULT.DIDNOTRUN}
        _, var, _ = candidates[np.random.randint(len(candidates))]
        model.branchVar(var)
        return {"result": scip.SCIP_RESULT.BRANCHED}


class PseudocostBrancher(scip.Branchrule):
    def __init__(self):
        self.log = []
        self.tracker = PseudocostTracker()
        self.prev_bound = None

    def branchexeclp(self, allowaddcons):
        model = self.model
        obj_bound = model.getDualbound()
        self.log.append((model.getNNodes(), obj_bound, model.getPrimalbound()))
        candidates = get_fractional_vars(model)
        if not candidates:
            return {"result": scip.SCIP_RESULT.DIDNOTRUN}
        if self.prev_bound is not None:
            gain = abs(obj_bound - self.prev_bound)
            for j, var, val in candidates:
                f = val - int(val)
                self.tracker.update(j, 'up' if f >= 0.5 else 'down', gain / max(f, 1e-6))
        self.prev_bound = obj_bound
        _, var, _ = max(candidates, key=lambda x: self.tracker.score(x[0], x[2]))
        model.branchVar(var)
        return {"result": scip.SCIP_RESULT.BRANCHED}


class StrongBrancher(scip.Branchrule):
    def __init__(self, max_candidates=5):
        self.log = []
        self.max_candidates = max_candidates

    def branchexeclp(self, allowaddcons):
        model = self.model
        obj_bound = model.getDualbound()
        self.log.append((model.getNNodes(), obj_bound, model.getPrimalbound()))
        candidates = get_fractional_vars(model)
        if not candidates:
            return {"result": scip.SCIP_RESULT.DIDNOTRUN}
        best_score = -float('inf')
        best_var = None
        for j, var, val in candidates[:self.max_candidates]:
            down_bd, up_bd, down_inf, up_inf, down_obj, up_obj, nsolved = model.getVarStrongbranch(var, 10)
            score = min(abs(down_obj - obj_bound), 1e10) * min(abs(up_obj - obj_bound), 1e10)
            if score > best_score:
                best_score = score
                best_var = var
        model.branchVar(best_var if best_var is not None else candidates[0][1])
        return {"result": scip.SCIP_RESULT.BRANCHED}


class ReliabilityBrancher(scip.Branchrule):
    def __init__(self, reliability_threshold=8):
        self.log = []
        self.tracker = PseudocostTracker()
        self.reliability_threshold = reliability_threshold
        self.prev_bound = None

    def branchexeclp(self, allowaddcons):
        model = self.model
        obj_bound = model.getDualbound()
        self.log.append((model.getNNodes(), obj_bound, model.getPrimalbound()))
        candidates = get_fractional_vars(model)
        if not candidates:
            return {"result": scip.SCIP_RESULT.DIDNOTRUN}
        if self.prev_bound is not None:
            gain = abs(obj_bound - self.prev_bound)
            for j, var, val in candidates:
                f = val - int(val)
                self.tracker.update(j, 'up' if f >= 0.5 else 'down', gain / max(f, 1e-6))
        self.prev_bound = obj_bound
        reliable = [(j, v, val) for j, v, val in candidates if self.tracker.is_reliable(j, self.reliability_threshold)]
        unreliable = [(j, v, val) for j, v, val in candidates if not self.tracker.is_reliable(j, self.reliability_threshold)]
        if unreliable:
            best_var = max(unreliable, key=lambda x: -abs((x[2] - int(x[2])) - 0.5))
        else:
            best_var = max(reliable, key=lambda x: self.tracker.score(x[0], x[2]))
        j, var, val = best_var
        self.tracker.branch_count[j] += 1
        model.branchVar(var)
        return {"result": scip.SCIP_RESULT.BRANCHED}


INSTANCES = [
    "instances/air05.mps",
    "instances/cap6000.mps",
    "instances/fiber.mps",
    "instances/gen.mps",
    "instances/misc07.mps",
]

STRATEGIES = ['default', 'random', 'pseudocost', 'strong', 'reliability']


def make_brancher(strategy):
    if strategy == 'random':
        return RandomBrancher()
    elif strategy == 'pseudocost':
        return PseudocostBrancher()
    elif strategy == 'strong':
        return StrongBrancher()
    elif strategy == 'reliability':
        return ReliabilityBrancher()
    return None


def run_instance(instance_path, strategy, time_limit=600, run_id=0):
    m = scip.Model()
    m.setParam('display/verblevel', 0)
    m.setParam('limits/time', time_limit)
    m.setParam('lp/threads', 1)
    m.setParam('branching/relpscost/priority', -10000000)
    m.setParam('branching/pscost/priority', -10000000)
    m.setParam('branching/random/priority', -10000000)
    m.setParam('branching/mostinf/priority', -10000000)
    m.setParam('branching/leastinf/priority', -10000000)
    m.setParam('branching/fullstrong/priority', -10000000)
    m.setParam('branching/allfullstrong/priority', -10000000)
    m.setParam('branching/cloud/priority', -10000000)
    m.setParam('branching/distribution/priority', -10000000)
    m.setParam('branching/inference/priority', -10000000)
    m.setParam('branching/lookahead/priority', -10000000)
    m.setParam('branching/multaggr/priority', -10000000)
    m.setParam('branching/nodereopt/priority', -10000000)
    m.setParam('branching/vanillafullstrong/priority', -10000000)
    m.readProblem(instance_path)

    if strategy != 'default':
        brancher = make_brancher(strategy)
        m.includeBranchrule(
            brancher,
            f"{strategy}_{run_id}",
            f"{strategy}_{run_id}",
            priority=1000000,
            maxdepth=-1,
            maxbounddist=1.0
        )

    start = time.time()
    m.optimize()
    elapsed = time.time() - start

    nodes = m.getNNodes()
    best = m.getObjVal() if m.getNSols() > 0 else None
    bound = m.getDualbound()
    gap = abs(best - bound) / max(abs(best), 1e-6) if best is not None else float('inf')

    return {
        'strategy': strategy,
        'nodes': nodes,
        'runtime': elapsed,
        'gap': gap,
    }


def already_done(out_path, instance_name, strategy):
    if not os.path.exists(out_path):
        return False
    with open(out_path, 'r') as f:
        for row in csv.DictReader(f):
            if row['instance'] == instance_name and row['strategy'] == strategy:
                return True
    return False


def append_result(out_path, instance_name, strategy, nodes, runtime, gap):
    write_header = not os.path.exists(out_path)
    with open(out_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['instance', 'strategy', 'nodes', 'runtime', 'gap'])
        writer.writerow([instance_name, strategy, nodes, runtime, gap])


def run_strategy(strategy, time_limit=600, out_path="results.csv"):
    print(f"\n=== Running strategy: {strategy} ===")
    for i, instance_path in enumerate(INSTANCES):
        instance_name = instance_path.split('/')[-1].replace('.mps', '')
        if already_done(out_path, instance_name, strategy):
            print(f"  {instance_name}: already done, skipping")
            continue
        print(f"  {instance_name}... ", end='', flush=True)
        res = run_instance(instance_path, strategy, time_limit, run_id=i)
        append_result(out_path, instance_name, strategy, res['nodes'], res['runtime'], res['gap'])
        print(f"nodes={res['nodes']:.0f}  time={res['runtime']:.1f}s  gap={res['gap']:.4f}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--strategy', type=str, choices=STRATEGIES, required=True,
                        help='Which branching strategy to run')
    parser.add_argument('--time_limit', type=int, default=600,
                        help='Time limit per instance in seconds (default: 600)')
    parser.add_argument('--out', type=str, default='results.csv',
                        help='Output CSV file (default: results.csv)')
    args = parser.parse_args()
    run_strategy(args.strategy, time_limit=args.time_limit, out_path=args.out)