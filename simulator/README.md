# Synthetic Event Simulator

Generate deterministic-shape normal or abnormal ML telemetry and optionally send it to the bulk event API:

```bash
export AI_SOC_API_KEY='aisoc_prefix_secret'
python simulator/cli.py normal-telemetry --count 200 --send
python simulator/cli.py abnormal-telemetry --count 50 --send
```

Create an `events:write` key through the administrator API first. The simulator
also retains the rule and credential-compromise scenarios from earlier sprints.
