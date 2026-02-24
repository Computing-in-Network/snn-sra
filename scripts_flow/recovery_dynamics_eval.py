import argparse
import copy
import random
import re
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

# Path patch for local package imports.
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from scripts.topo_manager import generate_topology
from scripts_flow.compare_snn_vs_ospf import OSPFSyncSimulator, ECMPSimulator, OSPFSimulator, PPOSimulator
from scripts_flow.main_snn import build_flow_config, build_snn_runtime_config, choose_failure_edge
from scripts_flow.snn_router import SNNRouter
from scripts_flow.snn_simulator import SNNSimulator
from scripts_flow.traffic import TrafficGenerator


def parse_int_ranges(spec):
    vals = []
    for part in [x.strip() for x in spec.split(",") if x.strip()]:
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= b:
                vals.extend(range(a, b + 1))
            else:
                vals.extend(range(a, b - 1, -1))
        else:
            vals.append(int(part))
    return vals


def choose_failure_edges_multi(graph, k):
    g = graph.copy()
    out = []
    for _ in range(k):
        if g.number_of_edges() <= 0:
            break
        edge_bc = nx.edge_betweenness_centrality(g)
        edge = max(edge_bc.items(), key=lambda kv: kv[1])[0]
        edge = (int(edge[0]), int(edge[1]))
        out.append(edge)
        if g.has_edge(*edge):
            g.remove_edge(*edge)
    return out


def make_sim(algo, topo, graph, flow_cfg, snn_mode):
    n = graph.number_of_nodes()
    if algo == "v1":
        return make_snn_sim(topo, graph, flow_cfg, "distance_vector")
    if algo == "v2":
        return make_snn_sim(topo, graph, flow_cfg, "snn_event_dv")
    if algo == "v1_legacy":
        return make_snn_sim(topo, graph, flow_cfg, "distance_vector")
    if algo == "ospf_sync":
        return OSPFSyncSimulator(build_nodes(n), graph, hop_limit=64, sync_period=12, spf_delay=4)
    if algo == "ecmp":
        return ECMPSimulator(build_nodes(n), graph, hop_limit=64)
    if algo == "ppo":
        return PPOSimulator(build_nodes(n), graph, hop_limit=64, seed=7, train=True)
    if algo == "snn":
        return make_snn_sim(topo, graph, flow_cfg, snn_mode)
    raise ValueError(f"Unsupported algo: {algo}")


def build_nodes(num_nodes, queue_size=8.0):
    from scripts_flow.snn_node import SNNQueueNode

    return {
        i: SNNQueueNode(node_id=i, service_rate=22, buffer_size=180, alpha=0.22, beta_I=beta, T_d=1, tau_m=4.0, v_th=1.0)
        for i, beta in [(i, float(queue_size)) for i in range(num_nodes)]
    }


def make_snn_sim(topo, graph, flow_cfg, snn_mode):
    cfg = build_snn_runtime_config(topo, snn_mode)
    router_kwargs = dict(cfg.get("router", {}))
    router_kwargs["beta_s"] = 8.0
    router = SNNRouter(**router_kwargs)
    sim_kwargs = dict(cfg.get("sim", {}))
    sim_kwargs["known_destinations"] = [f["dst"] for f in flow_cfg]
    return SNNSimulator(build_nodes(graph.number_of_nodes(), 8.0), graph, router, routing_mode=snn_mode, **sim_kwargs)


def crossing_step(steps, ratio, threshold):
    for step, val in zip(steps, ratio):
        if np.isfinite(val) and val >= threshold:
            return int(step - steps[0])
    return float("nan")


def compute_recovery_metrics(df, fail_step, pre_window=20):
    pre_mask = df["step"] < fail_step
    if not pre_mask.any() or pre_mask.sum() == 0:
        baseline = float("nan")
    else:
        baseline = df.loc[pre_mask, "pdr"].tail(pre_window).mean()
        baseline = float(baseline)

    fail_mask = df["step"] >= fail_step
    if not fail_mask.any():
        fail_step = int(df["step"].iloc[-1])
        fail_mask = df["step"] >= fail_step

    steps = df.loc[fail_mask, "step"].to_numpy(dtype=int)
    pdr_after = df.loc[fail_mask, "pdr"].to_numpy(dtype=float)

    if not np.isfinite(baseline) or baseline <= 0:
        max_drop = float("nan")
        t50 = float("nan")
        t90 = float("nan")
        auc = float("nan")
        return baseline, max_drop, t50, t90, auc

    min_after = float(np.nanmin(pdr_after)) if pdr_after.size else float("nan")
    max_drop = 100.0 * (baseline - min_after) / baseline

    ratio = pdr_after / baseline if pdr_after.size else np.array([])
    t50 = crossing_step(steps, ratio, 0.5)
    t90 = crossing_step(steps, ratio, 0.9)

    if pdr_after.size == 0:
        auc = float("nan")
    else:
        clipped = np.clip(ratio, 0.0, 1.0)
        x = np.arange(len(clipped), dtype=float)
        auc = float(np.trapz(clipped, x=x) / max(1, len(clipped)))

    return baseline, max_drop, t50, t90, auc


def run_case(
    algo,
    topo,
    seed,
    num_nodes,
    steps,
    fail_step,
    failure_profile,
    er_p,
    ba_m,
    snn_mode,
    pre_window,
):
    random.seed(seed)
    np.random.seed(seed)

    graph0 = generate_topology(kind=topo, num_nodes=num_nodes, seed=seed, er_p=er_p, ba_m=ba_m)
    flow_cfg = build_flow_config(num_nodes=num_nodes, seed=seed)
    traffic = TrafficGenerator(flow_cfg)

    if failure_profile == "single":
        fail_steps = [int(fail_step)]
    elif failure_profile == "frequent":
        fail_steps = [int(fail_step - 30), int(fail_step), int(fail_step + 30), int(fail_step + 60)]
    elif failure_profile == "multi":
        fail_steps = [int(fail_step), int(fail_step + 24), int(fail_step + 48)]
    else:
        raise ValueError(f"Unsupported failure profile: {failure_profile}")

    fail_steps = sorted({x for x in fail_steps if 0 <= x < steps})
    if len(fail_steps) <= 1:
        e = choose_failure_edge(graph0)
        fail_edges = [e] if e is not None else []
    else:
        fail_edges = choose_failure_edges_multi(graph0, len(fail_steps))

    graph = copy.deepcopy(graph0)
    sim = make_sim(algo, topo, graph, flow_cfg, snn_mode)

    history = []
    fi = 0
    for k in range(steps):
        while fi < len(fail_steps) and k == fail_steps[fi]:
            if fi < len(fail_edges):
                e = fail_edges[fi]
                if e is not None and graph.has_edge(*e):
                    graph.remove_edge(*e)
            fi += 1

        metrics = sim.run_step(k, traffic.generate(k))
        metrics["step"] = k
        metrics["failure_profile"] = failure_profile
        history.append(metrics)

    if hasattr(sim, "finalize"):
        sim.finalize()

    df = pd.DataFrame(history)
    final = df.iloc[-1]
    last_fail = fail_steps[-1] if fail_steps else fail_step
    baseline, max_drop, t50, t90, auc = compute_recovery_metrics(df, last_fail, pre_window=pre_window)

    return {
        "algo": algo,
        "topo": topo,
        "size": int(num_nodes),
        "seed": int(seed),
        "failure_profile": failure_profile,
        "fail_step": int(last_fail),
        "baseline_pdr": float(baseline),
        "max_drop_pct": float(max_drop),
        "t50_steps": float(t50),
        "t90_steps": float(t90),
        "auc_recovery": float(auc),
        "pdr_final": float(final.pdr),
    }


def build_group_summary(runs_df):
    metric_cols = ["baseline_pdr", "max_drop_pct", "t50_steps", "t90_steps", "auc_recovery", "pdr_final"]
    rows = []
    keys = ["topo", "size", "failure_profile", "algo"]
    for key, group in runs_df.groupby(keys):
        row = {keys[i]: key[i] for i in range(len(keys))}
        row["n"] = int(len(group))
        for m in metric_cols:
            vals = group[m].to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            row[f"{m}_mean"] = float(np.mean(vals)) if vals.size else float("nan")
            row[f"{m}_std"] = float(np.std(vals, ddof=1)) if vals.size > 1 else float("nan")
            row[f"{m}_median"] = float(np.median(vals)) if vals.size else float("nan")
        rows.append(row)
    return pd.DataFrame(rows).sort_values(keys).reset_index(drop=True)


def bootstrap_ci(values, rng, n_boot=1000, alpha=0.05):
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan"), float("nan")
    if arr.size == 1:
        x = float(arr[0])
        return x, x
    idx = rng.integers(0, arr.size, size=(n_boot, arr.size))
    means = arr[idx].mean(axis=1)
    lo = float(np.quantile(means, alpha / 2.0))
    hi = float(np.quantile(means, 1.0 - alpha / 2.0))
    return lo, hi


def sign_flip_pvalue(diffs, rng, n_perm=10000):
    arr = np.asarray(diffs, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    obs = abs(float(np.mean(arr)))
    if arr.size <= 12:
        from itertools import product

        signs = np.array(list(product([-1.0, 1.0], repeat=arr.size)))
        vals = np.abs((signs * arr).mean(axis=1))
        p = (np.sum(vals >= obs) + 1.0) / (vals.size + 1.0)
        return float(p)

    signs = rng.choice([-1.0, 1.0], size=(n_perm, arr.size))
    vals = np.abs((signs * arr).mean(axis=1))
    p = (np.sum(vals >= obs) + 1.0) / (n_perm + 1.0)
    return float(p)


def build_recovery_significance(runs_df, base_algo="v1", rng=None):
    if rng is None:
        rng = np.random.default_rng(20260224)

    metric_cols = ["max_drop_pct", "t50_steps", "t90_steps", "auc_recovery", "pdr_final"]
    rows = []
    keys = ["topo", "size", "failure_profile"]
    for key, group in runs_df.groupby(keys):
        base = group[group["algo"] == base_algo]
        if base.empty:
            continue

        for target_algo in sorted(group["algo"].unique()):
            if target_algo == base_algo:
                continue
            var = group[group["algo"] == target_algo]
            if var.empty:
                continue

            merged = var.merge(base, on=["seed", "topo", "size", "failure_profile"], suffixes=("_target", "_base"))
            if merged.empty:
                continue

            for m in metric_cols:
                diffs = (merged[f"{m}_target"] - merged[f"{m}_base"]).to_numpy(dtype=float)
                diffs = diffs[np.isfinite(diffs)]
                if diffs.size == 0:
                    continue
                lo, hi = bootstrap_ci(diffs, rng=rng, n_boot=2000, alpha=0.05)
                p = sign_flip_pvalue(diffs, rng=rng, n_perm=2000)
                rows.append(
                    {
                        "topo": key[0],
                        "size": key[1],
                        "failure_profile": key[2],
                        "base_algo": base_algo,
                        "target_algo": target_algo,
                        "metric": m,
                        "n_pairs": int(len(diffs)),
                        "mean_diff_target_minus_base": float(np.mean(diffs)),
                        "ci95_lo": lo,
                        "ci95_hi": hi,
                        "p_value_two_sided": p,
                    }
                )
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Evaluate recovery dynamics (MaxDrop, T50/T90, AUC) after failures.")
    parser.add_argument("--algos", default="v1,v2,ospf_sync,ecmp,ppo")
    parser.add_argument("--topos", default="ba,er")
    parser.add_argument("--sizes", default="50,100")
    parser.add_argument("--seeds", default="1-20")
    parser.add_argument("--steps", type=int, default=240)
    parser.add_argument("--fail-step", type=int, default=150)
    parser.add_argument("--failure-profiles", default="single")
    parser.add_argument("--pre-window", type=int, default=20)
    parser.add_argument("--er-p", type=float, default=0.06)
    parser.add_argument("--ba-m", type=int, default=3)
    parser.add_argument("--snn-mode", default="snn_event_dv")
    parser.add_argument("--out-prefix", default="run_dir/issue14_recovery")
    parser.add_argument("--out-dir", default="run_dir", help="Backward-compatible alias not used now")
    parser.add_argument("--random-seed", type=int, default=20260224)
    args = parser.parse_args()

    algos = [x.strip() for x in args.algos.split(",") if x.strip()]
    topos = [x.strip() for x in args.topos.split(",") if x.strip()]
    sizes = parse_int_ranges(args.sizes)
    seeds = parse_int_ranges(args.seeds)
    failure_profiles = [x.strip() for x in args.failure_profiles.split(",") if x.strip()]

    valid = {"v1", "v2", "ospf", "ospf_sync", "ecmp", "ppo", "snn", "v1_legacy"}
    invalid = [a for a in algos if a not in valid]
    if invalid:
        raise ValueError(f"Unsupported algos: {invalid}")

    run_rows = []
    total = len(topos) * len(sizes) * len(seeds) * len(failure_profiles) * len(algos)
    done = 0
    for topo in topos:
        for size in sizes:
            for profile in failure_profiles:
                for seed in seeds:
                    for algo in algos:
                        done += 1
                        print(
                            f"[{done:04d}/{total:04d}] topo={topo} size={size} profile={profile} seed={seed} algo={algo}",
                            flush=True,
                        )
                        run_rows.append(
                            run_case(
                                algo=algo,
                                topo=topo,
                                seed=seed,
                                num_nodes=size,
                                steps=args.steps,
                                fail_step=args.fail_step,
                                failure_profile=profile,
                                er_p=args.er_p,
                                ba_m=args.ba_m,
                                snn_mode=args.snn_mode,
                                pre_window=args.pre_window,
                            )
                        )

    runs_df = pd.DataFrame(run_rows)
    runs_path = Path(f"{args.out_prefix}_recovery_runs.csv")
    summary_path = Path(f"{args.out_prefix}_recovery_summary.csv")
    sig_path = Path(f"{args.out_prefix}_recovery_significance.csv")
    runs_path.parent.mkdir(parents=True, exist_ok=True)

    runs_df.to_csv(runs_path, index=False)
    summary_df = build_group_summary(runs_df)
    summary_df.to_csv(summary_path, index=False)
    sig_df = build_recovery_significance(runs_df, base_algo="v1", rng=np.random.default_rng(args.random_seed))
    sig_df.to_csv(sig_path, index=False)

    print("Saved:", runs_path)
    print("Saved:", summary_path)
    print("Saved:", sig_path)


if __name__ == "__main__":
    main()
