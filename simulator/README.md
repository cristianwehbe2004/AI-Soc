# Synthetic Event Simulator

Generate deterministic-shape normal or abnormal ML telemetry and optionally send it to the bulk event API:

```bash
python simulator/cli.py normal-telemetry --count 200 --send
python simulator/cli.py abnormal-telemetry --count 50 --send
```

The simulator also retains the rule and credential-compromise scenarios from earlier sprints.
