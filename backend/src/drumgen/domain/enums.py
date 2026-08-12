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
    HIHAT = "hihat"
    HIHAT_OPEN = "hihat_open"
    KICK = "kick"
    TOM_HIGH = "tom_high"
    TOM_MID = "tom_mid"
    TOM_LOW = "tom_low"


class AccentMode(StrEnum):
    RUDIMENT = "rudiment"
    METRIC = "metric"
    BOTH = "both"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    MID = "mid"
    PRO = "pro"
