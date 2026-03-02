import argparse
import copy
import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from scripts_flow.compare_snn_vs_ospf import OSPFSyncSimulator, build_nodes
from scripts_flow.main_snn import build_flow_config, build_snn_runtime_config
from scripts_flow.snn_router import SNNRouter
from scripts_flow.snn_simulator import SNNSimulator
from scripts_flow.traffic import TrafficGenerator


def _parse_edges(raw):
    edges = []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            u, v = int(item[0]), int(item[1])
        elif isinstance(item, dict):
            u, v = int(item["a"]), int(item["b"])
        else:
            continue
        if u == v:
            continue
        if u > v:
            u, v = v, u
        edges.append((u, v))
    return sorted(set(edges))


def load_topology_trace(path):
    trace_path = Path(path)
    if not trace_path.exists():
        raise FileNotFoundError(f"trace file not found: {trace_path}")

    snapshots = []
    if trace_path.suffix.lower() == ".jsonl":
        lines = [ln.strip() for ln in trace_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        for ln in lines:
            obj = json.loads(ln)
            step = int(obj["step"])
            edges = _parse_edges(obj.get("edges", obj.get("links", [])))
            snapshots.append((step, edges))
    else:
        obj = json.loads(trace_path.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            data = obj.get("snapshots", [])
        else:
            data = obj
        for entry in data:
            step = int(entry["step"])
            edges = _parse_edges(entry.get("edges", entry.get("links", [])))
            snapshots.append((step, edges))

    snapshots.sort(key=lambda x: x[0])
    if not snapshots:
        raise ValueError("empty topology trace")
    return snapshots


def infer_num_nodes(snapshots, default_nodes):
    if default_nodes and default_nodes > 0:
        return int(default_nodes)
    max_node = -1
    for _, edges in snapshots:
        for u, v in edges:
            max_node = max(max_node, u, v)
    if max_node < 0:
        raise ValueError("cannot infer node count from empty edges")
    return max_node + 1


def apply_edges(graph, num_nodes, edges):
    graph.clear()
    graph.add_nodes_from(range(num_nodes))
    graph.add_edges_from(edges, cost=1.0)


def summarize(df):
    rows = []
    for algo in sorted(df["algo"].unique()):
        sub = df[df["algo"] == algo]
        last = sub.iloc[-1]
        rows.append(
            {
                "algo": algo,
                "pdr_final": float(last["pdr"]),
                "avg_delay_final": float(last["avg_delay"]),
                "avg_hop_final": float(last["avg_hop"]),
                "loss_final": float(last["loss"]),
                "route_changes_total": float(sub["route_changes"].sum()),
                "table_updates_total": float(sub["table_updates"].sum()),
                "broadcasts_total": float(sub["broadcasts"].sum()),
            }
        )
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Routing-only shadow experiment (SNN vs OSPF Sync).")
    parser.add_argument("--trace", required=True, help="Topology trace file (.json or .jsonl)")
    parser.add_argument("--nodes", type=int, default=0, help="Node count override; 0 means infer from trace")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--steps", type=int, default=0, help="Run steps; 0 means up to last trace step")
    parser.add_argument("--snn-mode", default="snn_event_dv", help="snn_event_dv or snn_spike_native")
    parser.add_argument("--sync-period", type=int, default=12)
    parser.add_argument("--spf-delay", type=int, default=4)
    parser.add_argument("--out", default="run_dir/routing_shadow_steps.csv")
    parser.add_argument("--out-agg", default="run_dir/routing_shadow_summary.csv")
    args = parser.parse_args()

    np.random.seed(args.seed)
    snapshots = load_topology_trace(args.trace)
    num_nodes = infer_num_nodes(snapshots, args.nodes)
    last_step = snapshots[-1][0]
    steps = args.steps if args.steps > 0 else (last_step + 1)

    snapshot_map = {step: edges for step, edges in snapshots}
    current_edges = snapshots[0][1]

    graph_snn = nx.Graph()
    graph_ospf = nx.Graph()
    apply_edges(graph_snn, num_nodes, current_edges)
    apply_edges(graph_ospf, num_nodes, current_edges)

    flow_cfg = build_flow_config(num_nodes=num_nodes, seed=args.seed)
    traffic = TrafficGenerator(flow_cfg)

    cfg = build_snn_runtime_config("ba", args.snn_mode)
    router_kwargs = dict(cfg.get("router", {}))
    router_kwargs["beta_s"] = 8.0
    router = SNNRouter(**router_kwargs)
    sim_kwargs = dict(cfg.get("sim", {}))
    sim_kwargs["known_destinations"] = [f["dst"] for f in flow_cfg]

    snn_sim = SNNSimulator(
        build_nodes(num_nodes, 8.0),
        graph_snn,
        router,
        routing_mode=args.snn_mode,
        **sim_kwargs,
    )
    ospf_sim = OSPFSyncSimulator(
        build_nodes(num_nodes, 0.0),
        graph_ospf,
        hop_limit=64,
        sync_period=args.sync_period,
        spf_delay=args.spf_delay,
    )

    rows = []
    for step in range(steps):
        if step in snapshot_map:
            current_edges = snapshot_map[step]
            apply_edges(graph_snn, num_nodes, current_edges)
            apply_edges(graph_ospf, num_nodes, current_edges)

        packets = traffic.generate(step)
        packets_snn = copy.deepcopy(packets)
        packets_ospf = copy.deepcopy(packets)

        m_snn = snn_sim.run_step(step, packets_snn)
        m_ospf = ospf_sim.run_step(step, packets_ospf)

        rows.append(
            {
                "step": step,
                "algo": "snn",
                "pdr": float(m_snn.get("pdr", 0.0)),
                "avg_delay": float(m_snn.get("avg_delay", 0.0)),
                "avg_hop": float(m_snn.get("avg_hop", 0.0)),
                "loss": float(m_snn.get("loss", 0.0)),
                "route_changes": float(m_snn.get("route_changes", 0.0)),
                "table_updates": float(m_snn.get("table_updates", 0.0)),
                "broadcasts": float(m_snn.get("broadcasts", 0.0)),
            }
        )
        rows.append(
            {
                "step": step,
                "algo": "ospf_sync",
                "pdr": float(m_ospf.get("pdr", 0.0)),
                "avg_delay": float(m_ospf.get("avg_delay", 0.0)),
                "avg_hop": float(m_ospf.get("avg_hop", 0.0)),
                "loss": float(m_ospf.get("loss", 0.0)),
                "route_changes": 0.0,
                "table_updates": float(m_ospf.get("table_updates", 0.0)),
                "broadcasts": float(m_ospf.get("broadcasts", 0.0)),
            }
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)

    agg = summarize(df)
    out_agg = Path(args.out_agg)
    out_agg.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(out_agg, index=False)

    print(f"steps result -> {out_path}")
    print(f"summary result -> {out_agg}")
    print(agg.to_string(index=False))


if __name__ == "__main__":
    main()
