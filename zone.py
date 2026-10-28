"""Zones that make up the drone network."""

from __future__ import annotations

import sys
from enum import Enum

from exceptions import SimulationError

UNLIMITED: int = sys.maxsize


class ZoneType(Enum):
    """Type of a zone, written as-is in the map file."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def cost(self) -> int:
        """Return how many turns entering such a zone costs."""
        if self is ZoneType.RESTRICTED:
            return 2
        return 1

    @property
    def is_passable(self) -> bool:
        """Return whether a drone may enter such a zone."""
        return self is not ZoneType.BLOCKED


class Zone:
    """A single zone of the network."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        color: str | None = None,
        max_drones: int = 1,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Create a zone.

        Args:
            name: unique name of the zone.
            x: horizontal coordinate.
            y: vertical coordinate.
            zone_type: type driving cost and accessibility.
            color: optional color used by the display.
            max_drones: how many drones may stand here at once.
            is_start: True for the start hub.
            is_end: True for the end hub.
        """
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_drones = max_drones
        self.is_start = is_start
        self.is_end = is_end
        self.occupants: set[int] = set()
        self.reserved = 0

    @property
    def capacity(self) -> int:
        """Return the real capacity, ignoring max_drones on start/end."""
        if self.is_start or self.is_end:
            return UNLIMITED
        return self.max_drones

    @property
    def used(self) -> int:
        """Return how many places are taken or booked right now."""
        return len(self.occupants) + self.reserved

    def has_room(self, incoming: int = 1) -> bool:
        """Return whether `incoming` more drones fit in this zone."""
        if not self.zone_type.is_passable:
            return False
        return self.used + incoming <= self.capacity

    def reserve(self) -> None:
        """Book one place for a drone that is still flying to this zone."""
        self.reserved = self.reserved + 1

    def release(self) -> None:
        """Give back a place booked by reserve()."""
        if self.reserved > 0:
            self.reserved = self.reserved - 1

    def enter(self, drone_id: int) -> None:
        """Add a drone to this zone.

        Args:
            drone_id: identifier of the arriving drone.

        Raises:
            SimulationError: if the zone has no room left.
        """
        if not self.has_room():
            raise SimulationError(f"zone {self.name} is full")
        self.occupants.add(drone_id)

    def leave(self, drone_id: int) -> None:
        """Remove a drone from this zone.

        Args:
            drone_id: identifier of the leaving drone.

        Raises:
            SimulationError: if the drone is not in this zone.
        """
        if drone_id not in self.occupants:
            raise SimulationError(
                f"drone {drone_id} is not in zone {self.name}"
            )
        self.occupants.discard(drone_id)

    def __repr__(self) -> str:
        """Return a short representation used while debugging."""
        if self.capacity == UNLIMITED:
            limit = "inf"
        else:
            limit = str(self.capacity)
        return (
            f"Zone({self.name}, {self.x}, {self.y}, "
            f"{self.zone_type.value}, {len(self.occupants)}/{limit})"
        )
