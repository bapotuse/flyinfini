"""Shortest path computation, written without any graph library."""

from __future__ import annotations

from network import Network
from zone import Zone

UNREACHABLE = -1


class Pathfinder:
    """Compute, for every zone, the cost in turns to reach a target."""

    def __init__(self, network: Network) -> None:
        """Create a pathfinder working on a network.

        Args:
            network: the network to explore.
        """
        self.network = network

    def distances_to(self, target: Zone) -> dict[str, int]:
        """Return the cost in turns from every zone to the target.

        This is Dijkstra's algorithm, walked backwards from the target.
        Entering a zone costs what its type says, so the price of a
        step belongs to the zone the drone arrives in.

        Args:
            target: the zone every drone wants to reach.

        Returns:
            A dictionary giving the cost of each reachable zone.
        """
        distances: dict[str, int] = {}
        done: dict[str, bool] = {}
        if not target.zone_type.is_passable:
            return distances
        distances[target.name] = 0

        while True:
            current_name = self.closest_unvisited(distances, done)
            if current_name == "":
                break
            done[current_name] = True
            current = self.network.zones[current_name]
            step = current.zone_type.cost
            for connection in self.network.neighbours(current):
                other = connection.other_end(current)
                if not other.zone_type.is_passable:
                    continue
                new_distance = distances[current_name] + step
                if other.name not in distances:
                    distances[other.name] = new_distance
                elif new_distance < distances[other.name]:
                    distances[other.name] = new_distance
        return distances

    def closest_unvisited(
        self, distances: dict[str, int], done: dict[str, bool]
    ) -> str:
        """Return the known zone with the smallest cost left to visit.

        Args:
            distances: costs found so far.
            done: zones already handled.

        Returns:
            The name of the zone, or an empty string when none is left.
        """
        best_name = ""
        best_value = 0
        for name in distances:
            if name in done:
                continue
            if best_name == "" or distances[name] < best_value:
                best_name = name
                best_value = distances[name]
        return best_name

    def distance_of(self, distances: dict[str, int], zone: Zone) -> int:
        """Return the cost of a zone, or UNREACHABLE when unknown.

        Args:
            distances: costs returned by distances_to().
            zone: the zone to look up.
        """
        if zone.name not in distances:
            return UNREACHABLE
        return distances[zone.name]
