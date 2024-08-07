from __future__ import annotations


class Phase:
    def __init__(self, name: str):
        self.name = name
        self.next = None


spring_moves = Phase("Spring Moves")
spring_retreats = Phase("Spring Retreats")
fall_moves = Phase("Fall Moves")
fall_retreats = Phase("Fall Retreats")
winter_adjustments = Phase("Winter Adjustments")

spring_moves.next = spring_retreats
spring_retreats.next = fall_moves
fall_moves.next = fall_retreats
fall_retreats.next = winter_adjustments
winter_adjustments.next = spring_moves


def is_moves_phase(phase: Phase) -> bool:
    return phase == spring_moves or phase == fall_moves


def is_retreats_phase(phase: Phase) -> bool:
    return phase == spring_retreats or phase == fall_retreats


def is_adjustments_phase(phase: Phase) -> bool:
    return phase == winter_adjustments
