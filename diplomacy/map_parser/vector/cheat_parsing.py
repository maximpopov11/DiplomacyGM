from diplomacy.persistence.province import Province, Coast, ProvinceType


# TODO: (BETA) don't use any of the cheats
# We are not yet perfect when parsing the map. This file is a temporary hard-coded cheat to get around that.


# Create high seas and sands provinces
def create_high_seas_and_sands(provinces: set[Province], name_to_province: dict[str, Province]) -> None:
    # create provinces
    _create_high_province("NAO", 5, ProvinceType.SEA, provinces, name_to_province)
    _create_high_province("SAO", 5, ProvinceType.SEA, provinces, name_to_province)
    _create_high_province("INO", 5, ProvinceType.SEA, provinces, name_to_province)
    _create_high_province("NPO", 5, ProvinceType.SEA, provinces, name_to_province)
    _create_high_province("SPO", 5, ProvinceType.SEA, provinces, name_to_province)
    _create_high_province("SAH", 3, ProvinceType.LAND, provinces, name_to_province)

    # set adjacencies
    _set_adjacencies(
        name_to_province,
        "NAO",
        5,
        {
            name_to_province["Robertstorg"],
            name_to_province["Brattahlid"],
            name_to_province["Greenland Sea"],
            name_to_province["Rockall Rise"],
            name_to_province["Iberian Current"],
            name_to_province["Seewarte Seamounts"],
            name_to_province["SAO1"],
            name_to_province["SAO2"],
            name_to_province["SAO3"],
            name_to_province["SAO4"],
            name_to_province["SAO5"],
            name_to_province["Saragasso Sea"],
            name_to_province["Bermuda"],
            name_to_province["Massachusetts Bay"],
            name_to_province["St. Marguerite Baie"],
            name_to_province["Strait of Belle Isle"],
            name_to_province["Labrador Sea"],
        },
    )
    _set_adjacencies(
        name_to_province,
        "SAO",
        5,
        {
            name_to_province["NAO1"],
            name_to_province["NAO2"],
            name_to_province["NAO3"],
            name_to_province["NAO4"],
            name_to_province["NAO5"],
            name_to_province["Seewarte Seamounts"],
            name_to_province["Serra Leoa Rise"],
            name_to_province["Manden"],
            name_to_province["Gold Coast"],
            name_to_province["Guinea Rise"],
            name_to_province["Angola Basin"],
            name_to_province["St. Helena"],
            name_to_province["Cape Basin"],
            name_to_province["Southern Sea"],
            name_to_province["Argentine Basin"],
            name_to_province["Guanabara Bay"],
            name_to_province["Todos os Santos Bay"],
            name_to_province["Mauritsstad"],
            name_to_province["St. Marcos Bay"],
            name_to_province["Guiana Current"],
            name_to_province["Saragasso Sea"],
        },
    )
    _set_adjacencies(
        name_to_province,
        "INO",
        5,
        {
            name_to_province["Laccadive Plateau"],
            name_to_province["Maldives"],
            name_to_province["Gulf of Mannar"],
            name_to_province["Ceylon"],
            name_to_province["Gulf of Ceylon"],
            name_to_province["Cocos Basin"],
            name_to_province["Sumatra"],
            name_to_province["Mentawai Strait"],
            name_to_province["Timor Sea"],
            name_to_province["Kimberley"],
            name_to_province["Great Australian Bight"],
            name_to_province["Antarctic Basin"],
            name_to_province["Crozet Basin"],
            name_to_province["Reunion"],
            name_to_province["Mascarene Sea"],
            name_to_province["Somali Basin"],
        },
    )
    _set_adjacencies(
        name_to_province,
        "NPO",
        5,
        {
            name_to_province["Chukchi Sea"],
            name_to_province["North Equatorial Current"],
            name_to_province["Hawai'i"],
            name_to_province["Berlanga Ridge"],
            name_to_province["Guatemala Basin"],
            name_to_province["SPO1"],
            name_to_province["SPO2"],
            name_to_province["SPO3"],
            name_to_province["SPO4"],
            name_to_province["SPO5"],
            name_to_province["Solomon Islands"],
            name_to_province["Halmahera Sea"],
            name_to_province["Philippene Sea"],
            name_to_province["Kuroshio Current"],
            name_to_province["Edo"],
            name_to_province["Tsugaru Strait"],
            name_to_province["Kuril Sea"],
            name_to_province["Sea of Okhotsk"],
            name_to_province["Koryaks"],
        },
    )
    _set_adjacencies(
        name_to_province,
        "SPO",
        5,
        {
            name_to_province["NPO1"],
            name_to_province["NPO2"],
            name_to_province["NPO3"],
            name_to_province["NPO4"],
            name_to_province["NPO5"],
            name_to_province["Guatemala Basin"],
            name_to_province["Galapagos"],
            name_to_province["Peru Basin"],
            name_to_province["Roggeveen Basin"],
            name_to_province["Chiloe"],
            name_to_province["Mar de Hoces"],
            name_to_province["Antarctic Basin"],
            name_to_province["Aotearoa"],
            name_to_province["Gunai"],
            name_to_province["Coral Sea"],
            name_to_province["Solomon Islands"],
        },
    )
    _set_adjacencies(
        name_to_province,
        "SAH",
        3,
        {
            name_to_province["Ghadames"],
            name_to_province["Fezzan"],
            name_to_province["Zaghawa"],
            name_to_province["Darfur"],
            name_to_province["Kanem"],
            name_to_province["Hausa States"],
            name_to_province["Gurma"],
            name_to_province["Mossi"],
            name_to_province["Jenne"],
            name_to_province["Timbuktu"],
            name_to_province["Aswanik"],
            name_to_province["Regeibat"],
        },
    )


def _set_adjacencies(
    name_to_province: dict[str, Province],
    name: str,
    num: int,
    adjacent_provinces: set[Province],
) -> None:
    slots: list[Province] = []
    for i in range(1, num + 1):
        slot = name_to_province[name + str(i)]
        slots.append(slot)

    for slot in slots:
        for adjacent in adjacent_provinces:
            slot.adjacent.add(adjacent)
            adjacent.adjacent.add(slot)

        # should be adjacent to the other spaces in the high seas/sands
        for slot2 in slots:
            if slot != slot2:
                slot.adjacent.add(slot2)
                # the reciprocating adjacency will be added in another loop iteration


def _create_high_province(
    name: str,
    num: int,
    province_type: ProvinceType,
    provinces: set[Province],
    name_to_province: dict[str, Province],
) -> None:
    high_provinces = []
    for i in range(1, num + 1):
        high_provinces.append(Province(name + str(i), [], province_type, False, set(), set(), None, None, None))

    provinces.union(high_provinces)
    for province in high_provinces:
        name_to_province[province.name] = province


# Set coasts for all provinces with multiple coasts
def set_coasts(name_to_province: dict[str, Province]) -> None:
    _set_coasts(
        name_to_province["Panama"],
        {
            "nc": {
                name_to_province["Bay of Panama"],
            },
            "sc": {
                name_to_province["Colon Ridge"],
            },
        },
    )
    _set_coasts(
        name_to_province["Honduras"],
        {
            "nc": {
                name_to_province["Gulf of Honduras"],
                name_to_province["Bay of Panama"],
            },
            "sc": {
                name_to_province["Guatemala Basin"],
                name_to_province["Colon Ridge"],
            },
        },
    )
    _set_coasts(
        name_to_province["Yucatan"],
        {
            "nc": {
                name_to_province["Gulf of Mexico"],
                name_to_province["Yucatan Channel"],
            },
            "sc": {
                name_to_province["Guatemala Basin"],
            },
        },
    )
    _set_coasts(
        name_to_province["Mexico City"],
        {
            "ec": {
                name_to_province["Gulf of Mexico"],
            },
            "wc": {
                name_to_province["Guatemala Basin"],
                name_to_province["Berlanga Ridge"],
                name_to_province["Viscaino Bay"],
            },
        },
    )
    _set_coasts(
        name_to_province["Mexico City"],
        {
            "ec": {
                name_to_province["Gulf of Mexico"],
            },
            "wc": {
                name_to_province["Guatemala Basin"],
                name_to_province["Berlanga Ridge"],
                name_to_province["Viscaino Bay"],
            },
        },
    )
    _set_coasts(
        name_to_province["Nakhon Si"],
        {
            "ec": {
                name_to_province["Gulf of Siam"],
                name_to_province["Natuna Sea"],
            },
            "wc": {
                name_to_province["Malacca Strait"],
            },
        },
    )
    _set_coasts(
        name_to_province["Pyeongyang"],
        {
            "ec": {
                name_to_province["Oriental Sea"],
                name_to_province["Tsushima"],
            },
            "wc": {
                name_to_province["Beizhili Sea"],
                name_to_province["Yellow Sea"],
            },
        },
    )
    _set_coasts(
        name_to_province["Chukchis"],
        {
            "ec": {
                name_to_province["Chukchi Sea"],
            },
            "wc": {
                name_to_province["Sea of Okhotsk"],
            },
        },
    )
    _set_coasts(
        name_to_province["Rome"],
        {
            "ec": {
                name_to_province["Adriatic Sea"],
            },
            "wc": {
                name_to_province["Ligurian Sea"],
                name_to_province["Tyrrhenian Sea"],
            },
        },
    )


# Remove coasts for canal provinces
def set_canals(name_to_province: dict[str, Province]) -> None:
    _set_coasts(
        name_to_province["Cairo"],
        {
            "coast #1": {
                name_to_province["Levantine Sea"],
                name_to_province["Red Sea"],
            }
        },
    )
    _set_coasts(
        name_to_province["Kiel"],
        {
            "coast #1": {
                name_to_province["Wadden Sea"],
                name_to_province["Copenhagen"],
            }
        },
    )
    _set_coasts(
        name_to_province["Constantinople"],
        {
            "coast #1": {
                name_to_province["Black Sea"],
                name_to_province["Aegean Sea"],
            }
        },
    )


def _set_coasts(province: Province, name_to_adjacent: dict[str, set[Province]]):
    province.coasts = set()
    for name, adjacent in name_to_adjacent.items():
        coast = Coast(f"{province.name} {name}", adjacent)
        province.coasts.add(coast)
