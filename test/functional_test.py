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
    test_edit()
    test_coasts()
    test_high_seas_and_sands()
    test_pre_core_builds()
    test_successive_adjudication()
    test_move_types()
    test_illegal_orders()


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
    # TODO: (!)
    pass


def test_high_seas_and_sands() -> None:
    # TODO: (!)
    pass


def test_pre_core_builds() -> None:
    # TODO: (!)
    pass


def test_successive_adjudication() -> None:
    # TODO: (!)
    pass


def test_move_types() -> None:
    # TODO: (!)
    pass


def test_illegal_orders() -> None:
    # TODO: (!)
    pass


def run():
    test()
