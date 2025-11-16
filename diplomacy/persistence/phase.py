from __future__ import annotations


class Phase:
    def __init__(self, name: str, shortname: str, index: int, next_phase: Phase, previous_phase: Phase):
        self.name: str = name
        self.shortname: shortname = shortname
        self.index = index
        self.next: Phase = next_phase
        self.previous: Phase = previous_phase

    def __str__(self):
        return self.name


_winter_builds = Phase("Winter Builds", "wa", 4, None, None)
_fall_retreats = Phase("Fall Retreats", "fr", 3, _winter_builds, None)
_fall_moves = Phase("Fall Moves", "fm", 2, _fall_retreats, None)
_spring_retreats = Phase("Spring Retreats", "sr", 1, _fall_moves, None)
_spring_moves = Phase("Spring Moves", "sm", 0, _spring_retreats, None)

_winter_builds.next = _spring_moves
_winter_builds.previous = _fall_retreats
_fall_retreats.previous = _fall_moves
_fall_moves.previous = _spring_retreats
_spring_retreats.previous = _spring_moves
_spring_moves.previous = _winter_builds

_name_to_phase: dict[str, Phase] = {
    "Spring Moves": _spring_moves,
    "Spring Retreats": _spring_retreats,
    "Fall Moves": _fall_moves,
    "Fall Retreats": _fall_retreats,
    "Winter Builds": _winter_builds,
}


def get(name: str) -> Phase:
    return _name_to_phase[name]


def initial() -> Phase:
    return _spring_moves


def is_moves(phase: Phase) -> bool:
    return phase == _spring_moves or phase == _fall_moves


def is_retreats(phase: Phase) -> bool:
    return phase == _spring_retreats or phase == _fall_retreats


def is_builds(phase: Phase) -> bool:
    return phase == _winter_builds
