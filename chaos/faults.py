"""Experiment → Chaos Mesh custom resource. Chaos Mesh's own `duration` is a second safety net."""

from __future__ import annotations

from .spec import Experiment


def manifest(e: Experiment, run_id: str) -> dict:
    selector = {"namespaces": [e.namespace], "labelSelectors": e.selector}
    base = {"metadata": {"name": f"{e.name}-{run_id}", "namespace": e.namespace,
                         "labels": {"chaos.programme/experiment": e.name, "chaos.programme/run": run_id}}}
    mode = {"mode": "fixed", "value": str(e.max_targets)}
    duration = f"{e.duration_seconds}s"
    p = e.params
    if e.fault == "pod-kill":
        return {"apiVersion": "chaos-mesh.org/v1alpha1", "kind": "PodChaos", **base,
                "spec": {"action": "pod-kill", "selector": selector, **mode}}
    if e.fault in ("network-delay", "network-partition"):
        spec = {"selector": selector, **mode, "duration": duration, "direction": p.get("direction", "to")}
        if e.fault == "network-delay":
            spec |= {"action": "delay", "delay": {"latency": p.get("latency", "200ms"), "jitter": p.get("jitter", "20ms")}}
        else:
            spec |= {"action": "partition"}
        if "target_selector" in p:
            spec["target"] = {"selector": {"namespaces": [p.get("target_namespace", e.namespace)],
                                           "labelSelectors": p["target_selector"]}, "mode": "all"}
        return {"apiVersion": "chaos-mesh.org/v1alpha1", "kind": "NetworkChaos", **base, "spec": spec}
    if e.fault == "dns-error":
        return {"apiVersion": "chaos-mesh.org/v1alpha1", "kind": "DNSChaos", **base,
                "spec": {"action": "error", "selector": selector, **mode, "duration": duration,
                         "patterns": p.get("patterns", [])}}
    if e.fault == "cpu-stress":
        return {"apiVersion": "chaos-mesh.org/v1alpha1", "kind": "StressChaos", **base,
                "spec": {"selector": selector, **mode, "duration": duration,
                         "stressors": {"cpu": {"workers": p.get("workers", 2), "load": p.get("load", 80)}}}}
    raise ValueError(e.fault)
