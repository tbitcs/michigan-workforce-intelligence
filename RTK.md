# RTK Policy

This project uses Rust Token Killer (RTK) to reduce agent-visible command output. Codex does not have a transparent shell hook, so project instructions explicitly require `rtk <command>` for supported commands.

Setup:

```bash
rtk --version
rtk gain
rtk init --codex
```

Telemetry should remain disabled unless a maintainer opts in. RTK filters are an output optimization only: they must never alter source data, test inputs, database payloads, hashes, or generated reports. If compressed output hides a needed failure detail, inspect RTK's failure tee rather than rerunning a noisy command.
