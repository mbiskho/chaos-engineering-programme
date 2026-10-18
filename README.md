# Chaos Engineering Programme

Controlled experiments that check our resilience assumptions before a real outage does. Each experiment is a YAML file with a hypothesis, a steady-state metric, one fault, a blast radius and automatic abort conditions. A small runner executes them against Kubernetes using Chaos Mesh, stops the moment an abort condition trips, and records the result.

```
experiment.yaml ──► 1. steady state holds?   (Prometheus queries)  ── no ──► don't start
                    2. inject fault           (Chaos Mesh resource, scoped by labels + namespace)
                    3. watch for `duration`   every 10s: abort conditions? ── yes ──► remove fault now
                    4. remove fault, wait for recovery
                    5. steady state again?    → result: hypothesis held / refuted / aborted
                                               → results/<experiment>-<time>.json
```

## The rules every experiment follows

- **A written hypothesis.** "When one payments-api pod dies, p99 latency stays under 300 ms and error rate under 1%." Without one it isn't an experiment.
- **Smallest blast radius first.** Staging before production, one pod before a zone, `max_targets` enforced by the runner.
- **Abort conditions are mandatory.** The runner refuses an experiment without at least one, and checks them every 10 seconds.
- **The fault is always removed.** Removal runs in a `finally` block, and Chaos Mesh resources also carry their own `duration`, so a crashed runner still ends the fault.

## Catalog

| Experiment | Fault | Hypothesis |
|---|---|---|
| `pod-kill-payments-api` | kill 1 of N pods | no user-visible errors; HPA/ReplicaSet replaces it in < 60 s |
| `network-latency-db` | +200 ms to Postgres | timeouts and retries keep error rate < 1% |
| `dns-failure-vendor` | DNS errors for the KYC vendor | onboarding degrades gracefully: queued, not failed |
| `az-outage-simulation` | partition one zone's nodes | traffic shifts to remaining zones within SLO |

## Usage

```bash
pip install -e ".[dev]"
chaos validate experiments/                                # schema + safety rules, no cluster needed
chaos run experiments/pod-kill-payments-api.yaml --dry-run # prints the Chaos Mesh resource it would apply
chaos run experiments/pod-kill-payments-api.yaml           # needs kubectl context + PROMETHEUS_URL
```

Game days (a scheduled team exercise running several experiments) use `gamedays/template.md`.

## Layout

```
chaos/spec.py       experiment schema + safety validation
chaos/steady.py     Prometheus queries and threshold evaluation (pure comparison logic)
chaos/faults.py     experiment → Chaos Mesh manifest
chaos/runner.py     the loop: check, inject, watch, remove, verify, record
chaos/cli.py        validate / run
experiments/        the catalog
gamedays/           game day plan and write-up template
```
