"""Turn by turn simulation of the drone fleet."""

from __future__ import annotations

from connection import Connection
from drone import Drone
from exceptions import SimulationError
from network import Network
from pathfinder import Pathfinder
from zone import Zone, ZoneType

# Distance given to a zone the end cannot be reached from.
FAR_AWAY = 1000000000


class ExitPromise:
    """A place kept for a drone that must leave a zone next turn."""

    def __init__(self, zone: Zone, connection: Connection, turn: int) -> None:
        """Create a promise.

        Args:
            zone: the zone the drone must leave.
            connection: the way out kept for it.
            turn: the turn the promise was made, it lasts one more.
        """
        self.zone = zone
        self.connection = connection
        self.turn = turn


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
        self.next_id = 1
        self.delivered = 0
        self.turn = 0
        self.promises: list[ExitPromise] = []
        self.turns: list[list[str]] = []

    def prepare(self) -> None:
        """Measure the map before the first turn.

        The drones still waiting on the start zone are all alike, so
        they are only created when they take off. That keeps every turn
        cheap even with a huge fleet stuck behind a bottleneck.

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
        self.next_id = 1
        self.delivered = 0
        self.turn = 0
        self.promises = []
        self.turns = []
        if start is end:
            self.delivered = self.network.nb_drones

    def run(self) -> list[list[str]]:
        """Play the whole simulation and return the moves of each turn.

        Returns:
            One list of moves per turn.

        Every move brings a drone strictly closer to the end zone, so
        the loop always ends as long as each turn moves something.

        Raises:
            SimulationError: if the drones get stuck.
        """
        self.prepare()
        while not self.all_delivered():
            moves = self.play_turn()
            if len(moves) == 0:
                raise SimulationError(
                    "the drones cannot move any more, the map is stuck"
                )
            self.turns.append(moves)
        return self.turns

    def all_delivered(self) -> bool:
        """Return whether every drone reached the end zone."""
        return self.delivered == self.network.nb_drones

    def play_turn(self) -> list[str]:
        """Play one turn and return the moves it produced.

        Drones closer to the goal are served first, so that the place
        they free can be taken during the very same turn. The drones
        waiting on the start zone are the furthest, so they come last.
        """
        self.turn = self.turn + 1
        self.reset_links()
        moves: list[str] = []
        for drone in self.sorted_drones():
            if drone.is_flying:
                self.finish_flight(drone, moves)
            else:
                self.try_to_move(drone, moves)
        self.launch_from_start(moves)
        self.drop_old_promises()

        still_away: list[Drone] = []
        for drone in self.drones:
            if drone.delivered:
                self.delivered = self.delivered + 1
            else:
                still_away.append(drone)
        self.drones = still_away
        return moves

    def launch_from_start(self, moves: list[str]) -> None:
        """Send drones off the start zone while there is room.

        As soon as one waiting drone cannot leave, the next ones cannot
        either, since they stand in the same place.

        Args:
            moves: list collecting the moves of the turn.
        """
        start = self.network.get_start()
        waiting = self.network.nb_drones - (self.next_id - 1)
        while waiting > 0:
            drone = Drone(self.next_id, start)
            start.enter(drone.drone_id)
            if not self.try_to_move(drone, moves):
                start.leave(drone.drone_id)
                return
            self.next_id = self.next_id + 1
            self.drones.append(drone)
            waiting = waiting - 1

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
            return self.distances.get(drone.target.name, FAR_AWAY)
        return self.distances.get(drone.zone.name, FAR_AWAY)

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

    def try_to_move(self, drone: Drone, moves: list[str]) -> bool:
        """Move a drone one step closer to the end zone if it can.

        Args:
            drone: the drone to move.
            moves: list collecting the moves of the turn.

        Returns:
            True if the drone moved.
        """
        current = drone.zone
        options = self.sorted_options(current)
        for connection in options:
            other = connection.other_end(current)
            if not connection.has_room():
                continue
            if other.zone_type is ZoneType.RESTRICTED:
                if not self.book(other):
                    continue
                self.leave_for_flight(drone, connection, other, moves)
            else:
                promised = self.keep_promise(current, connection)
                if not promised and not other.has_room():
                    continue
                self.walk(drone, connection, other, moves)
            return True
        return False

    def book(self, target: Zone) -> bool:
        """Book a place in a zone for a drone about to fly toward it.

        A place is free right away most of the time. It can also be
        taken when a drone already inside leaves on the very turn the
        newcomer lands, which the rules allow. That departure is then
        promised: a place on its way out is kept for it, so no other
        drone can steal it and leave the newcomer with nowhere to land.

        Args:
            target: the restricted zone the drone aims for.

        Returns:
            True if the place is booked.
        """
        if target.is_end:
            return True
        if target.reserved + 1 > target.capacity:
            return False
        needed = len(target.occupants) + target.reserved + 1
        needed = needed - target.capacity - self.promised_from(target)
        if needed <= 0:
            return True

        exits = self.free_exits(target)
        total = 0
        for item in exits:
            total = total + item[1]
        if total < needed:
            return False
        for connection, room in exits:
            while room > 0 and needed > 0:
                self.promise(target, connection)
                room = room - 1
                needed = needed - 1
        return True

    def free_exits(self, zone: Zone) -> list[tuple[Connection, int]]:
        """List the ways out of a zone that can be promised next turn.

        Only plain zones are counted: leaving toward a restricted zone
        would need a booking of its own.

        Args:
            zone: the zone the drones would leave.

        Returns:
            Each usable connection with how many places it can promise.
        """
        here = self.distances.get(zone.name, FAR_AWAY)
        result: list[tuple[Connection, int]] = []
        for connection in self.network.neighbours(zone):
            other = connection.other_end(zone)
            if not other.zone_type.is_passable:
                continue
            if other.zone_type is ZoneType.RESTRICTED:
                continue
            if self.distances.get(other.name, FAR_AWAY) >= here:
                continue
            room = connection.max_link_capacity
            room = room - self.promised_on(connection)
            left = other.capacity - other.used
            if left < room:
                room = left
            if room > 0:
                result.append((connection, room))
        return result

    def promise(self, zone: Zone, connection: Connection) -> None:
        """Keep a place for a drone that must leave a zone next turn.

        Args:
            zone: the zone the drone leaves.
            connection: the way out kept for it.
        """
        connection.other_end(zone).reserve()
        self.promises.append(ExitPromise(zone, connection, self.turn))

    def promised_from(self, zone: Zone) -> int:
        """Count the departures promised this turn out of a zone."""
        total = 0
        for promise in self.promises:
            if promise.zone is zone and promise.turn == self.turn:
                total = total + 1
        return total

    def promised_on(self, connection: Connection) -> int:
        """Count the departures promised this turn on a connection."""
        total = 0
        for promise in self.promises:
            if (
                promise.connection is connection
                and promise.turn == self.turn
            ):
                total = total + 1
        return total

    def keep_promise(self, zone: Zone, connection: Connection) -> bool:
        """Use a place promised to a drone leaving a zone, if any.

        Args:
            zone: the zone the drone leaves.
            connection: the way out it takes.

        Returns:
            True if a promised place was given back for the drone.
        """
        for promise in self.promises:
            if promise.zone is zone and promise.connection is connection:
                self.promises.remove(promise)
                connection.other_end(zone).release()
                return True
        return False

    def drop_old_promises(self) -> None:
        """Give back the places promised last turn and never used."""
        kept: list[ExitPromise] = []
        for promise in self.promises:
            if promise.turn < self.turn:
                promise.connection.other_end(promise.zone).release()
            else:
                kept.append(promise)
        self.promises = kept

    def sorted_options(self, current: Zone) -> list[Connection]:
        """Return the useful connections, the most promising first.

        A connection is useful when it leads strictly closer to the end
        zone. Zones marked as priority come first when the cost is the
        same.

        Args:
            current: the zone the drone stands in.
        """
        here = self.distances.get(current.name, FAR_AWAY)
        order: list[tuple[int, int, int]] = []
        links = self.network.neighbours(current)
        position = 0
        for connection in links:
            other = connection.other_end(current)
            there = self.distances.get(other.name, FAR_AWAY)
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
