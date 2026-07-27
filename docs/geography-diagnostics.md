# Geography payload diagnostics

LeadMap keeps the checksum-addressed canonical geography artifact unchanged for source fidelity and boundary assignment. The map workspace uses a deterministic simplified representation for rendering.

Use the diagnostics command to compare both representations without modifying either file:

```powershell
python .\scripts\geography-diagnostics.py `
  .\data\geography\<checksum>.json `
  --output .\artifacts\geography-diagnostics.json
```

Omit `--output` to print the JSON report to stdout.

The report includes:

- canonical checksum and feature count;
- canonical and map JSON byte sizes;
- canonical and map coordinate counts;
- byte and coordinate reduction percentages;
- configured simplification tolerance;
- derivation duration in milliseconds.

The duration is informational. It is not compared with a hard threshold because workstation, filesystem and runtime conditions vary. For regression review, compare reports produced on equivalent environments and pay particular attention to byte size, coordinate count, feature count and identifiers.

The command performs no network access, collects no telemetry and never rewrites the canonical artifact. Invalid or unsupported geometry fails closed.
