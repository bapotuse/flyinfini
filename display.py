"""Colored terminal output for the simulation."""

from __future__ import annotations

from network import Network

RESET = "\033[0m"
BOLD = "\033[1m"

COLORS = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
    "grey": "\033[90m",
    "orange": "\033[33m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
}

DRONE_COLORS = [
    "cyan",
    "magenta",
    "yellow",
    "green",
    "blue",
    "red",
    "bright_cyan",
    "bright_magenta",
    "bright_yellow",
    "bright_green",
    "bright_blue",
    "bright_red",
]

TYPE_SIGNS = {
    "normal": " ",
    "priority": "+",
    "restricted": "!",
    "blocked": "x",
}


class Display:
    """Print the map and the moves with colors."""

    def __init__(self, network: Network, colored: bool = True) -> None:
        """Create a display for a network.

        Args:
            network: the network to describe.
            colored: False to print plain text only.
        """
        self.network = network
        self.colored = colored

    def paint(self, text: str, color: str | None) -> str:
        """Return the text wrapped in color codes.

        Args:
            text: the text to show.
            color: a color name, or None for the default one.
        """
        if not self.colored or color is None:
            return text
        if color not in COLORS:
            return text
        return COLORS[color] + text + RESET

    def zone_label(self, name: str, width: int = 0) -> str:
        """Return a zone name painted with its own color.

        The padding is added before the colors, otherwise the escape
        codes would be counted as visible characters.

        Args:
            name: the name of the zone.
            width: minimum width of the result.
        """
        text = name
        while len(text) < width:
            text = text + " "
        if name not in self.network.zones:
            return text
        return self.paint(text, self.network.zones[name].color)

    def drone_label(self, drone: str) -> str:
        """Return a drone name painted with its own color.

        Each drone keeps the same color for the whole simulation, so a
        single drone can be followed from one turn to the next.

        Args:
            drone: a drone name such as 'D1'.
        """
        number = drone[1:]
        if not drone.startswith("D") or not number.isdigit():
            return drone
        color = DRONE_COLORS[(int(number) - 1) % len(DRONE_COLORS)]
        return self.paint(drone, color)

    def move_label(self, move: str) -> str:
        """Return one move with the drone and the destination painted.

        Args:
            move: a move such as 'D1-roof1'.
        """
        if "-" not in move:
            return move
        cut = move.index("-")
        drone = move[:cut]
        target = move[cut + 1:]
        return f"{self.drone_label(drone)}-{self.zone_label(target)}"

    def show_header(self) -> None:
        """Print the zones of the map and what they mean."""
        start = self.network.get_start()
        end = self.network.get_end()
        print(self.title("Map"))
        print(
            f"  {self.network.nb_drones} drones, "
            f"{len(self.network.zones)} zones, "
            f"{len(self.network.connections)} connections"
        )
        print(f"  start: {self.zone_label(start.name)}")
        print(f"  end:   {self.zone_label(end.name)}")
        print(self.title("Zones"))
        for name in self.network.zones:
            zone = self.network.zones[name]
            sign = TYPE_SIGNS[zone.zone_type.value]
            print(
                f"  {sign} {self.zone_label(name, 20)} "
                f"{zone.zone_type.value:<11} "
                f"capacity {self.capacity_text(name)}"
            )
        print(self.title("Simulation"))

    def capacity_text(self, name: str) -> str:
        """Return the capacity of a zone as readable text.

        Args:
            name: the name of the zone.
        """
        zone = self.network.zones[name]
        if zone.is_start or zone.is_end:
            return "unlimited"
        return str(zone.max_drones)

    def title(self, text: str) -> str:
        """Return a small section title.

        Args:
            text: the words of the title.
        """
        if not self.colored:
            return f"\n{text}"
        return f"\n{BOLD}{text}{RESET}"

    def moves_line(self, moves: list[str]) -> str:
        """Return the moves of one turn, painted, in the official order.

        Args:
            moves: the moves played during this turn.
        """
        painted: list[str] = []
        for move in moves:
            painted.append(self.move_label(move))
        return " ".join(painted)

    def show_turn(self, number: int, moves: list[str]) -> None:
        """Print one turn with colors.

        Args:
            number: the number of the turn, starting at 1.
            moves: the moves played during this turn.
        """
        label = f"turn {number:>3}"
        if self.colored:
            label = f"{BOLD}{label}{RESET}"
        print(f"  {label}  " + self.moves_line(moves))

    def show_summary(self, turns: int) -> None:
        """Print the final result of the simulation.

        Args:
            turns: how many turns the simulation needed.
        """
        print(self.title("Result"))
        print(
            f"  {self.network.nb_drones} drones delivered "
            f"in {turns} turns"
        )
