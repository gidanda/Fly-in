*This project has been created as part of the 42 curriculum by hirokigoda.*

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
- colored terminal feedback for zone arrivals and connection travel.

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

Pass a map through the `MAP` variable:

```sh
make run MAP=maps/easy/01_linear_path.txt
```

The equivalent direct command is:

```sh
.venv/bin/python -m fly_in maps/easy/01_linear_path.txt
```

### Debugging

```sh
make debug MAP=maps/easy/01_linear_path.txt
```

### Quality checks

```sh
make lint
.venv/bin/python -m pytest
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
| `color` | Single-word display color | terminal default |
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
that turn are included:

```text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

A zone arrival uses `D<ID>-<zone-name>`. The first turn of travel into a
`restricted` zone uses `D<ID>-C<connection-id>` because the drone finishes the
turn on that connection.

When standard output is an interactive terminal:

- a zone arrival uses the destination zone's `color` metadata;
- connection travel is cyan;
- an unknown but specified color name uses visible magenta as a fallback;
- a zone without a color remains in the terminal's default color; and
- `black` is displayed as gray so that it remains readable on dark terminals.

ANSI color codes are automatically disabled when output is redirected to a
file, sent through a pipe, or captured by a test. The underlying movement
format therefore remains suitable for automated evaluation:

```sh
make run MAP=maps/easy/01_linear_path.txt > result.txt
```

Color makes the destination of each arrival immediately recognizable, while
the shared cyan color distinguishes drones that are still traveling from
drones that reached a zone.

## Algorithm and implementation strategy

### 1. Parsing and static graph construction

`MapParser` reads the file once and creates immutable `Zone` and `Connection`
objects. `DroneMap` indexes them by ID, name, endpoint pair, and adjacency so
that later lookups do not repeatedly scan every definition.

Syntax errors are reported as `MapParseError` values with the file path, line
number, source text, and a specific cause. Cross-object map constraints are
checked while `DroneMap` builds its indexes.

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
7. reserves capacity for forced next-turn arrivals from restricted travel.

If the best candidate is unavailable, the planner tries the next candidate. A
drone waits when no safe candidate exists. Restricted-arrival reservations are
deliberately conservative: they do not assume that a currently occupying drone
will leave on the following turn.

### 4. Immutable turn simulation

`Drone`, its states, `MoveIntent`, `TurnPlan`, and `TurnProjection` are
immutable value objects. Previewing a turn creates a new `SimulationState`
snapshot rather than modifying the current one.

`SimulationState.preview_turn()` resolves map-dependent movement information,
counts every connection user during the turn, applies movement, and validates
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
| `TurnFormatter` | Produce plain or ANSI-colored movement text |
| `SimulationRunner` | Repeat planning, projection, formatting, and output |

## Performance

The following results were measured with the included maps and the current
greedy planner. A lower turn count is better.

| Map | Drones | Result | Reference target |
| --- | ---: | ---: | ---: |
| Linear path | 2 | 4 | 6 or fewer |
| Simple fork | 4 | 4 | 8 or fewer |
| Basic capacity | 4 | 4 | 6 or fewer |
| Dead end trap | 5 | 8 | 12 or fewer |
| Circular loop | 6 | 15 | 15 or fewer |
| Priority puzzle | 5 | 7 | 12 or fewer |
| Maze nightmare | 8 | 13 | 30 or fewer |
| Capacity hell | 12 | 16 | 35 or fewer |
| Ultimate challenge | 15 | 26 | 45 or fewer |
| The Impossible Dream | 25 | 43 | Reference record: 45 |

All supplied reference targets are met. The optional challenger map completes
two turns faster than its supplied 45-turn reference record.

## Testing

The test suite covers parsing, error context, graph lookup, shortest-cost
analysis, immutable drone transitions, turn-plan validation, simultaneous
capacity handling, restricted movement, conservative reservations, planning,
formatting, terminal colors, the runner, and the CLI entry point.

All distributed maps are also parsed and executed as integration checks.

## Resources

- Fly-in subject, version 1.6, supplied by 42.
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
