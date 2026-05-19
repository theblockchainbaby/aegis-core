# Lifecycle and Supervision

Read this before changing how `aegis-core up` starts, stops, or supervises the organism.

## The half death

`aegis-core up` spawns a `nats-server` subprocess and then runs ten services that all connect to it over the bus. Twice during the dogfood, NATS died while the `up` process kept running. The services retried into a dead socket forever. The process looked alive from the outside, the cockpit even answered `/healthz` with `ok`, but the bus underneath was gone. Nothing surfaced the failure. The operator found out only by noticing error spew or a dead cockpit.

A system that looks alive while disconnected erodes trust faster than any behavior bug. The fix is to make the failure loud.

## The fix

Three changes, all on one principle: a loud full death is recoverable, a silent half death is not.

1. `up` watches NATS. `up` now polls its `nats-server` subprocess. If NATS exits, `up` logs a fatal reason, tears down every child service, and exits with a nonzero code. See `_supervise` in `src/aegis_core/cli.py`.

2. `/healthz` checks the bus. The observer cockpit's `/healthz` endpoint now returns HTTP 503 with `status unhealthy` when the bus is connected but down, instead of always reporting `ok`. It checks `AegisBus.is_connected`, not just whether the web process answers.

3. launchd restarts it. A launchd job at `ops/launchd/com.aegiscore.dogfood.plist` runs `up` with `KeepAlive` true. When `up` exits, for any reason, launchd restarts the whole organism. This is what lets the 90 day dogfood survive unattended. launchd is the supervisor. There is no separate watchdog, by design.

## Running the dogfood under launchd

The plist lives in the repo at `ops/launchd/com.aegiscore.dogfood.plist`. To activate it:

1. Stop any `up` you are running by hand in a Terminal first. Two `up` processes will fight over ports 4222 and 8080.

2. Symlink the plist into LaunchAgents:

       ln -sf /Users/york/aegis-core/ops/launchd/com.aegiscore.dogfood.plist ~/Library/LaunchAgents/com.aegiscore.dogfood.plist

3. Load it:

       launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aegiscore.dogfood.plist

The organism now starts on load, restarts on every exit, and starts again at login. Its output is captured to `dogfood/up.out.log` and `dogfood/up.err.log`.

To check status:

       launchctl print gui/$(id -u)/com.aegiscore.dogfood

To stop it:

       launchctl bootout gui/$(id -u)/com.aegiscore.dogfood

`bootout` removes the job entirely, so `KeepAlive` does not fight it. That is the clean way to take the organism down.

## The sleep and wake question

NATS died twice. A plausible trigger is macOS sleep and wake: the machine sleeps, the `nats-server` process does not survive cleanly, and `up` is left half dead on the next wake.

### Diagnostic finding, 2026-05-19

The `pmset -g log` output reaches back to 2026-05-13, which covers the window of the first observed NATS death around May 14. The log shows frequent sleep and wake activity on those dates, including background maintenance DarkWake cycles and at least one clamshell sleep on the night of May 13. However, the exact time the NATS process died was never recorded anywhere, so there is no specific timestamp to compare against the power log. The finding is inconclusive: sleep and wake events were present near the relevant dates, but without a NATS death timestamp, no correlation can be confirmed or ruled out.

Going forward this is answerable precisely. launchd now captures every `up` death with a timestamp in `dogfood/up.err.log`. The next time NATS dies, compare that timestamp against `pmset -g log` sleep and wake events. If they line up, the durable fix is to also run `nats-server` as its own launchd job rather than as a child of `up`, so each survives independently.
