"""Connections (edges) between two zones."""

from __future__ import annotations

from exceptions import SimulationError
from zone import Zone


class Connection:
    """A bidirectional link between two zones."""

    def __init__(
        self,
        zone_a: Zone,
        zone_b: Zone,
        max_link_capacity: int = 1,
    ) -> None:
        """Create a connection.

        Args:
            zone_a: first end of the link.
            zone_b: second end of the link.
            max_link_capacity: how many drones may cross it at once.
        """
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = max_link_capacity
        self.users = 0

    @property
    def name(self) -> str:
        """Return the name used in the output, as written in the map."""
        return f"{self.zone_a.name}-{self.zone_b.name}"

    def links(self, first: str, second: str) -> bool:
        """Return whether this connection joins those two zone names."""
        if self.zone_a.name == first and self.zone_b.name == second:
            return True
        if self.zone_a.name == second and self.zone_b.name == first:
            return True
        return False

    def other_end(self, zone: Zone) -> Zone:
        """Return the zone at the other end of the link.

        Args:
            zone: one of the two ends.

        Raises:
            SimulationError: if the zone is not an end of this link.
        """
        if zone is self.zone_a:
            return self.zone_b
        if zone is self.zone_b:
            return self.zone_a
        raise SimulationError(
            f"zone {zone.name} is not part of connection {self.name}"
        )

    def has_room(self) -> bool:
        """Return whether one more drone may cross this turn."""
        return self.users < self.max_link_capacity

    def __repr__(self) -> str:
        """Return a short representation used while debugging."""
        return (
            f"Connection({self.name}, "
            f"{self.users}/{self.max_link_capacity})"
        )
