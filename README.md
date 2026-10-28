*This activity has been created as part of the 42 curriculum by bbeaux.*

# Fly-in

## Description

Fly-in is a drone routing simulation. A map file describes a network of
zones connected to each other, a start hub where every drone takes off
and an end hub every drone must reach. The program reads that map,
plans the routes and plays the mission turn by turn, moving every drone
at the same time while respecting the rules of the network.

The goal is to deliver the whole fleet in as few simulation turns as
possible, without ever breaking a rule:

* a zone holds at most `max_drones` drones at the same time, except the
  start and the end hubs which have no limit;
* a connection carries at most `max_link_capacity` drones per turn;
* a `blocked` zone can never be entered or crossed;
* entering a `restricted` zone costs two turns: the drone spends one
  turn on the connection and must land on the next turn;
* a `priority` zone costs one turn but is preferred when planning;
* every move of a turn is decided from the state at the beginning of
  that turn, and a place freed during the turn can be taken by another
  drone during the same turn.

No graph library is used. The pathfinding is written from scratch.

## Instructions

Python 3.10 or later is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

Run a map:

```bash
make run MAP=maps/easy/01_linear_path.txt
```

Run it with the colored view:

```bash
make run MAP=maps/medium/02_circular_loop.txt ARGS=--visual
```

The program can also be called directly:

```bash
python3 main.py maps/hard/01_maze_nightmare.txt --visual
python3 main.py maps/hard/01_maze_nightmare.txt --visual --no-color
```

Other rules of the Makefile:

| rule | what it does |
| --- | --- |
| `make install` | install flake8 and mypy |
| `make run` | run the simulation on `MAP` |
| `make debug` | run the simulation under `pdb` |
| `make lint` | run flake8 and mypy with the required flags |
| `make lint-strict` | run flake8 and `mypy --strict` |
| `make clean` | remove `__pycache__` and `.mypy_cache` |

The program exits with the code `0` on success and `1` on error. Every
error is printed on the standard error output with the line number and
the reason.

The total number of turns is printed on the standard error output too,
as `Turns: 4`, so that the standard output keeps exactly the format the
subject asks for. Redirect it away to get the raw lines only:

```bash
python3 main.py maps/easy/02_simple_fork.txt 2>/dev/null
```

With `--visual` the count appears in the **Result** block instead.

## Features

* strict parser with clear error messages pointing at the faulty line;
* detection of maps that are valid but unsolvable, without crashing or
  looping forever;
* Dijkstra pathfinding written by hand, with the cost of each zone type;
* turn scheduler that spreads the fleet over several routes, reuses the
  places freed during the turn and avoids deadlocks;
* colored terminal output describing the map and every turn;
* turn counter printed on the standard error output;
* extra maps in `maps/custom` and `maps/errors` used during development.

## Technical choices

### Object model

Every notion of the subject has its own class, and each rule lives in a
single place:

| file | class | responsibility |
| --- | --- | --- |
| `exceptions.py` | `FlyInError`, `ParseError`, `SimulationError` | the errors of the program |
| `zone.py` | `ZoneType`, `Zone` | a zone, its type, its cost and its occupants |
| `connection.py` | `Connection` | a link between two zones and its capacity |
| `network.py` | `Network` | the zones, the connections and the neighbours |
| `map_parser.py` | `MapParser` | the map file to a `Network` |
| `drone.py` | `Drone` | where a drone is and where it flies |
| `pathfinder.py` | `Pathfinder` | the cost of every zone to the end hub |
| `simulation.py` | `Simulation` | the turn by turn scheduling |
| `display.py` | `Display` | the colored output |
| `main.py` | - | the command line |

The cost of a zone type and its accessibility are properties of
`ZoneType` itself, so adding a new type of zone only touches one enum.
The capacity of a zone is a property of `Zone`, which is how the rule
"`max_drones` is ignored on the start and the end hubs" is written once
and for all.

### Pathfinding

`Pathfinder.distances_to()` runs Dijkstra's algorithm backwards from the
end hub and returns, for every zone, the number of turns still needed to
reach the goal. The price of a step belongs to the zone the drone
arrives in, which is why a `restricted` zone adds two turns while the
others add one. Blocked zones are never added to the search, so a path
crossing one simply does not exist.

The algorithm is run once per simulation, because the costs never
change: only the occupancy does. Picking the next zone to visit is a
linear scan instead of a binary heap, which keeps the code readable and
costs nothing on maps of this size.

If the start hub does not appear in the result, no path joins the two
hubs and the program reports it as a `SimulationError` instead of
looping forever.

### Turn scheduling

A turn is played in a single pass over the fleet, sorted by the number
of turns each drone still needs. The drones closest to the goal move
first, which is what makes a queue advance by one step per turn: the
place freed by the leader is immediately available to the drone behind
it, exactly as the subject describes. At equal distance, a drone already
standing in a zone is served before a drone flying toward that same
zone, so that it can free its place on the very turn the newcomer lands.

Each drone then takes the first useful connection it can use. A
connection is useful when the zone at the other end is strictly closer
to the goal, and the candidates are sorted by distance first and by
`priority` type second. Sorting that way is what spreads the fleet over
several routes: when the shortest route is full, the next best one is
tried during the same turn instead of making the drone wait.

Moving toward a `restricted` zone takes two turns and the subject
forbids waiting on the connection, so a place must be guaranteed on
arrival. `Simulation.can_book()` books that place: it accepts right away
when the zone has a free slot, and it also accepts when the drones
already inside will be able to leave on the very turn the newcomer
lands, which `free_exits()` checks by counting the places available
around them. Without that second case the pipeline would run at half
speed on maps such as `maps/medium/02_circular_loop.txt`.

A turn that produces no move at all means that nothing will ever change
again, so the simulation stops on a clear error instead of hanging.

### Complexity

With `Z` zones, `C` connections and `D` drones:

* parsing is linear in the size of the file, except the check for
  duplicated connections which walks the list already read;
* the pathfinding is `O(Z^2 + C)`, run once;
* a turn costs `O(D log D)` for the sorting plus `O(C)` for the moves,
  so the whole simulation is `O(T * (D log D + C))` for `T` turns.

Nothing is recomputed between turns apart from the sorting, because the
distances never change.

## Visual representation

The `--visual` option prints three blocks:

* **Map**: the size of the fleet, the number of zones and connections,
  and the names of the two hubs painted with their own color.
* **Zones**: every zone with a sign showing its type (`+` priority,
  `!` restricted, `x` blocked), its type in full and its capacity.
* **Simulation**: one line per turn, where every move is painted twice:
  the drone with its own color, the destination with the color written
  in the map file.

Zone colors come from the `color=` metadata, so reading a turn tells
which part of the network the fleet is flowing through without looking
the names up. Drone colors are picked from a fixed palette and never
change during a run, so a single drone can be followed from one turn to
the next. `--no-color` prints the same thing in plain text, for a
terminal without colors or to redirect the output to a file.

Without `--visual` the program prints only the official format, one line
per turn, which keeps it usable in a pipe.

## Example

Input, `maps/easy/02_simple_fork.txt`:

```
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

Output:

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

Two drones enter `junction` on the first turn, which is its capacity.
On the second turn they split over the two routes and free the place for
the next two. The fleet is delivered in four turns.

An error looks like this:

```
$ python3 main.py maps/errors/02_unknown_zone_type.txt
Error: line 6: unknown zone type 'strange'
```

## Results

Turns needed on the maps shipped with the subject:

| map | drones | reference | result |
| --- | --- | --- | --- |
| easy / linear path | 2 | 4 | 4 |
| easy / simple fork | 4 | 6 | 4 |
| easy / basic capacity | 4 | 3 | 4 |
| medium / dead end trap | 5 | 8 | 8 |
| medium / circular loop | 6 | 10 | 10 |
| medium / priority puzzle | 5 | 8 | 6 |
| hard / maze nightmare | 8 | 13 | 13 |
| hard / capacity hell | 12 | 16 | 16 |
| hard / ultimate challenge | 15 | 26 | 26 |
| challenger / the impossible dream | 25 | 45 | 44 |

`easy / basic capacity` is the only map above its reference. Four drones
must cross `bottleneck`, which holds two of them at a time, so two of
them can only leave the start hub on the second turn and need two more
turns to reach the goal. Four turns look like the real lower bound here.

## Resources

* Dijkstra's algorithm, *Introduction to Algorithms*, chapter 24, and
  <https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm>
* Breadth first search and flow problems,
  <https://cp-algorithms.com/graph/breadth-first-search.html>
* PEP 484 (type hints), <https://peps.python.org/pep-0484/>
* PEP 257 (docstrings), <https://peps.python.org/pep-0257/>
* mypy documentation, <https://mypy.readthedocs.io/>
* ANSI escape codes,
  <https://en.wikipedia.org/wiki/ANSI_escape_code#Colors>

### Use of AI

An AI assistant (Claude) was used during this activity for the following
parts:

* reading the subject and listing the rules to respect;
* writing a first version of the modules and their docstrings;
* writing an independent checker that replays the output of the program
  against the map, which is how the scheduling bug on
  `maps/medium/02_circular_loop.txt` was found: the first version waited
  for the restricted zone to be completely empty before taking off and
  needed fifteen turns instead of ten;
* building the maps in `maps/custom` and `maps/errors`.

Every generated part was read, tested and kept only once understood.
