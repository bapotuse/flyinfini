"""Read a map file and build the matching network."""

from __future__ import annotations

from connection import Connection
from exceptions import ParseError
from network import Network
from zone import Zone, ZoneType

MAX_DRONES = 1000000
ZONE_KEYS = ["zone", "color", "max_drones"]
LINK_KEYS = ["max_link_capacity"]


class MapParser:
    """Turn the text of a map file into a Network object."""

    def __init__(self) -> None:
        """Create a parser with an empty network."""
        self.network = Network()
        self.nb_drones_seen = False
        self.start_seen = False
        self.end_seen = False

    def parse(self, path: str) -> Network:
        """Read a map file and return the network it describes.

        Args:
            path: path of the map file.

        Returns:
            The network built from the file.

        Raises:
            ParseError: if the file does not follow the expected format.
        """
        try:
            with open(path, "r", encoding="utf-8") as map_file:
                lines = map_file.readlines()
        except OSError as error:
            raise ParseError(0, f"cannot read the map file: {error}")
        except UnicodeDecodeError:
            raise ParseError(0, "the map file is not valid UTF-8 text")

        number = 0
        for raw_line in lines:
            number = number + 1
            line = self.clean(raw_line)
            if line != "":
                self.parse_line(number, line)

        self.check_end_of_file()
        return self.network

    def clean(self, raw_line: str) -> str:
        """Remove the comment part and the spaces around a line.

        Args:
            raw_line: a line as read from the file.
        """
        line = raw_line
        if "#" in line:
            line = line[:line.index("#")]
        return line.strip()

    def parse_line(self, number: int, line: str) -> None:
        """Dispatch one meaningful line to the right reader.

        Args:
            number: 1-based number of the line.
            line: the cleaned line.

        Raises:
            ParseError: if the line does not start with a known prefix.
        """
        if ":" not in line:
            raise ParseError(number, f"missing ':' in '{line}'")
        prefix = line[:line.index(":")].strip()
        rest = line[line.index(":") + 1:].strip()

        if prefix == "nb_drones":
            self.read_nb_drones(number, rest)
        elif prefix == "start_hub":
            self.read_zone(number, rest, True, False)
        elif prefix == "end_hub":
            self.read_zone(number, rest, False, True)
        elif prefix == "hub":
            self.read_zone(number, rest, False, False)
        elif prefix == "connection":
            self.read_connection(number, rest)
        else:
            raise ParseError(number, f"unknown line type '{prefix}'")

    def read_nb_drones(self, number: int, rest: str) -> None:
        """Read the 'nb_drones:' line.

        Args:
            number: 1-based number of the line.
            rest: text written after the prefix.

        Raises:
            ParseError: if the value is wrong or written twice.
        """
        if self.nb_drones_seen:
            raise ParseError(number, "nb_drones is defined twice")
        value = self.to_int(number, rest, "nb_drones")
        if value <= 0:
            raise ParseError(number, "nb_drones must be a positive integer")
        if value > MAX_DRONES:
            raise ParseError(
                number, f"nb_drones is too large (at most {MAX_DRONES})"
            )
        self.network.nb_drones = value
        self.nb_drones_seen = True

    def read_zone(
        self,
        number: int,
        rest: str,
        is_start: bool,
        is_end: bool,
    ) -> None:
        """Read a zone line and add the zone to the network.

        Args:
            number: 1-based number of the line.
            rest: text written after the prefix.
            is_start: True when the line is a start_hub.
            is_end: True when the line is an end_hub.

        Raises:
            ParseError: if the zone is invalid or already defined.
        """
        if not self.nb_drones_seen:
            raise ParseError(number, "nb_drones must be the first line")
        if is_start and self.start_seen:
            raise ParseError(number, "there is more than one start_hub")
        if is_end and self.end_seen:
            raise ParseError(number, "there is more than one end_hub")

        body, metadata = self.split_metadata(number, rest)
        parts = body.split()
        if len(parts) != 3:
            raise ParseError(
                number, "a zone needs a name and two coordinates"
            )

        name = parts[0]
        if "-" in name:
            raise ParseError(number, f"zone name '{name}' contains a dash")
        if self.network.has_zone(name):
            raise ParseError(number, f"zone '{name}' is defined twice")

        x = self.to_int(number, parts[1], "the x coordinate")
        y = self.to_int(number, parts[2], "the y coordinate")
        self.check_keys(number, metadata, ZONE_KEYS)

        zone_type = ZoneType.NORMAL
        if "zone" in metadata:
            zone_type = self.to_zone_type(number, metadata["zone"])

        color = None
        if "color" in metadata:
            color = metadata["color"]

        max_drones = 1
        if "max_drones" in metadata:
            max_drones = self.to_int(
                number, metadata["max_drones"], "max_drones"
            )
            if max_drones <= 0:
                raise ParseError(
                    number, "max_drones must be a positive integer"
                )

        zone = Zone(
            name, x, y, zone_type, color, max_drones, is_start, is_end
        )
        self.network.add_zone(zone)
        if is_start:
            self.start_seen = True
        if is_end:
            self.end_seen = True

    def read_connection(self, number: int, rest: str) -> None:
        """Read a connection line and add the link to the network.

        Args:
            number: 1-based number of the line.
            rest: text written after the prefix.

        Raises:
            ParseError: if the connection is invalid or duplicated.
        """
        body, metadata = self.split_metadata(number, rest)
        parts = body.split()
        if len(parts) != 1:
            raise ParseError(number, "a connection needs 'zone1-zone2'")

        names = parts[0].split("-")
        if len(names) != 2 or names[0] == "" or names[1] == "":
            raise ParseError(
                number, f"'{parts[0]}' is not a valid 'zone1-zone2' pair"
            )

        first = names[0]
        second = names[1]
        if not self.network.has_zone(first):
            raise ParseError(number, f"unknown zone '{first}'")
        if not self.network.has_zone(second):
            raise ParseError(number, f"unknown zone '{second}'")
        if first == second:
            raise ParseError(number, f"zone '{first}' links to itself")
        if self.network.has_connection(first, second):
            raise ParseError(
                number, f"connection '{first}-{second}' is defined twice"
            )

        self.check_keys(number, metadata, LINK_KEYS)
        capacity = 1
        if "max_link_capacity" in metadata:
            capacity = self.to_int(
                number, metadata["max_link_capacity"], "max_link_capacity"
            )
            if capacity <= 0:
                raise ParseError(
                    number, "max_link_capacity must be a positive integer"
                )

        connection = Connection(
            self.network.zones[first], self.network.zones[second], capacity
        )
        self.network.add_connection(connection)

    def split_metadata(
        self, number: int, rest: str
    ) -> tuple[str, dict[str, str]]:
        """Split a line into its body and its [key=value] block.

        Args:
            number: 1-based number of the line.
            rest: text written after the prefix.

        Returns:
            The body of the line and the metadata as a dictionary.

        Raises:
            ParseError: if the brackets or the pairs are malformed.
        """
        if "[" not in rest and "]" not in rest:
            return rest, {}
        if "[" not in rest or "]" not in rest:
            raise ParseError(number, "the metadata brackets are not closed")

        open_index = rest.index("[")
        close_index = rest.index("]")
        if close_index < open_index:
            raise ParseError(number, "the metadata brackets are reversed")
        if rest[close_index + 1:].strip() != "":
            raise ParseError(number, "text found after the metadata block")

        body = rest[:open_index].strip()
        inside = rest[open_index + 1:close_index].strip()
        metadata: dict[str, str] = {}
        if inside == "":
            return body, metadata

        for item in inside.split():
            if item.count("=") != 1:
                raise ParseError(
                    number, f"'{item}' is not a 'key=value' pair"
                )
            key = item[:item.index("=")].strip()
            value = item[item.index("=") + 1:].strip()
            if key == "" or value == "":
                raise ParseError(
                    number, f"'{item}' is not a 'key=value' pair"
                )
            if key in metadata:
                raise ParseError(number, f"'{key}' is given twice")
            metadata[key] = value
        return body, metadata

    def check_keys(
        self, number: int, metadata: dict[str, str], allowed: list[str]
    ) -> None:
        """Make sure every metadata key is expected here.

        Args:
            number: 1-based number of the line.
            metadata: the pairs read inside the brackets.
            allowed: the keys accepted on this kind of line.

        Raises:
            ParseError: if an unknown key is found.
        """
        for key in metadata:
            if key not in allowed:
                raise ParseError(number, f"unknown metadata key '{key}'")

    def to_int(self, number: int, text: str, what: str) -> int:
        """Convert a piece of text into an integer.

        Only plain digits, with an optional leading '-', are accepted:
        int() alone would also take '+5', '1_000' or ' 5'.

        Args:
            number: 1-based number of the line.
            text: the text to convert.
            what: name of the value, used in the error message.

        Raises:
            ParseError: if the text is not an integer.
        """
        digits = text
        if digits.startswith("-"):
            digits = digits[1:]
        if digits == "" or not digits.isascii() or not digits.isdigit():
            raise ParseError(
                number, f"{what} must be an integer, got '{text}'"
            )
        return int(text)

    def to_zone_type(self, number: int, text: str) -> ZoneType:
        """Convert a piece of text into a zone type.

        Args:
            number: 1-based number of the line.
            text: the text to convert.

        Raises:
            ParseError: if the text is not a known zone type.
        """
        try:
            return ZoneType(text)
        except ValueError:
            raise ParseError(number, f"unknown zone type '{text}'")

    def check_end_of_file(self) -> None:
        """Make sure the map holds everything it needs.

        Raises:
            ParseError: if a mandatory piece is missing.
        """
        if not self.nb_drones_seen:
            raise ParseError(0, "the map does not define nb_drones")
        if not self.start_seen:
            raise ParseError(0, "the map has no start_hub")
        if not self.end_seen:
            raise ParseError(0, "the map has no end_hub")
