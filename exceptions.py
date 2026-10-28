class FlyInError(Exception):
    """Base class for every error raised by this program."""


class ParseError(FlyInError):
    """Raised when the map file does not respect the expected format."""

    def __init__(self, line_number: int, message: str) -> None:
        """Build a parsing error.

        Args:
            line_number: 1-based number of the faulty line.
            message: human readable cause of the failure.
        """
        self.line_number = line_number
        self.message = message
        super().__init__(f"line {line_number}: {message}")


class SimulationError(FlyInError):
    """Raised when a valid map cannot be simulated."""
