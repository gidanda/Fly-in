*This project has been created as part of the 42 curriculum by hgoda.*

# Fly-in

## Description

Fly-in is a turn-based drone-routing simulator. It reads a map containing
zones, bidirectional connections, capacities, and movement properties, then
routes every drone from the start hub to the end hub in as few turns as
possible.

The simulation enforces:

- zone and connection capacity limits;
- one-turn movement into `normal` and `priority` zones;
- two-turn movement into `restricted` zones;
- inaccessible `blocked` zones;
- simultaneous departures and arrivals;
- deterministic, per-turn movement output; and
- a graphical viewer for zone colors, drone positions, and capacity usage.

The implementation uses only the Python standard library for runtime logic.
It does not use graph libraries such as NetworkX.

## Instructions

### Requirements

- Python 3.10 or newer
- `make`

The development tools are installed into a local `.venv` directory and are
listed in `requirements-dev.txt`.

### Installation

```sh
make install
```

### Running a simulation

Map files are not bundled with the submission. Obtain the map archive from
the subject attachments and extract it separately, or save the complete input
example below as a UTF-8 text file.

```sh
tar -xzvf /path/to/maps.tar.gz
```

Pass the path to an existing map through the `MAP` variable. Replace
`/path/to/map.txt` below with your actual map path:

```sh
make run MAP=/path/to/map.txt
```

The equivalent direct command is:

```sh
.venv/bin/python -m fly_in /path/to/map.txt
```

### Graphical viewer

Display the recorded simulation in a separate Tk window:

```sh
make gui MAP=/path/to/map.txt
```

The equivalent direct command uses `--gui`:

```sh
.venv/bin/python -m fly_in /path/to/map.txt --gui
```

The simulation first prints its usual terminal output and records the states.
The controls are **Reset**, **Previous turn**, and **Next turn**, left to right.
They select the first, previous, or next recorded state without recalculating
the simulation. Reset and Previous turn are disabled at the first state;
Next turn is disabled at the last state and re-enabled when going back.
Resizing the window fits the map to the canvas.
Zones use their specified colors (white for missing or unrecognized colors),
start/end zones have double outlines, and small diamonds represent drones.
Labels show drone count/capacity; large groups display at most five diamonds.
In-transit drones appear at connection midpoints and delivered drones at the
end zone. Unlimited zone capacity is displayed as `∞`.

This option requires a Python installation with working tkinter and Tcl/Tk,
plus a graphical desktop. Terminal-only execution does not import tkinter.

### Debugging

```sh
make debug MAP=/path/to/map.txt
```

### Quality checks

```sh
make lint
```

`make lint` runs both `flake8` and `mypy` with the options required by the
subject.

### Cleaning generated files

```sh
make clean
```

## Input format

The first definition contains the number of drones:

```text
nb_drones: 3
```

A map must contain exactly one start hub and one end hub. Regular zones are
declared with `hub:`:

```text
start_hub: start 0 0 [color=green]
hub: corridor 1 0 [zone=priority color=yellow max_drones=2]
hub: tunnel 2 0 [zone=restricted color=purple max_drones=1]
end_hub: goal 3 0 [color=blue]
```

Start and end hubs cannot use `zone=blocked`; regular hubs may use it to
represent inaccessible zones. The parser reports a source-aware error for a
blocked start or end hub.

Connections refer to zones that have already been declared:

```text
connection: start-corridor [max_link_capacity=2]
connection: corridor-tunnel [max_link_capacity=1]
connection: tunnel-goal [max_link_capacity=2]
```

Supported zone metadata:

| Key | Meaning | Default |
| --- | --- | --- |
| `zone` | `normal`, `priority`, `restricted`, or `blocked` | `normal` |
| `color` | Single-word display color | Unspecified; white in the GUI |
| `max_drones` | Maximum simultaneous zone occupancy | `1` |

Supported connection metadata:

| Key | Meaning | Default |
| --- | --- | --- |
| `max_link_capacity` | Maximum drones using the connection in one turn | `1` |

Empty lines and lines beginning with `#` are ignored. Definitions use exactly
one ASCII space between elements; tabs and leading or trailing spaces are
rejected. Metadata keys may appear in any order inside a single pair of square
brackets.

Invalid syntax, duplicate definitions, unknown zone references, invalid
capacities, or missing required hubs stop the program with a contextual error
message.

## Output format

Each output line represents one simulation turn. Only drones that moved during
that turn are included.

The following complete input combines the definitions shown above:

```text
nb_drones: 3
start_hub: start 0 0 [color=green]
hub: corridor 1 0 [zone=priority color=yellow max_drones=2]
hub: tunnel 2 0 [zone=restricted color=purple max_drones=1]
end_hub: goal 3 0 [color=blue]
connection: start-corridor [max_link_capacity=2]
connection: corridor-tunnel [max_link_capacity=1]
connection: tunnel-goal [max_link_capacity=2]
```

Expected terminal output for this input:

```text
D1-corridor D2-corridor
D1-corridor-tunnel D3-corridor
D1-tunnel D2-corridor-tunnel
D1-goal D2-tunnel D3-corridor-tunnel
D2-goal D3-tunnel
D3-goal
```

A zone arrival uses `D<ID>-<zone-name>`. The first turn of travel into a
`restricted` zone uses `D<ID>-<source-zone>-<destination-zone>` because the
drone finishes the turn on that connection.

Terminal output is always plain text, including interactive runs. Zone colors
are displayed only in the GUI. Logs can be redirected for automated evaluation:

```sh
make run MAP=/path/to/map.txt > result.txt
```

Use `make gui MAP=<map_file>` for a visual representation of the simulation.

## Algorithm and implementation strategy

### 1. Parsing and static graph construction

`MapParser` reads the file once and creates immutable `Zone` and `Connection`
objects. `DroneMap` indexes them by ID, endpoint pair, and adjacency so
that later lookups do not repeatedly scan every definition.

Syntax errors are reported as `MapParseError` values with the file path, line
number, source text, and a specific cause. Cross-object map constraints are
validated by `MapParser` before `DroneMap` builds its indexes. `Scenario` and
`DroneMap` trust these caller-validated values instead of repeating the input
checks. Code constructing these objects directly must satisfy the same
preconditions, including unique zone and connection IDs. The parser assigns
these IDs sequentially, so uniqueness follows from its construction process.

### 2. Reverse Dijkstra analysis

`Pathfinder` runs Dijkstra's algorithm once from the end hub over reversed
movement costs. An edge's effective cost is the cost of entering its
destination zone, so the reverse relaxation uses the current zone's entry
cost. This correctly handles the asymmetric cost implied by entering a
`restricted` zone.

The resulting table gives the minimum static cost from every reachable zone to
the goal. It is cached for the complete simulation. The preprocessing cost is
`O((V + E) log V)` with `V` zones and `E` connections.

### 3. Capacity-aware greedy planning

For each turn, `TurnPlanner`:

1. processes zone-bound drones from the lowest remaining goal cost to the
   highest, using the drone ID as a deterministic tie-breaker;
2. considers only accessible neighboring zones whose goal cost is strictly
   lower, preventing cycles;
3. orders candidates by entry cost plus remaining goal cost;
4. prefers a `priority` zone when candidate costs are equal;
5. tentatively adds each move to the current turn plan;
6. asks `SimulationState.preview_turn()` to validate all simultaneous zone and
   connection capacities; and
7. builds and validates a next-turn plan to accommodate forced arrivals.

If the best candidate is unavailable, the planner tries the next candidate. A
drone waits when no safe candidate exists. Lookahead uses only new one-turn
moves, allowing downstream departures to free space for restricted arrivals.
The entire verified next-turn plan is saved, not just selected departures.
On the following call its moves form the fixed base for further greedy moves.
The planner is therefore used sequentially for a single simulation.

### 4. Immutable turn simulation

`Drone`, its states, `MoveIntent`, `TurnPlan`, and `TurnProjection` are
immutable value objects. Previewing a turn creates a new `SimulationState`
snapshot rather than modifying the current one.

`SimulationState.preview_turn()` resolves map-dependent movement information,
counts continuing transit and new departures against connection capacity,
excluding existing transit arriving that turn, applies movement, and validates
the resulting zone occupancy. A returned projection is therefore executable
with respect to movement and capacity rules, although the planner remains
responsible for choosing an efficient plan.

### Main components

| Component | Responsibility |
| --- | --- |
| `MapParser` | Parse strict map syntax and report source-aware errors |
| `Zone`, `Connection`, `DroneMap` | Represent and index the static map |
| `Scenario` | Combine a map with its drone count |
| `Pathfinder` | Cache minimum static goal costs with reverse Dijkstra |
| `Drone` and drone states | Represent immutable per-drone state |
| `SimulationState` | Validate and project one simultaneous turn |
| `TurnPlanner` | Build a safe greedy movement plan |
| `TurnProjection` | Store the validated result of a turn preview |
| `TurnFormatter` | Produce plain-text movement logs |
| `SimulationRunner` | Repeat planning, projection, formatting, and output |

## Performance

The following results were measured during development using the maps
distributed with the subject and the current greedy planner. Those map files
are not included in the submission. A lower turn count is better.

| Map | Drones | Result | Optimum (subject v3.0) |
| --- | ---: | ---: | ---: |
| Linear path | 2 | 4 | 4 |
| Simple fork | 4 | 4 | 4 |
| Basic capacity | 4 | 4 | 4 |
| Dead end trap | 5 | 8 | 8 |
| Circular loop | 6 | 10 | 10 |
| Priority puzzle | 5 | 6 | 6 |
| Maze nightmare | 8 | 13 | 13 |
| Capacity hell | 12 | 16 | 16 |
| Ultimate challenge | 15 | 26 | 26 |
| The Impossible Dream | 25 | 45 | 43 |

All nine mandatory maps match their listed optima and satisfy the required
25% margin. The optional challenger map is two turns above its optimum.

## Verification performed during development

The development test suite covered parsing, error context, graph lookup,
shortest-cost analysis, immutable drone transitions, turn-plan validation,
simultaneous
capacity handling, restricted movement, saved lookahead plans, planning,
formatting, GUI controls, the runner, and the CLI entry point.

All subject-provided maps were also parsed and executed as integration checks.
The test suite and internal design documents are not included in the
submission. These checks describe verification performed during development,
not additional files required to run the submitted program.

## Resources

- Fly-in subject, versions 1.6 and 3.0, supplied by 42.
- [Python `heapq` documentation](https://docs.python.org/3.10/library/heapq.html)
- [Python `dataclasses` documentation](https://docs.python.org/3/library/dataclasses.html)
- [Python `argparse` documentation](https://docs.python.org/3/library/argparse.html)
- [Python `venv` documentation](https://docs.python.org/3/library/venv.html)
- [Dijkstra, “A note on two problems in connexion with graphs”](https://doi.org/10.1007/BF01386390)

### Use of AI

OpenAI Codex was used as an interactive learning and development assistant for:

- organizing the subject requirements;
- discussing data structures, validation boundaries, and object-oriented
  responsibilities;
- explaining parsing, Dijkstra's algorithm, immutable state transitions, and
  greedy scheduling;
- assisting with implementation and refactoring across the simulator and its
  tests;
- proposing edge cases and running systematic verification; and
- drafting the design-decision log and this README.

All generated or suggested work was reviewed through step-by-step design
discussion, static analysis, automated tests, execution on every supplied map,
and manual inspection. Responsibility for understanding, validating, and
maintaining the submitted code remains with the author.
