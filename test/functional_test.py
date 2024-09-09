from bot import command
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.phase import fall_retreats
from test import mock

# guilds
_GUILD = 1

# roles
_GM_ROLE = "GM"

# channels
_GM_CHANNEL = "admin-chat"


def test() -> None:
    try:
        _setup()
    except:
        # we're not testing create_game
        pass

    # TODO: (!) uncomment these
    # test_ping()
    # test_order()
    # test_remove_order()
    # test_view_orders()
    # test_adjudicate()
    # test_rollback()
    # test_get_scoreboard()
    # test_edit()
    # test_coasts()
    # test_high_seas_and_sands()
    test_move_types()


def _setup():
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    manager = Manager()
    response = command.create_game(gm_context, manager)
    assert "error" not in response


def test_ping() -> None:
    context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    manager = Manager()
    response = command.ping(context, manager)
    # ping exists solely to check the bot can listen and respond
    assert "error" not in response


def test_order() -> None:
    # GM can order
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE, """F London - English_Channel""")
    manager = Manager()
    response = command.order(gm_context, manager)
    assert "error" not in response
    assert manager.get_board(_GUILD).get_province("London").unit.order

    # Player can order
    player_context = mock.context(_GUILD, "france-orders", "France", """A Paris - Ghent""")
    manager = Manager()
    response = command.order(player_context, manager)
    assert "error" not in response
    assert manager.get_board(_GUILD).get_province("Paris").unit.order


def test_remove_order() -> None:
    manager = Manager()

    # set phase to Winter, France requires disband
    gm_context = mock.context(
        _GUILD,
        _GM_CHANNEL,
        _GM_ROLE,
        "set_phase winter_builds" "\n" "set_province_owner Paris none",
    )
    starting_count = len(manager.get_board(_GUILD).get_player("France").centers)
    response = command.edit(gm_context, manager)
    assert "error" not in response
    assert len(manager.get_board(_GUILD).get_player("France").centers) == starting_count - 1

    # set order
    player_context = mock.context(_GUILD, "france-orders", "France", """disband Marseille""")
    response = command.order(player_context, manager)
    assert "error" not in response
    assert manager.get_board(_GUILD).get_player("France").build_orders

    # remove order
    player_context = mock.context(_GUILD, "france-orders", "France", """Marseille""")
    response = command.remove_order(player_context, manager)
    assert "error" not in response
    assert not manager.get_board(_GUILD).get_player("France").build_orders


def test_view_orders() -> None:
    manager = Manager()

    # remove orders because they might be in the database
    player_context = mock.context(
        _GUILD,
        "austria-orders",
        "Austria",
        "Prague\nVienna\nTrieste\nInnsbruck",
    )
    response = command.remove_order(player_context, manager)
    assert "error" not in response

    # nothing ordered yet
    player_context = mock.context(_GUILD, "austria-orders", "Austria")
    response = command.view_orders(player_context, manager)
    assert "error" not in response
    assert "Missing orders" in response
    assert "Submitted orders" not in response

    # order all
    player_context = mock.context(
        _GUILD,
        "austria-orders",
        "Austria",
        "Prague H\nVienna H\nTrieste H\nInnsbruck H",
    )
    response = command.order(player_context, manager)
    assert "error" not in response

    # none missing
    player_context = mock.context(_GUILD, "austria-orders", "Austria")
    response = command.view_orders(player_context, manager)
    assert "error" not in response
    assert "Missing orders" not in response
    assert "Submitted orders" in response


def test_adjudicate() -> None:
    # successive adjudication is tested later, this just test the command works
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    manager = Manager()
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response


def test_rollback() -> None:
    # TODO: (!) await rollback implemented
    pass


def test_get_scoreboard() -> None:
    # TODO: (!) await scoreboard fixed
    pass


def test_edit() -> None:
    # all edit commands
    gm_context = mock.context(
        _GUILD,
        _GM_CHANNEL,
        _GM_ROLE,
        "set_phase fall_retreats\n"
        "set_core Genoa France\n"
        "set_half_core Rome France\n"
        "set_province_owner Bremen France\n"
        "create_unit A France Hesse\n"
        "delete_unit Marseille\n"
        "move_unit Nantes Bay_of_Biscay",
    )
    manager = Manager()
    response = command.edit(gm_context, manager)
    assert "error" not in response
    board = manager.get_board(_GUILD)
    assert board.phase == fall_retreats
    assert board.get_province("Genoa").core == board.get_player("France")
    assert board.get_province("Rome").half_core == board.get_player("France")
    assert board.get_province("Bremen").owner == board.get_player("France")
    assert board.get_province("Hesse").unit.player == board.get_player("France")
    assert not board.get_province("Marseille").unit
    assert not board.get_province("Nantes").unit
    assert board.get_province("Bay of Biscay").unit.player == board.get_player("France")


def test_coasts() -> None:
    manager = Manager()
    board = manager.get_board(_GUILD)

    # move on to coast
    player_context = mock.context(_GUILD, "spain-orders", "Spain", "Panama - Honduras_nc")
    response = command.order(player_context, manager)
    assert "error" not in response

    # adjudicate to spring retreats
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response
    assert board.get_province("Honduras").unit.player == board.get_player("Spain")

    # adjudicate to fall moves
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response
    assert board.get_province("Honduras").unit.player == board.get_player("Spain")

    # sit on coast
    player_context = mock.context(_GUILD, "spain-orders", "Spain", "Honduras_nc H")
    response = command.order(player_context, manager)
    assert "error" not in response

    # adjudicate to fall retreats
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response
    assert board.get_province("Honduras").unit.player == board.get_player("Spain")

    # adjudicate to winter builds
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response
    assert board.get_province("Honduras").unit.player == board.get_player("Spain")

    # adjudicate to spring moves
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response
    assert board.get_province("Honduras").unit.player == board.get_player("Spain")

    # illegal order
    player_context = mock.context(_GUILD, "spain-orders", "Spain", "Honduras_nc - Yucatan_nc")
    response = command.order(player_context, manager)
    assert "error" not in response

    # adjudicate to spring retreats
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response
    assert board.get_province("Honduras").unit.player == board.get_player("Spain")


def test_high_seas_and_sands() -> None:
    # TODO: (!) high seas/sands primary/retreat unit coordinates do not exist (are in SVG). Don't return & test once fixed
    return

    manager = Manager()
    board = manager.get_board(_GUILD)

    # move to high sand
    player_context = mock.context(_GUILD, "mali-orders", "Mali", "Jenne - SAH3")
    response = command.order(player_context, manager)
    assert "error" not in response

    # adjudicate to spring retreats
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response
    assert board.get_province("SAH3").unit.player == board.get_player("Mali")

    # adjudicate to fall moves
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response
    assert board.get_province("SAH3").unit.player == board.get_player("Mali")

    # move off of high sand
    player_context = mock.context(_GUILD, "mali-orders", "Mali", "SAH3 - Kanem")
    response = command.order(player_context, manager)
    assert "error" not in response

    # adjudicate to fall retreats
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response
    assert board.get_province("Kanem").unit.player == board.get_player("Mali")


def test_move_types() -> None:
    manager = Manager()

    # all move phase orders except convoys
    gm_context = mock.context(
        _GUILD,
        _GM_CHANNEL,
        _GM_ROLE,
        "Nantes H\n"
        "Paris - Ghent\n"
        "Dijon - Marseille\n"
        "Marseille - Gulf_of_Lyon\n"
        "Amsterdam - Ghent\n"
        "Utrecht S Amsterdam - Ghent\n"
        "London cores\n"
        "Plymouth - English_Channel\n"
        "Krakow - Silesia",
    )
    response = command.order(gm_context, manager)
    assert "error" not in response

    # TODO: (!) pydip expects move to coast to say the coast on it, Amsterdam - Ghent does not do that (maybe we do it in moves but not in supports?)
    # TODO: (!) test the maps look right by breakpointing after each adjudication

    # adjudicate to spring retreats
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response

    # adjudicate to fall moves
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response

    # convoys and force retreats
    gm_context = mock.context(
        _GUILD,
        _GM_CHANNEL,
        _GM_ROLE,
        "A Marseille c- Barcelona\n"
        "F Gulf_of_Lyon C A Marseille - Barcelona\n"
        "Barcelona - Occitania\n"
        "English_Channel S Paris - Ghent\n"
        "Paris - Ghent\n"
        "Prague - Silesia\n"
        "Vienna S Prague - Silesia",
    )
    response = command.order(gm_context, manager)
    assert "error" not in response

    # adjudicate to fall retreats
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response

    # all retreat phase orders
    gm_context = mock.context(
        _GUILD,
        _GM_CHANNEL,
        _GM_ROLE,
        "Ghent boom\n" "Silesia - Saxony",
    )
    response = command.order(gm_context, manager)
    assert "error" not in response

    # adjudicate to winter builds
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response

    # all build phase orders
    player_context = mock.context(_GUILD, "france-orders", "France", "Build F Marseille")
    response = command.order(player_context, manager)
    assert "error" not in response
    player_context = mock.context(_GUILD, "spain-orders", "Spain", "Disband Madrid")
    response = command.order(player_context, manager)
    assert "error" not in response

    # adjudicate to spring moves
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response

    # newly built units move
    player_context = mock.context(_GUILD, "france-orders", "France", "F Marseille - Savoy")
    response = command.order(player_context, manager)
    assert "error" not in response

    # adjudicate to spring retreats
    gm_context = mock.context(_GUILD, _GM_CHANNEL, _GM_ROLE)
    response = command.adjudicate(gm_context, manager)
    assert "error" not in response


def run():
    test()
