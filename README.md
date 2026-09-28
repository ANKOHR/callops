# CallOps

CallOps is a small-business call operations console. It runs scripted demo conversations, writes timestamped transcripts, extracts heuristic notes and follow-up candidates, and stores a CRM-style session record. Every follow-up is held in `DRAFT` until a human approves it.

## Quickstart

Requires Python 3.10 or newer. Runtime code uses only the Python standard library. Install pytest separately if you want to run the test suite.

```powershell
py -m pip install -e .
callops call --scenario discovery
callops notes discovery-demo
callops actions discovery-demo
callops report discovery-demo --format html
```

The default data directory is `data/`. Set it before the subcommand to use another directory, for example `callops --data-dir .\scratch call --scenario discovery`. Call output prints the transcript location, session ID, and the visible `SIMULATED CALL` banner. Running a scenario again replays the same fixed demo session and replaces its generated call, notes, and action records. Existing approval transitions for matching action IDs are retained.

Use the item ID shown by `actions` to approve a follow-up. To mark an approved item done, use the separate `done` command.

```powershell
callops approve act-discovery-demo-01 --by "Alex Morgan"
callops done act-discovery-demo-01 --by "Alex Morgan"
```

Reports are written to the data directory as Markdown or self-contained HTML. The HTML report includes a `SIMULATED CALL` banner.

## Honesty boundary

**CallOps uses simulated telephony only. No real calling takes place, and this build has no phone provider integration.** Every transcript, CLI call result, and HTML report visibly says `SIMULATED CALL` and identifies demo mode. These scripted fixtures are fictional examples, not records of real people or businesses.

Notes and action items are heuristic extractions from scripted transcript text. They are not verified facts or commitments. Each note includes transcript line references, and each action candidate includes a verbatim supporting quote and line number so a human can review the source.

## Approval gate rules

Each action item begins in `DRAFT`. The only allowed paths are:

```text
DRAFT -> APPROVED -> DONE
```

`approve <item> --by <name>` requires a non-empty human name and records the transition in `callops-audit.jsonl`. `done <item> --by <name>` only works for an item already in `APPROVED`. Attempting to mark a draft item done, approve it twice, or skip a state is rejected by the state machine. There is no CLI shortcut that writes an approved or done status directly.

## Determinism

The fixtures use fixed dialogue and fixed UTC start times. Call timestamps are offsets from those fixture times, and session IDs are stable per scenario. The engine uses no random number generator. The documented demo seed is `0` and is reserved for compatibility if a future fixture needs seeded variation. Replaying a scenario in the same data directory produces byte-identical transcript, notes, and call audit events.

## Fixture scenarios

All scenarios are fictional, scripted data shipped as JSON files in `callops/scenarios/`:

- `discovery`: a fictional HVAC business discusses team size, current dispatch work, a migration concern, budget, timing, and a proposed follow-up.
- `support-follow-up`: a fictional customer describes a scheduling issue and agrees to review a support update.
- `re-engagement`: a fictional prospect revisits an earlier conversation and considers a short product demonstration.
- `quiet`: a short exchange with no extracted facts, objections, budget, timeline, or action candidates. It demonstrates that heuristic extraction can return no results.

## Architecture

```text
scenario JSON
    |
    v
simulated call engine ---> timestamped transcript
    |                            |
    v                            v
JSON session store <--- heuristic notes and action extraction
    |                            |
    +---- audit JSONL <--- approval state machine
    |
    +---- Markdown or HTML CRM report
```

The Python CLI is in `callops/cli.py`. `engine.py` renders fixture dialogue, `extraction.py` derives notes and quoted action candidates, `store.py` persists sessions and audit events, `gate.py` enforces transitions, and `report.py` creates reports.

## Development

```powershell
py -m pytest
```
