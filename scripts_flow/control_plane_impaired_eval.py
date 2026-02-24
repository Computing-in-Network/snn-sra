import argparse
import copy
import re
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Path patch for local package imports.
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from scripts.topo_manager import generate_topology
from scripts_flow.compare_snn_vs_ospf import ECMPSimulator, OSPFSyncSimulator, PPOSimulator, build_nodes
from scripts_flow.main_snn import build_flow_config, build_snn_runtime_config
from scripts_flow.paper_stat_eval import bootstrap_ci, parse_int_ranges, sign_flip_pvalue
from scripts_flow.snn_router import SNNRouter
from scripts_flow.snn_simulator import SNNSimulator
from scripts_flow.traffic import TrafficGenerator


def parse_float_list(spec):
    vals = []
    for part in [x.strip() for x in spec.split(",") if x.strip()]:
        f = float(part)
        if f < 0:
            raise ValueError(f"invalid control-plane loss/drop value: {part}")
        vals.append(f)
    return vals


def build_sim(
    algo,
    topo,
    graph,
    flow_cfg,
    snn_mode,
    broadcast_loss=0.0,
    broadcast_delay=0,
    min_broadcast_period=1,
    route_ttl=40,
    seed=None,
):
    n = graph.number_of_nodes()
    if algo == "v1":
        cfg = build_snn_runtime_config(topo, snn_mode)
        cfg["sim"]["event_max_period"] = 9999
        router_kwargs = dict(cfg.get("router", {}))
        router_kwargs["beta_s"] = 8.0
        router = SNNRouter(**router_kwargs)
        sim_kwargs = dict(cfg.get("sim", {}))
        sim_kwargs["known_destinations"] = [f["dst"] for f in flow_cfg]
        sim_kwargs["control_broadcast_loss"] = float(broadcast_loss)
        sim_kwargs["control_broadcast_delay"] = int(broadcast_delay)
        sim_kwargs["control_min_broadcast_period"] = int(min_broadcast_period)
        sim_kwargs["route_ttl"] = int(route_ttl)
        return SNNSimulator(build_nodes(n, 8.0), graph, router, routing_mode=snn_mode, **sim_kwargs)

    if algo == "v2":
        cfg = build_snn_runtime_config(topo, snn_mode, formula_mode="v2")
        router_kwargs = dict(cfg.get("router", {}))
        router_kwargs["beta_s"] = 8.0
        router = SNNRouter(**router_kwargs)
        sim_kwargs = dict(cfg.get("sim", {}))
        sim_kwargs["known_destinations"] = [f["dst"] for f in flow_cfg]
        sim_kwargs["control_broadcast_loss"] = float(broadcast_loss)
        sim_kwargs["control_broadcast_delay"] = int(broadcast_delay)
        sim_kwargs["control_min_broadcast_period"] = int(min_broadcast_period)
        sim_kwargs["route_ttl"] = int(route_ttl)
        return SNNSimulator(build_nodes(n, 8.0), graph, router, routing_mode=snn_mode, **sim_kwargs)

    if algo == "ospf_sync":
        # Approximate control impairments by slowing OSPF SPF synchronization.
        sync_period = 12 + max(0, int(min_broadcast_period) - 1)
        spf_delay = 4 + int(round(float(broadcast_delay) * 0.8)) + int(round(float(broadcast_loss) * 20))
        return OSPFSyncSimulator(
            build_nodes(n, 0.0),
            graph,
            hop_limit=64,
            sync_period=sync_period,
            spf_delay=spf_delay,
        )

    if algo == "ecmp":
        return ECMPSimulator(build_nodes(n, 0.0), graph, hop_limit=64)

    if algo == "ppo":
        return PPOSimulator(build_nodes(n, 0.0), graph, hop_limit=64, seed=seed or 7, train=True)

    raise ValueError(f"Unsupported algo: {algo}")


def run_case(
    algo,
    topo,
    seed,
    num_nodes,
    steps,
    er_p,
    ba_m,
    snn_mode,
    broadcast_loss,
    broadcast_delay,
    min_broadcast_period,
    route_ttl,
):
    random.seed(seed)
    np.random.seed(seed)

    graph = generate_topology(kind=topo, num_nodes=num_nodes, seed=seed, er_p=er_p, ba_m=ba_m)
    flow_cfg = build_flow_config(num_nodes=num_nodes, seed=seed)
    traffic = TrafficGenerator(flow_cfg)
    sim = build_sim(
        algo=algo,
        topo=topo,
        graph=copy.deepcopy(graph),
        flow_cfg=flow_cfg,
        snn_mode=snn_mode,
        broadcast_loss=broadcast_loss,
        broadcast_delay=int(broadcast_delay),
        min_broadcast_period=int(min_broadcast_period),
        route_ttl=int(route_ttl),
        seed=seed,
    )

    rows = []
    for t in range(steps):
        metrics = sim.run_step(t, traffic.generate(t))
        metrics["step"] = int(t)
        rows.append(metrics)

    df = pd.DataFrame(rows)
    final = df.iloc[-1]
    tail = df.tail(min(60, len(df)))

    return {
        "issue": 16,
        "algo": algo,
        "topo": topo,
        "size": int(num_nodes),
        "seed": int(seed),
        "broadcast_loss": float(broadcast_loss),
        "broadcast_delay": int(broadcast_delay),
        "min_broadcast_period": int(min_broadcast_period),
        "route_ttl": int(route_ttl),
        "pdr_final": float(final.pdr),
        "delay_final": float(final.avg_delay),
        "hop_final": float(final.avg_hop),
        "loss_final": float(final.loss),
        "pdr_post": float(tail.pdr.mean()),
        "delay_post": float(tail.avg_delay.mean()),
        "route_changes_final": float(final.route_changes),
        "broadcasts_final": float(final.broadcasts),
        "table_updates_final": float(final.table_updates),
    }


def build_group_summary(runs_df):
    metric_cols = [
        "pdr_final",
        "delay_final",
        "hop_final",
        "loss_final",
        "pdr_post",
        "delay_post",
        "route_changes_final",
        "broadcasts_final",
        "table_updates_final",
    ]
    keys = [
        "topo",
        "size",
        "broadcast_loss",
        "broadcast_delay",
        "min_broadcast_period",
        "route_ttl",
        "algo",
    ]
    rows = []
    for key, g in runs_df.groupby(keys):
        row = {keys[i]: key[i] for i in range(len(keys))}
        row["n"] = int(len(g))
        for m in metric_cols:
            arr = g[m].to_numpy(dtype=float)
            arr = arr[np.isfinite(arr)]
            row[f"{m}_mean"] = float(np.mean(arr)) if arr.size else float("nan")
            row[f"{m}_std"] = float(np.std(arr, ddof=1)) if arr.size > 1 else float("nan")
            lo, hi = bootstrap_ci(arr, rng=np.random.default_rng(20260224), n_boot=1000, alpha=0.05)
            row[f"{m}_ci95_lo"] = lo
            row[f"{m}_ci95_hi"] = hi
        rows.append(row)
    return pd.DataFrame(rows)


def build_significance(runs_df):
    metric_cols = [
        "pdr_final",
        "delay_final",
        "hop_final",
        "loss_final",
        "pdr_post",
        "delay_post",
        "route_changes_final",
        "broadcasts_final",
        "table_updates_final",
    ]
    keys = [
        "topo",
        "size",
        "broadcast_loss",
        "broadcast_delay",
        "min_broadcast_period",
        "route_ttl",
    ]
    rows = []
    for key, g in runs_df.groupby(keys):
        base = g[g.algo == "v1"]
        if base.empty:
            base = g[g.algo == "v2"]
        if base.empty:
            continue
        for target in sorted(set(g.algo) - set(base.algo.unique())):
            tdf = g[g.algo == target]
            merged = tdf.merge(
                base,
                on=["seed", "topo", "size", "broadcast_loss", "broadcast_delay", "min_broadcast_period", "route_ttl"],
                suffixes=("_target", "_base"),
            )
            if merged.empty:
                continue
            for m in metric_cols:
                d = (merged[f"{m}_target"] - merged[f"{m}_base"]).to_numpy(dtype=float)
                d = d[np.isfinite(d)]
                if d.size == 0:
                    continue
                lo, hi = bootstrap_ci(d, rng=np.random.default_rng(20260224), n_boot=2000, alpha=0.05)
                p = sign_flip_pvalue(d, rng=np.random.default_rng(20260224), n_perm=4000)
                rows.append(
                    {
                        "topo": key[0],
                        "size": key[1],
                        "broadcast_loss": key[2],
                        "broadcast_delay": key[3],
                        "min_broadcast_period": key[4],
                        "route_ttl": key[5],
                        "base_algo": base.algo.iloc[0],
                        "target_algo": target,
                        "metric": m,
                        "n_pairs": int(len(d)),
                        "mean_diff_target_minus_base": float(np.mean(d)),
                        "ci95_lo": lo,
                        "ci95_hi": hi,
                        "p_value_two_sided": p,
                    }
                )
    return pd.DataFrame(rows)


def build_cp_boundary(sig_df):
    if sig_df.empty:
        return pd.DataFrame(columns=[
            "topo",
            "size",
            "broadcast_loss",
            "broadcast_delay",
            "min_broadcast_period",
            "route_ttl",
            "target_algo",
            "robust_ratio",
            "status",
        ])

    rows = []
    key_fields = [
        "topo",
        "size",
        "broadcast_loss",
        "broadcast_delay",
        "min_broadcast_period",
        "route_ttl",
        "target_algo",
    ]
    for key, g in sig_df[sig_df.metric == "pdr_final"].groupby(key_fields):
        robust = int(((g.mean_diff_target_minus_base > 0) & (g.p_value_two_sided < 0.05)).sum())
        total = int(len(g))
        ratio = robust / max(total, 1)
        if ratio >= 0.70:
            status = "robust"
        elif ratio >= 0.40:
            status = "weakened"
        else:
            status = "failed"
        rows.append(
            {
                "topo": key[0],
                "size": key[1],
                "broadcast_loss": key[2],
                "broadcast_delay": key[3],
                "min_broadcast_period": key[4],
                "route_ttl": key[5],
                "target_algo": key[6],
                "robust_ratio": ratio,
                "robust_count": robust,
                "total_count": total,
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Control-plane impaired routing robustness evaluation.")
    parser.add_argument("--algos", default="v1,v2,ospf_sync,ecmp,ppo")
    parser.add_argument("--topos", default="ba,er")
    parser.add_argument("--sizes", default="50,100")
    parser.add_argument("--seeds", default="1-5")
    parser.add_argument("--broadcast-losses", default="0,0.05,0.10,0.20")
    parser.add_argument("--broadcast-delays", default="0,2,5,10")
    parser.add_argument("--min-broadcast-periods", default="1,3,6")
    parser.add_argument("--route-ttls", default="20,40,80")
    parser.add_argument("--steps", type=int, default=220)
    parser.add_argument("--er-p", type=float, default=0.06)
    parser.add_argument("--ba-m", type=int, default=3)
    parser.add_argument("--snn-mode", default="snn_event_dv")
    parser.add_argument("--out-prefix", default="run_dir/issue16_cp_impaired")
    parser.add_argument("--random-seed", type=int, default=20260224)
    args = parser.parse_args()

    algos = [x.strip() for x in args.algos.split(",") if x.strip()]
    topos = [x.strip() for x in args.topos.split(",") if x.strip()]
    sizes = parse_int_ranges(args.sizes)
    seeds = parse_int_ranges(args.seeds)
    losses = parse_float_list(args.broadcast_losses.replace("_", "."))
    delays = parse_int_ranges(args.broadcast_delays)
    periods = parse_int_ranges(args.min_broadcast_periods)
    ttls = parse_int_ranges(args.route_ttls)

    valid = {"v1", "v2", "ospf_sync", "ecmp", "ppo"}
    invalid = [a for a in algos if a not in valid]
    if invalid:
        raise ValueError(f"Unsupported algos: {invalid}")

    np.random.seed(args.random_seed)
    rows = []
    for topo in topos:
        for size in sizes:
            for seed in seeds:
                for loss in losses:
                    for delay in delays:
                        for period in periods:
                            for ttl in ttls:
                                for algo in algos:
                                    rows.append(
                                        run_case(
                                            algo=algo,
                                            topo=topo,
                                            seed=seed,
                                            num_nodes=size,
                                            steps=args.steps,
                                            er_p=args.er_p,
                                            ba_m=args.ba_m,
                                            snn_mode=args.snn_mode,
                                            broadcast_loss=loss,
                                            broadcast_delay=delay,
                                            min_broadcast_period=period,
                                            route_ttl=ttl,
                                        )
                                    )

    runs_df = pd.DataFrame(rows)
    summary_df = build_group_summary(runs_df)
    sig_df = build_significance(runs_df)
    boundary_df = build_cp_boundary(sig_df)

    runs_prefix = Path(args.out_prefix)
    runs_prefix.parent.mkdir(parents=True, exist_ok=True)
    run_path = f"{args.out_prefix}_cp_impaired_runs.csv"
    summary_path = f"{args.out_prefix}_cp_impaired_summary.csv"
    sig_path = f"{args.out_prefix}_cp_impaired_significance.csv"
    boundary_path = f"{args.out_prefix}_cp_boundary.csv"

    runs_df.to_csv(run_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    sig_df.to_csv(sig_path, index=False)
    boundary_df.to_csv(boundary_path, index=False)

    print(f"Saved: {run_path}")
    print(f"Saved: {summary_path}")
    print(f"Saved: {sig_path}")
    print(f"Saved: {boundary_path}")


if __name__ == "__main__":
    main()
