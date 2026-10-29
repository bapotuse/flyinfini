from __future__ import annotations

import argparse
import os
import sys

from display import Display
from exceptions import FlyInError
from map_parser import MapParser
from simulation import Simulation


def build_arguments() -> argparse.ArgumentParser:
    """Describe the options accepted on the command line."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Route a fleet of drones across a network of zones.",
    )
    parser.add_argument("map", help="path of the map file to fly")
    parser.add_argument(
        "--visual",
        action="store_true",
        help="show the map and a colored view of every turn",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="print plain text, even when writing to a terminal",
    )
    return parser


def main() -> int:
    """Run the simulation asked on the command line.

    Colors are used only when the output really goes to a terminal, so
    a redirected output keeps the exact format asked by the subject.

    Returns:
        0 when everything went well, 1 on error.
    """
    arguments = build_arguments().parse_args()
    try:
        network = MapParser().parse(arguments.map)
        simulation = Simulation(network)
        turns = simulation.run()
    except FlyInError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    colored = not arguments.no_color and sys.stdout.isatty()
    display = Display(network, colored)
    if arguments.visual:
        display.show_header()
        number = 0
        for moves in turns:
            number = number + 1
            display.show_turn(number, moves)
        display.show_summary(len(turns))
    else:
        for moves in turns:
            print(display.moves_line(moves))
        sys.stdout.flush()
        print(f"Turns: {len(turns)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # The reader of the output left early (e.g. `| head`).
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(0)
