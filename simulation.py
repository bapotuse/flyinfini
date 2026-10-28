"""Turn by turn simulation of the drone fleet."""

from __future__ import annotations

from connection import Connection
from drone import Drone
from exceptions import SimulationError
from network import Network
from pathfinder import Pathfinder
from zone import Zone, ZoneType

MAX_TURNS = 10000


class Simulation:
    """Move every drone from the start zone to the end zone."""

    def __init__(self, network: Network) -> None:
        """Create a simulation for a network.

        Args:
            network: the network the drones fly in.
        """
        self.network = network
        self.pathfinder = Pathfinder(network)
        self.distances: dict[str, int] = {}
        self.drones: list[Drone] = []
        self.turns: list[list[str]] = []

    def prepare(self) -> None:
        """Place every drone on the start zone and measure the map.

        Raises:
            SimulationError: if no path joins the start and the end.
        """
        start = self.network.get_start()
        end = self.network.get_end()
        self.network.reset()
        self.distances = self.pathfinder.distances_to(end)
        if start.name not in self.distances:
            raise SimulationError(
                "no path connects the start zone to the end zone"
            )

        self.drones = []
        self.turns = []
        number = 0
        while number < self.network.nb_drones:
            number = number + 1
            drone = Drone(number, start)
            start.enter(drone.drone_id)
            if start is end:
                drone.delivered = True
            self.drones.append(drone)

    def run(self) -> list[list[str]]:
        """Play the whole simulation and return the moves of each turn.

        Returns:
            One list of moves per turn.

        Raises:
            SimulationError: if the drones get stuck.
        """
        self.prepare()
        while not self.all_delivered():
            if len(self.turns) >= MAX_TURNS:
                raise SimulationError("the simulation runs for too long")
            moves = self.play_turn()
            if len(moves) == 0:
                raise SimulationError(
                    "the drones cannot move any more, the map is stuck"
                )
            self.turns.append(moves)
        return self.turns

    def all_delivered(self) -> bool:
        """Return whether every drone reached the end zone."""
        for drone in self.drones:
            if not drone.delivered:
                return False
        return True

    def play_turn(self) -> list[str]:
        """Play one turn and return the moves it produced.

        Drones closer to the goal are served first, so that the place
        they free can be taken during the very same turn.
        """
        self.reset_links()
        moves: list[str] = []
        for drone in self.sorted_drones():
            if drone.delivered:
                continue
            if drone.is_flying:
                self.finish_flight(drone, moves)
            else:
                self.try_to_move(drone, moves)
        return moves

    def reset_links(self) -> None:
        """Count again how many drones sit on each connection."""
        for connection in self.network.connections:
            connection.users = 0
        for drone in self.drones:
            if drone.connection is not None:
                drone.connection.users = drone.connection.users + 1

    def sorted_drones(self) -> list[Drone]:
        """Return the drones, the closest to the end zone first.

        When two drones are as close, the one already standing in a
        zone is served before the one still flying toward it, so the
        place it frees can be used during the same turn.
        """
        order: list[tuple[int, int, int]] = []
        position = 0
        for drone in self.drones:
            if drone.is_flying:
                rank = 1
            else:
                rank = 0
            order.append((self.drone_distance(drone), rank, position))
            position = position + 1
        order.sort()

        result: list[Drone] = []
        for item in order:
            result.append(self.drones[item[2]])
        return result

    def drone_distance(self, drone: Drone) -> int:
        """Return how many turns a drone still needs to reach the end.

        Args:
            drone: the drone to measure.
        """
        if drone.target is not None:
            return self.distances.get(drone.target.name, MAX_TURNS)
        return self.distances.get(drone.zone.name, MAX_TURNS)

    def finish_flight(self, drone: Drone, moves: list[str]) -> None:
        """Land a drone that was crossing a connection.

        Args:
            drone: the flying drone.
            moves: list collecting the moves of the turn.

        Raises:
            SimulationError: if the drone has no destination.
        """
        connection = drone.connection
        target = drone.target
        if connection is None or target is None:
            raise SimulationError(f"drone {drone.name} flies nowhere")

        connection.users = connection.users - 1
        target.release()
        target.enter(drone.drone_id)
        drone.land(target)
        if target.is_end:
            drone.delivered = True
        moves.append(f"{drone.name}-{target.name}")

    def try_to_move(self, drone: Drone, moves: list[str]) -> None:
        """Move a drone one step closer to the end zone if it can.

        Args:
            drone: the drone to move.
            moves: list collecting the moves of the turn.
        """
        current = drone.zone
        options = self.sorted_options(current)
        for connection in options:
            other = connection.other_end(current)
            if not connection.has_room():
                continue
            if other.zone_type is ZoneType.RESTRICTED:
                if not self.can_book(other):
                    continue
                self.leave_for_flight(drone, connection, other, moves)
            else:
                if not other.has_room():
                    continue
                self.walk(drone, connection, other, moves)
            return

    def can_book(self, target: Zone) -> bool:
        """Return whether a drone may start flying toward a zone.

        A place is free right away most of the time. It can also be
        taken when the drones already inside will be able to leave on
        the very turn the newcomer lands, which the rules allow.

        Args:
            target: the restricted zone the drone aims for.
        """
        if target.is_end:
            return True
        if target.reserved + 1 > target.capacity:
            return False
        needed = len(target.occupants) + target.reserved + 1
        needed = needed - target.capacity
        if needed <= 0:
            return True
        return self.free_exits(target) >= needed

    def free_exits(self, zone: Zone) -> int:
        """Count how many drones may leave a zone on the next turn.

        Args:
            zone: the zone the drones would leave.
        """
        here = self.distances.get(zone.name, MAX_TURNS)
        total = 0
        for connection in self.network.neighbours(zone):
            other = connection.other_end(zone)
            if not other.zone_type.is_passable:
                continue
            if self.distances.get(other.name, MAX_TURNS) >= here:
                continue
            room = connection.max_link_capacity
            if not other.is_start and not other.is_end:
                left = other.capacity - other.used
                if left < room:
                    room = left
            if room > 0:
                total = total + room
        return total

    def sorted_options(self, current: Zone) -> list[Connection]:
        """Return the useful connections, the most promising first.

        A connection is useful when it leads strictly closer to the end
        zone. Zones marked as priority come first when the cost is the
        same.

        Args:
            current: the zone the drone stands in.
        """
        here = self.distances.get(current.name, MAX_TURNS)
        order: list[tuple[int, int, int]] = []
        links = self.network.neighbours(current)
        position = 0
        for connection in links:
            other = connection.other_end(current)
            there = self.distances.get(other.name, MAX_TURNS)
            if there < here:
                if other.zone_type is ZoneType.PRIORITY:
                    rank = 0
                else:
                    rank = 1
                order.append((there, rank, position))
            position = position + 1
        order.sort()

        result: list[Connection] = []
        for item in order:
            result.append(links[item[2]])
        return result

    def leave_for_flight(
        self,
        drone: Drone,
        connection: Connection,
        target: Zone,
        moves: list[str],
    ) -> None:
        """Start a two turn move toward a restricted zone.

        The place in the target zone is booked right away, so the drone
        is sure to land next turn instead of waiting on the connection.

        Args:
            drone: the drone that takes off.
            connection: the link it starts crossing.
            target: the restricted zone it aims for.
            moves: list collecting the moves of the turn.
        """
        drone.zone.leave(drone.drone_id)
        connection.users = connection.users + 1
        target.reserve()
        drone.take_off(connection, target)
        moves.append(f"{drone.name}-{connection.name}")

    def walk(
        self,
        drone: Drone,
        connection: Connection,
        target: Zone,
        moves: list[str],
    ) -> None:
        """Move a drone to a neighbour zone in a single turn.

        Args:
            drone: the drone that moves.
            connection: the link it uses.
            target: the zone it reaches.
            moves: list collecting the moves of the turn.
        """
        drone.zone.leave(drone.drone_id)
        connection.users = connection.users + 1
        target.enter(drone.drone_id)
        drone.land(target)
        if target.is_end:
            drone.delivered = True
        moves.append(f"{drone.name}-{target.name}")
