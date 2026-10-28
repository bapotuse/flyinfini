"""The drones that travel across the network."""

from __future__ import annotations

from connection import Connection
from zone import Zone


class Drone:
    """One drone, with the place where it currently is."""

    def __init__(self, drone_id: int, start: Zone) -> None:
        """Create a drone sitting in the start zone.

        Args:
            drone_id: number of the drone, starting at 1.
            start: zone where every drone begins.
        """
        self.drone_id = drone_id
        self.zone = start
        self.connection: Connection | None = None
        self.target: Zone | None = None
        self.delivered = False

    @property
    def name(self) -> str:
        """Return the name used in the output, like 'D1'."""
        return f"D{self.drone_id}"

    @property
    def is_flying(self) -> bool:
        """Return whether the drone is currently on a connection."""
        return self.connection is not None

    def take_off(self, connection: Connection, target: Zone) -> None:
        """Send the drone on a connection toward a restricted zone.

        Args:
            connection: the link the drone starts crossing.
            target: the zone it will reach next turn.
        """
        self.connection = connection
        self.target = target

    def land(self, zone: Zone) -> None:
        """Place the drone inside a zone and stop any flight.

        Args:
            zone: the zone the drone reaches.
        """
        self.zone = zone
        self.connection = None
        self.target = None

    def __repr__(self) -> str:
        """Return a short representation used while debugging."""
        if self.connection is not None:
            return f"Drone({self.name}, flying on {self.connection.name})"
        return f"Drone({self.name}, in {self.zone.name})"
