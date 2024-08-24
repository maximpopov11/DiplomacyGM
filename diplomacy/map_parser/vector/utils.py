from xml.etree.ElementTree import Element

from diplomacy.persistence.player import Player


def get_player(element: Element, color_to_player: dict[str, Player]) -> Player:
    style = element.get("style").split(";")
    for value in style:
        prefix = "fill:#"
        if value.startswith(prefix):
            color = value[len(prefix) :]
            return color_to_player[color]
