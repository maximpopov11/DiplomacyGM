# TODO - move this somewhere that makes more sense
from diplomacy.persistence.province import Coast, Location, Province


def get_adjacent_provinces(location: Location) -> set[Province]:
    if isinstance(location, Coast):
        return location.adjacent_seas | {coast.province for coast in location.get_adjacent_coasts()}
    if isinstance(location, Province):
        return location.adjacent
    raise ValueError(f"Location {location} should be Coast or Province")