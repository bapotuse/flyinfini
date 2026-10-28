*This activity has been created as part of the 42 curriculum by bbeaux.*

# Fly-in

## Description

A map file describes a network of zones, a start hub and an end hub.
The program reads it and moves a fleet of drones from the start to the
end in as few turns as possible, without any graph library.

Rules respected: zone and connection capacities, blocked zones that can
never be entered, restricted zones that cost two turns, priority zones
preferred when planning, and simultaneous moves where a place freed
during a turn can be taken during that same turn.

## Instructions

Python 3.10 or later.

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
make run MAP=maps/easy/01_linear_path.txt
```

Or directly:

```bash
python3 main.py maps/medium/02_circular_loop.txt
python3 main.py maps/medium/02_circular_loop.txt --visual
```

Makefile rules: `install`, `run`, `debug`, `lint`, `lint-strict`,
`clean`. Options: `--visual` for the detailed view, `--no-color` for
plain text.

Errors go to the standard error output with the faulty line, and the
program exits with `1`.

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

An error looks like `Error: line 6: unknown zone type 'strange'`.

## Technical choices

One class per notion: `ZoneType` and `Zone`, `Connection`, `Network`,
`MapParser`, `Drone`, `Pathfinder`, `Simulation`, `Display`. Each rule
lives in a single place, so the cost of a zone type or the capacity of a
hub is written only once.

**Pathfinding.** `Pathfinder` runs Dijkstra by hand, backwards from the
end hub, and returns the number of turns every zone still needs to reach
the goal. The price of a step belongs to the zone the drone arrives in,
so a restricted zone adds two turns. Blocked zones are never added, and
a start hub missing from the result means the map is unsolvable. The
search is run once, since the costs never change.

**Scheduling.** Every turn, the drones are served from the closest to
the goal to the furthest, which makes a queue advance one step per turn:
the place freed by the leader is taken by the drone behind it during the
same turn. Each drone then takes the first free connection leading
strictly closer to the goal, priority zones first, which spreads the
fleet over several routes instead of making it wait.

**Restricted zones.** A drone cannot wait on a connection, so a place is
booked before taking off. `can_book()` accepts a free slot, but also
accepts a slot held by a drone that will be able to leave on the very
turn the newcomer lands. Without that second case the fleet would move
at half speed on `maps/medium/02_circular_loop.txt`.

A turn with no move at all means nothing will ever change again, so the
program stops with a clear message instead of hanging.

## Visual representation

Moves are painted with the color of their drone, the same one from the
first turn to the last, so a drone can be followed across the turns.
Colors appear only when the output goes to a terminal, so a redirected
output keeps the exact format of the subject. `--visual` adds the map,
the list of zones with their type and capacity, and the total number of
turns.

## Results

Turns on the maps of the subject: 4, 4, 4 (easy), 8, 10, 6 (medium),
13, 16, 26 (hard), 44 (challenger). Every reference is reached except
`easy/03`, where four drones must cross a zone holding two of them at a
time, which makes four turns the real lower bound.

## Resources

* Dijkstra's algorithm,
  <https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm>
* PEP 484 (type hints) and PEP 257 (docstrings)
* mypy documentation, <https://mypy.readthedocs.io/>
* ANSI escape codes,
  <https://en.wikipedia.org/wiki/ANSI_escape_code#Colors>

### Use of AI

An AI assistant was used for two things: looking up functions and
syntax I was unsure typing notations, ANSI escape codes, and handling repetitive work
(docstrings, the test maps in `maps/custom` and `maps/errors`).

