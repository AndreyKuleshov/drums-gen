from enum import StrEnum


class Hand(StrEnum):
    L = "L"
    R = "R"

    def other(self) -> "Hand":
        return Hand.L if self is Hand.R else Hand.R


class Articulation(StrEnum):
    NORMAL = "normal"
    FLAM = "flam"
    DRAG = "drag"
    BUZZ = "buzz"


class Surface(StrEnum):
    SNARE = "snare"


class AccentMode(StrEnum):
    RUDIMENT = "rudiment"
    METRIC = "metric"
    BOTH = "both"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    MID = "mid"
    PRO = "pro"
