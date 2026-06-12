# Aegis Core dogfood observations

Started 2026.05.13. Day 1 of 90.

Field notes. Not tickets, not feature requests, not engineering tasks. Append only. Raw.

Each entry: timestamp, situation, what it did, reaction, classification.

**Classes:** timing / restraint / continuity / repetition / tone / presence

**Discipline:** one observation is noise. Wait for a cluster of roughly 5 in the same class before changing anything. When a cluster forms, replay through the canonical cycle harness before touching live rules.

***

## 2026.05.13 11:53 PDT · presence

**Situation:** Cold start of `aegis-core up` immediately after `dogfood start`.
**What it did:** Boot produced roughly 9 full Python stack traces (services racing NATS startup) before stabilizing. Then went silent.
**Reaction:** Felt like the organism crashed instead of waking. Awakening should breathe, not traceback.
**Note:** Likely fix when cluster forms. A NATS readiness probe before service start, or quieter retry backoff.

## 2026.05.13 11:53 PDT · presence

**Situation:** First look at cockpit at `http://127.0.0.1:8080/` after cold start.
**What it did:** Showed "No presence state recorded yet" plus "(silence)" plus 0 aired and 0 vetoed.
**Reaction:** Organism has no perceptual inputs at all on this hardware. The `senses.no_sources_configured` warning fired at boot. Without senses there are no state changes, no proposals, no restraint activity. Cockpit will stay silent except for scheduler firings.
**Note:** If by end of week the only entries are scheduler driven, this becomes a structural finding: the system needs at least one perceptual input source before it can be dogfooded.

## 2026.05.13 11:53 PDT · presence

**Situation:** Reading `rules/schedule.yaml` against the Plan F scheduler implementation.
**What it did:** YAML comment says "All times are local 24h" but `scheduler.py` calls `datetime.now(UTC)`, so times are effectively UTC.
**Reaction:** For PDT, `morning_reflection: 09:00` UTC is 02:00 local (sleep), `evening_reflection: 18:00` UTC is 11:00 local (already passed today). The scheduler's idea of "morning" is not the operator's.
**Note:** Likely fix when cluster forms. Either localize the parse or rename keys to UTC explicitly. Minor change, rule layer only.

***

## 2026.05.14 15:05 PDT · presence

**Situation:** Day 2 of 90. Asked the first look question after 21 hours of ambient run. Cockpit was running, scheduler had fired 4 times on time (Wed 22:00, Thu 07:00, 18:00, 22:00 UTC), state cleanly transitioned through sleep, dormant, reflective, sleep.
**What it did:** Operated invisibly for a full day. No notifications, no sounds, no visual pull.
**Reaction:** "I didn't notice anything."
**Note:** Ambiguous signal. Could be presence working as designed (principle 10: comfortable to ignore; principle 19: never compete for attention) OR functionally absent (no senses, no voice, only silent state transitions in a browser tab, so there is literally nothing to notice). The diagnostic question for tomorrow: would I have noticed if `up` had crashed and the cockpit died? If yes, ambient. If no, invisible.

## 2026.05.14 evening PDT · presence

**Situation:** Tried to open the cockpit in Safari after finishing the host activity sensor. Safari could not connect.
**What it did:** The `up` process (pid 37169, alive since the 2026.05.13 launch) was still running, but its NATS subprocess had died and port 8080 was no longer listening. The organism half collapsed: parent process up, bus and cockpit down. Earlier the same day the cockpit was serving normally, so NATS died sometime between then and now, likely across a machine sleep.
**Reaction:** Did not notice until the cockpit failed to load. This is the empirical answer to the Day 2 diagnostic question, would I notice if it crashed. No. The organism can die and keep looking alive from the outside.
**Note:** Presence class. Touches principle 21, failure should become behavioral, not silent collapse. Likely fix when a cluster forms: a supervisor or health check that either restarts NATS or makes `up` exit loudly when NATS dies, instead of lingering as a half dead parent. For now the fix is a manual restart of `up`.

## 2026.05.19 08:28 PDT · presence

**Situation:** Checked the organism after roughly a week of dogfood, with the host sensor live. Pulled the full cockpit timeline.
**What it did:** From 15:19:28 to 15:21:28 UTC the timeline shows a relentless oscillation, one full cycle every 5 seconds for over two minutes: attentive to settling (reason `settling_for:presence_lost`), then settling back to attentive (reason `settling_complete`). Mood strobed with it, warmth 0.70 to 0.55 to 0.70, breath 5.5s to 6.5s to 5.5s, every 5 seconds. The 5 second period is exactly the host sensor poll interval.
**Reaction:** The organism cannot rest. When York is away it thrashes between attentive and settling forever instead of calmly going dormant. The mood strobes. This is the opposite of the slow calm presence the design is built on. Violates Presence Momentum (principle 25) and graceful behavior (principle 21).
**Note:** Root cause is an interaction. The host sensor re-emits present=false every 5 second poll while York is away. Each one kicks ATTENTIVE into SETTLING. The SETTLING path does not carry through to DORMANT, a Plan B limitation where the state service drops the routed target, so it falls back to ATTENTIVE. Five seconds later the next poll repeats it. Two candidate fixes: make the sensor edge triggered so presence is emitted only on change, and fix the settling path to complete to the routed target. Severe enough to fix soon rather than wait for a cluster of five. First real behavioral observation of the dogfood.

## 2026.05.19 09:56 PDT · presence

**Situation:** Tried to restart `up` to pick up the settling fix. Opened the Terminal to a wall of ConnectionRefusedError tracebacks.
**What it did:** The previous `up` process (pid 39325) was half dead again. Parent process alive, its NATS subprocess gone, every service inside it stuck in an infinite reconnect loop spewing ConnectionRefusedError on 4222. Same failure as the 2026.05.14 entry. Second occurrence. A fresh `up` started cleanly once the stale one was killed.
**Reaction:** The half death is a pattern now, not a one off. Twice the organism has silently lost its bus while the parent process lingered looking alive. Nothing surfaces it. The operator finds out only by seeing error spew or a dead cockpit.
**Note:** Second observation of the same specific failure, so lifecycle robustness is now a real cluster, not a single weird moment. Candidate fixes: a supervisor, or make `up` exit loudly when its NATS subprocess dies instead of lingering as a half dead parent, or move the dogfood to a launchd service that restarts on failure. This should be the next piece of work after the settling fix.

## 2026.05.20 07:35 PDT · presence

**Situation:** First morning check after activating the launchd supervisor on 2026.05.19 around 14:28. Ran the pinned three command lifecycle check.
**What it did:** launchd reports runs=3, last exit code=1, currently running healthy (pid 97335, nats 97336, both ports bound, healthz ok). `up.out.log` shows two clean death and restart cycles overnight. nats-server exited at 22:23:01 and again at 22:40:11 on 2026.05.19, both with returncode 0. Each time `up` detected it, logged `up.nats_exited`, echoed FATAL, exited nonzero, and launchd restarted the organism. Run 3 has been stable from 22:40 through the 07:29 morning wake, roughly 9 hours.
**Reaction:** PASS. This is Branch 2 from the pinned tree. The worst case, silent half death, did not recur. Both failures were loud, timestamped, and cleanly recovered. The system failed honestly and recovered cleanly, which is the standard.
**Note:** Two open points. First, the sleep and wake correlation did not confirm. `pmset -g log` showed no power events at 22:23 or 22:40, and the 07:29 morning wake did not kill run 3. The hypothesis that sleep and wake kills NATS is weakened, not supported. Second, nats-server exited with returncode 0 both times, a clean shutdown, not a crash. Something asked NATS to stop. Cause unidentified. The two deaths clustered 17 minutes apart, then 9 hours of stability, consistent with a one off transient around the time a person stops work for the night. Not urgent, launchd recovers it cleanly every time. If clean NATS exits cluster again, investigate what sends the stop, and consider the Branch 3 move of a separate launchd job for nats-server.

## 2026.05.24 PDT · presence

**Situation:** Aegis status check on Day 13 of 90, four days after the lifecycle Branch 2 pass. Pulled `launchctl print`, healthz, `/api/now`, `/api/dogfood`, `/api/timeline`, and grep'd `up.out.log` for scheduler and mind activity.
**What it did:** The lifecycle layer continues to hold. Same pid 97335 since 2026.05.19 22:40, roughly 5 days 5 hours of continuous uptime through multiple sleep and wake cycles. launchd `runs=3` unchanged, no new NATS deaths. The clean NATS exit cluster from 2026.05.19 evening has not recurred. healthz ok, host sensor publishing, presence cycles flowing normally.
**Reaction:** The lifecycle layer is solid. But the scheduler has fired zero times in 5 days. The timeline buffer holds 100 of 500 events (no rotation has happened), and no `scheduled_morning`, `scheduled_evening`, `scheduled_quiet`, or `scheduled_wake` reasons appear anywhere. The REFLECTIVE state has not been entered once. Mind has had no opportunity to propose. Restraint still 0 aired, 0 vetoed. `last_utterance` and `last_candidate` still null. The cognition path is structurally untested, same shape as the senses gap before the host sensor went in.
**Note:** This is the legitimate "if it stays silent for a week" diagnostic the playbook foreshadowed. Either the scheduler task is not actually running inside `ObserverService.main`, `self._scheduler` is None (schedule.yaml did not load under launchd, possibly a path issue with `parents[4]` resolution), or the trigger comparison never matches the 60 second window. Next step is a small diagnostic, not a fix. Verify whether `_scheduler` initialized and whether `_scheduler_task` is alive in pid 97335. Until something fires REFLECTIVE, Mind cannot run, the Steward cannot gate, and the dogfood's actual metric (restraint quality) cannot be measured.

## 2026.05.24 PDT · presence (diagnostic followup)

**Situation:** Followed the previous entry with a live bus probe. Subscribed to `mood.changed`, `mind.utterance_proposal`, `voice.speak`, and `memory.continuity_candidate`, then published one fake scheduler firing (`state.changed` with `reason=scheduled_morning, current=REFLECTIVE`) and waited 4 seconds.
**What it did:** Mood reacted twice (REFLECTIVE_VIOLET then back to ATTENTIVE_WARM when the real state.changed arrived a second later). Mind produced zero utterance proposals. Memory published zero continuity candidates. Voice stayed silent.
**Reaction:** The cognition path has two structural gaps, not one. Front end: the scheduler is not firing, confirmed by 5 days of silence (cause still unidentified, `_scheduler_loop` task is silently not effective). Back end: the keeper has consolidated nothing in 5 days of host sensor data, so even with a manual REFLECTIVE trigger Mind queries memory, finds no consolidated Moments, and stays silent. The bus and routing are fine, the mood service is alive, the wiring works end to end. The work is at the two ends.
**Note:** Either gap alone would block the dogfood's actual metric. Together they explain the 13 day silence completely. Two separable investigations: (A) why doesn't `_scheduler_loop` actually tick (instrument the observer service or add a log line at trigger time, then restart and watch), and (B) why has the keeper consolidated nothing (check the keeper's consolidation cycle and whether the host sensor's events are even reaching the storage layer the keeper reads).

## 2026.05.25 PDT · presence (keeper diagnosis)

**Situation:** Investigated gap B from the previous followup: why has the keeper consolidated nothing in 5 days. Read the keeper service code and queried `/tmp/aegis-memory.db` directly.
**What it did:** The `moments` table holds 6,978 rows. The `events` table holds 163,082 rows (74,834 `senses.posture`, 74,834 `senses.presence`, 14,103 `state.changed`). All raw accumulation works. But the `moments` state breakdown is `tentative=6978, consolidated=0, fading=0`. Every Moment ever created is still tentative. The keeper has never run a consolidation pass.
**Reaction:** The cause is precise and small. `KeeperService` has a `setup(bus)` but no `async def main`, so it inherits the base class default which just waits for shutdown. The function `consolidate_now_async()` is defined and would correctly promote tentative Moments and publish `memory.continuity_candidate`, but nothing calls it. Plan C/D shipped the consolidation logic without wiring a periodic invocation. Same shape as gap A (the scheduler), same "I built the engine, forgot the cron."
**Note:** Fix is roughly a `KeeperService.main()` that loops with a sleep and calls `await self.consolidate_now_async()`. Cadence is the design call (every 5 minutes? every 30 minutes? nightly?). Both A and B must land before the cognition path is exercisable: A so REFLECTIVE actually fires, B so memory has consolidated content to surface when Mind queries. Either alone is insufficient.

## 2026.05.25 PDT · presence (scheduler diagnostic result)

**Situation:** Investigated gap A from the prior entries: why has the scheduler not fired in 5 days. Added three log lines to `_scheduler_loop` (start, per tick, per trigger), committed at `79de8e6`, then force killed pid 97335 (graceful SIGTERM had hung) so launchd would respawn with the instrumented code.
**What it did:** Fresh pid 42555 came up clean. Instrumentation immediately showed `observer.scheduler_loop_started scheduler_present=True`, then `observer.scheduler_tick n_triggers=0` every 30 seconds as expected. The loop is running, the scheduler logic is fine, and zero triggers in the observed window is correct because 19:35 to 19:36 UTC is not inside any of the four trigger windows. Healthz ok. Behavior in the new process matches the design.
**Reaction:** Gap A was not a logic bug or a wiring bug. In the old long lived pid 97335 the `_scheduler_loop` task was effectively dead while the senses pump kept publishing. That is a partial failure state. The task almost certainly crashed silently five days ago and stayed dead because nothing observed it. The instrumentation makes silent task death visible. The next time it happens it will surface in the log within 30 seconds rather than five days. Two structural lessons: long lived asyncio processes drift, and tasks need observability or they fail invisibly.
**Note:** Also caught a separate finding during the diagnostic: pid 97335 hung in shutdown after SIGTERM. The heartbeat service logged service.stopped but the senses pump kept publishing for at least 7 minutes. That means the SIGTERM signal handler set the stop event in `_supervise` but at least one service did not unblock cleanly. Likely the same accumulated asyncio drift. Not the next fix, but worth tracking. The 22:00 UTC trigger today (in roughly 2.5 hours) is the empirical test that triggers actually fire from the new process.

## 2026.05.26 00:00 PDT · presence (first cognition activity)

**Situation:** Morning check after the gap A and B fixes landed and the organism ran overnight under launchd. Day 14 of 90.
**What it did:** Both fixes empirically confirmed. The scheduler fired `quiet_hours_start` at 22:00:22 UTC and `quiet_hours_end` at 07:00:07 UTC, on time within the 22 second window. The keeper ran its first consolidation pass at 20:39 UTC and swept the 6,978 tentative backlog: 219 consolidated, 6,765 faded out, 31 kept tentative. Subsequent hourly passes processed new Moments as they arrived. A real ContinuityCandidate now sits in Mind's cache (moment id `moment_2026-05-26T05-30-48_observing_window_a0fe8a`, focus_score 0.57). Lifecycle still holding, same pid 85807 since the restart, runs=5, healthz ok.
**Reaction:** This is the first cognition activity in 14 days of dogfood. The 3 percent consolidation rate (219 of 6,978) matches the design intent that Memory Magic Moments are rare, not constant. The cognition pipeline is now connected end to end: keeper → ContinuityCandidate → Mind cache. The only step still pending is the first REFLECTIVE trigger, which fires next at 09:00 UTC `morning_reflection` (in roughly 2 hours from now). When it fires, Mind queries the cache, sees the candidate, routes to the Steward, gate runs, aired or vetoed. That is the first move of `aired_total` or `vetoed_total` off zero in 14 days.
**Note:** This is the loop working exactly as designed. The dogfood surfaced two real structural bugs (scheduler silent, keeper has no main loop), both were diagnosed with timestamped evidence, both got small TDD fixes, both are now empirically proven. Nothing was tuned that was not pressured by observation. Discipline held. The next empirical input is the morning_reflection firing in ~2 hours. After that, normal observation driven tuning resumes on the actual restraint quality, which is what the dogfood was always for.

## 2026.05.27 PDT · restraint (first gate decisions ever)

**Situation:** 24 hour check after the gap A and B fixes landed and the cognition pipeline came alive. Day 15 of 90.
**What it did:** Both REFLECTIVE triggers fired on schedule (morning_reflection 2026-05-26 02:00 PDT, evening_reflection 2026-05-26 11:00 PDT). Mind received the REFLECTIVE state, queried the cached ContinuityCandidate, and produced a proposal both times. Steward ran the gate and vetoed both with reason `confidence_below_threshold`. Two rows in the `interventions` table, both `vetoed`, both `memory_magic` class. aired_total=0, vetoed_total=2. Lifecycle still holding: same pid 85807 since the 2026-05-25 restart, runs=5, healthz ok, no new deaths through 2.5 days including multiple sleep wake cycles. Keeper continues hourly consolidations producing 1 to 4 Moments per pass.
**Reaction:** This is the first time the Steward has gated anything in 15 days. The chain is empirically alive end to end: host sensor → state machine → keeper consolidation → ContinuityCandidate → Mind → utterance proposal → Steward gate → intervention log. The vetoes are honest: the cached candidates have confidence 0.2 to 0.57, all below the 0.85 threshold. Most Moments are short observing windows with low focus_score. The Steward is correctly restraining. This is principle 20 working as designed, the 19:1 vetoes to aired signature from the Plan D capstone now starting to surface empirically.
**Note:** The dogfood is now finally measuring its actual metric, restraint quality. Open questions, no longer plumbing: 1) At what candidate confidence will a proposal finally air? 2) Do the vetoes feel right when they happen, or do any feel like the organism should have spoken? 3) What does chosen silence feel like, compared to the broken silence of the first two weeks? Need more sample. Two vetoes is not a pattern yet, twenty might be. The disciplined posture from here is the normal observation log rhythm: wait for clusters, classify into the six failure classes, only adjust rules layer when pressure builds.

## 2026.06.03 PDT · continuity

**Situation:** Routine cockpit check after several days of uptime under launchd. Current pid 1157 (running since Saturday 03:00 PDT).
**What it did:** `/api/dogfood` reported `aired_total=0, vetoed_total=1, day_of_90=0, started_at=null`. Ground truth from the prior entry on 2026.05.27 was `aired=0, vetoed=2` on Day 15. The cockpit's day counter and started_at zeroed out, and one of the two prior vetoes is missing from the summary count.
**Reaction:** The cognition path itself is unaffected (keeper consolidating, scheduler ticking, Steward gating, intervention rows still presumably in the DB). What broke is the cockpit's continuity across process respawn. The dogfood's metric of record (restraint quality over the 90 day window) requires those counters to be stable across restarts. If every launchd respawn resets day_of_90 to 0, the 90 day window can never close visibly.
**Note:** One observation. Logging only, no fix. Per the playbook, wait for a cluster before touching the snapshot or restore layer. Next checks should verify whether the underlying interventions table still holds both vetoes (so the bug is purely in summary read on cold start) or whether a row was actually lost (which would be a deeper bug). Defer until cluster pressure builds or a second cockpit anomaly appears.

## 2026.06.11 PDT · continuity (cockpit anomaly followup, diagnostic)

**Situation:** Second cockpit check after the 2026.06.03 anomaly entry. Wanted to disambiguate whether the missing veto count was a cockpit summary read bug or a real row loss bug.
**What it did:** `/api/dogfood` now reports `aired=0, vetoed=0, day_of_90=0, started_at=null`, worse than the prior pass (vetoed went 1 to 0). Direct SQL against `/tmp/aegis-memory.db`: interventions table holds 0 rows (expected 2 from the 2026.05.26 morning_reflection and 2026.05.27 evening_reflection vetoes). Events table holds 4,525 rows, all timestamped between 19:41:24 UTC and 22:49:06 UTC today. Moments table holds 13 rows. scar_tissue and themes tables hold 0. `kern.boottime` says the Mac rebooted at 2026.06.11 12:38:36 PDT. `aegis-core up` respawned at 12:40:28 PDT under launchd, 2 minutes after boot. DB file `/tmp/aegis-memory.db` was created today, WAL is fresh. Every row in every table is from since today's boot.
**Reaction:** The cockpit was not lying. The underlying DB really is empty of all prior history. Root cause is the storage path: `/tmp/aegis-memory.db` lives in macOS `/tmp/`, which is wiped on reboot. Every Mac reboot resets the dogfood's metric of record. The 90 day window cannot close because day 1 keeps restarting. This explains the 2026.06.03 anomaly cleanly (that was a previous reboot's short fresh DB partway through accumulating its own veto history) and predicts the next anomaly precisely (next reboot, same wipe). Cognition layer is fine. Storage layer is misconfigured.
**Note:** Observation #2 in the continuity class. By the playbook this is still short of a cluster of 5, but the precedent from the 2026.05.19 oscillation entry was that an obvious structural defect with a single clean cause is the kind of thing to fix without waiting for five. The fix is small and scoped: move the DB path from `/tmp/aegis-memory.db` to a stable user location (`~/.aegis-core/memory.db` or `~/Library/Application Support/aegis-core/memory.db`), settle on a single configuration owner for the path, and either copy the current `/tmp` DB across one time before the next reboot or accept the loss and start clean. Logging only here. Fix decision and timing are York's, not the runtime's.

## 2026.06.11 PDT · continuity (storage path fix, executed)

**Situation:** The 2026.06.11 diagnostic entry identified `/tmp/aegis-memory.db` as the root cause of the continuity anomaly cluster (`/tmp` is wiped on macOS reboot, so the dogfood's metric of record could not survive any reboot). York's call: fix now, not wait. No more day 1 restarts.
**What it did:** Six hardcoded `/tmp/aegis-memory.db` references and one `/tmp/aegis-voice.log` reference were moved to `~/.aegis-core/memory.db` and `~/.aegis-core/voice.log`. Five service modules (memory, observer, keeper, mind, steward), the voice backend, and four CLI defaults in `cli.py`. `from pathlib import Path` was already present in all 7 files; only the constant strings changed. 246 tests pass. The live `/tmp` DB was migrated via `sqlite3 .backup` to `~/.aegis-core/memory.db` (5,411 events, 13 moments, 0 interventions captured in the snapshot). pid 942 and the nats subprocess (pid 3586) were force killed. launchd respawned `aegis-core up` as pid 37217 after the 10s throttle. `lsof` confirms pid 37217 holds `~/.aegis-core/memory.db` (and `.db-wal`, `.db-shm`) open. 8 second probe showed events growing from 5,428 to 5,432 at the new path. The orphaned `/tmp/aegis-memory.db` is left in place as a fallback for now.
**Reaction:** The dogfood now has stable storage. A Mac reboot will no longer wipe the 90 day window. The cockpit still reports `day_of_90=0, started_at=null` because that derivation lives in a layer above the DB (it appears to reset on process restart, separate concern). The cognition path is unaffected. This was a small surgical fix scoped exactly to the diagnosed root cause, taking the 2026.05.19 precedent at face value.
**Note:** Two things to watch from here. First, whether `started_at` and `day_of_90` continue to reset on the next process respawn (would indicate a separate fix is needed in the dogfood state derivation, possibly a row in `meta` or a `dogfood_state` table set on first start and read on subsequent ones). Second, whether the next genuine launchd respawn (sleep/wake cycle or system restart) correctly opens `~/.aegis-core/memory.db` and preserves accumulated state across it. Until then, the storage layer fix is locally verified and writes are persisting to a path that survives reboots.

<!-- Append new entries above this line. Keep format consistent. -->
