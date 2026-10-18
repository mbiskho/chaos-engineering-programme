from pathlib import Path

from chaos.faults import manifest
from chaos.spec import Condition, Experiment, load, validate
from chaos.steady import holds

EXPERIMENTS = Path(__file__).resolve().parents[1] / "experiments"


def exp(**kw):
    base = dict(name="x", hypothesis="error rate stays below one percent during the fault", environment="staging",
                namespace="ns", selector={"app": "a"}, fault="pod-kill", owner="me",
                steady_state=[Condition("ok", "q", "<", 1)], abort_if=[Condition("bad", "q", ">", 5)])
    return Experiment(**{**base, **kw})


def test_catalog_is_valid():
    for f in EXPERIMENTS.glob("*.yaml"):
        load(f)


def test_safety_rules():
    assert validate(exp()) == []
    assert any("abort_if" in p for p in validate(exp(abort_if=[])))
    assert any("selector" in p for p in validate(exp(selector={})))
    assert any("production" in p for p in validate(exp(environment="production", max_targets=3)))


def test_no_data_never_counts_as_holding():
    assert not holds(Condition("c", "q", "<", 1), None)
    assert holds(Condition("c", "q", "<", 1), 0.5)


def test_manifest_scoping():
    m = manifest(exp(fault="network-delay", params={"latency": "100ms"}, max_targets=1), "r1")
    assert m["kind"] == "NetworkChaos" and m["spec"]["selector"]["labelSelectors"] == {"app": "a"}
    assert m["spec"]["value"] == "1" and m["spec"]["duration"] == "120s"
