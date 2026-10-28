"""The whole network of zones and connections."""

from __future__ import annotations

from connection import Connection
from exceptions import SimulationError
from zone import Zone


class Network:
    """Hold every zone and every connection of a map."""

    def __init__(self, nb_drones: int = 0) -> None:
        """Create an empty network.

        Args:
            nb_drones: how many drones the map asks for.
        """
        self.nb_drones = nb_drones
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.links: dict[str, list[Connection]] = {}
        self.start: Zone | None = None
        self.end: Zone | None = None

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the network.

        Args:
            zone: the zone to store.
        """
        self.zones[zone.name] = zone
        self.links[zone.name] = []
        if zone.is_start:
            self.start = zone
        if zone.is_end:
            self.end = zone

    def has_zone(self, name: str) -> bool:
        """Return whether a zone with this name already exists."""
        return name in self.zones

    def add_connection(self, connection: Connection) -> None:
        """Add a connection and register it on both of its ends.

        Args:
            connection: the connection to store.
        """
        self.connections.append(connection)
        self.links[connection.zone_a.name].append(connection)
        self.links[connection.zone_b.name].append(connection)

    def has_connection(self, first: str, second: str) -> bool:
        """Return whether those two zones are already connected."""
        for connection in self.connections:
            if connection.links(first, second):
                return True
        return False

    def neighbours(self, zone: Zone) -> list[Connection]:
        """Return every connection attached to a zone.

        Args:
            zone: the zone to look around.
        """
        return self.links[zone.name]

    def get_start(self) -> Zone:
        """Return the start zone.

        Raises:
            SimulationError: if the map has no start zone.
        """
        if self.start is None:
            raise SimulationError("the map has no start zone")
        return self.start

    def get_end(self) -> Zone:
        """Return the end zone.

        Raises:
            SimulationError: if the map has no end zone.
        """
        if self.end is None:
            raise SimulationError("the map has no end zone")
        return self.end

    def reset(self) -> None:
        """Clear every runtime counter before a new simulation."""
        for name in self.zones:
            zone = self.zones[name]
            zone.occupants = set()
            zone.reserved = 0
        for connection in self.connections:
            connection.users = 0

    def __repr__(self) -> str:
        """Return a short representation used while debugging."""
        return (
            f"Network({len(self.zones)} zones, "
            f"{len(self.connections)} connections, "
            f"{self.nb_drones} drones)"
        )
