from diplomacy.persistence.province import Province, Coast, ProvinceType


# We are not yet perfect when parsing the map. This file is a temporary hard-coded cheat to get around that.


# Create high seas and sands provinces
def create_high_seas_and_sands(provinces: set[Province], name_to_province: dict[str, Province]) -> None:
    # create provinces
    _create_high_province("NAO", 5, ProvinceType.SEA, provinces, name_to_province)
    _create_high_province("SAO", 5, ProvinceType.SEA, provinces, name_to_province)
    _create_high_province("INO", 5, ProvinceType.SEA, provinces, name_to_province)
    _create_high_province("NPO", 5, ProvinceType.SEA, provinces, name_to_province)
    _create_high_province("SPO", 5, ProvinceType.SEA, provinces, name_to_province)
    existing_sah = set()
    for province in provinces:
        if province.name[:3] == "SAH":  # These get created because they're land tiles, remove them
            existing_sah.add(province)
    provinces = provinces - existing_sah
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
    return provinces


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
        high_provinces.append(
            Province(
                name + str(i),
                [],
                None,
                None,
                province_type,
                False,
                set(),
                set(),
                None,
                None,
                None,
            )
        )

    provinces.update(high_provinces)
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
        coast = Coast(f"{province.name} {name}", None, None, adjacent, province)
        province.coasts.add(coast)


def fix_phantom_units(provinces: set[Province]):
    for province in provinces:
        if province.name == "Yucatan Channel":
            province.primary_unit_coordinate = (1028, 952)
            province.retreat_unit_coordinate = (1039, 921)
        if province.name == "SAH1":
            province.primary_unit_coordinate = (2029, 922)
            province.retreat_unit_coordinate = (2041, 935)
        if province.name == "SAH2":
            province.primary_unit_coordinate = (2100, 949)
            province.retreat_unit_coordinate = (2112, 961)
        if province.name == "SAH3":
            province.primary_unit_coordinate = (2129, 1017)
            province.retreat_unit_coordinate = (2141, 1029)
        if province.name == "Imerina":
            province.primary_unit_coordinate = (2632, 1518)
            province.retreat_unit_coordinate = (2648, 1485)
            province.coast().primary_unit_coordinate = province.primary_unit_coordinate
            province.coast().retreat_unit_coordinate = province.retreat_unit_coordinate

def set_secondary_locs(name_to_province: dict[str, set[Province]]):
    def set_one(name, primary, retreat):
        p: Province = name_to_province[name]
        # correct for inkscape giving top left, not middle coord
        primary = (primary[0] + 7.7655, primary[1] + 7.033)
        retreat = (retreat[0] + 7.7655, retreat[1] + 7.033)
        p.all_locs.add(primary)
        p.all_rets.add(retreat)
    
    set_one("NPO1", (3982.726, 874.217), (3994.726, 886.217))
    set_one("NPO2", (4059.726, 874.217), (4071.726, 886.217))
    set_one("NPO3", (4136.726, 874.217), (4148.726, 886.217))
    set_one("NPO4", (4021.226, 942.459), (4033.226, 954.459))
    set_one("NPO5", (4098.226, 942.401), (4110.226, 954.401))

    set_one("SPO1", (4061.260, 1509.495), (4073.260, 1521.495))
    set_one("SPO2", (4138.259, 1509.495), (4150.259, 1521.495))
    set_one("SPO3", (4215.260, 1510.000), (4227.260, 1522.000))
    set_one("SPO4", (4099.759, 1577.737), (4111.759, 1589.737))
    set_one("SPO5", (4176.760, 1577.678), (4188.760, 1589.678))

    set_one("Chukchi Sea", (28.000, 241.000), (72.908, 186.392))