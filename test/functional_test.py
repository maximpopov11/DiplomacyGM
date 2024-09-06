from bot import command
from diplomacy.persistence.manager import Manager
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

    test_ping()
    test_order()
    test_remove_order()
    test_view_orders()
    test_adjudicate()
    test_rollback()
    test_get_scoreboard()
    test_edit()
    test_create_game()
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
    # set phase to Winter, France requires disband
    gm_context = mock.context(
        _GUILD,
        _GM_CHANNEL,
        _GM_ROLE,
        "set_phase winter_builds" "\n" "set_province_owner Paris none",
    )
    manager = Manager()
    starting_count = len(manager.get_board(_GUILD).get_player("France").centers)
    response = command.edit(gm_context, manager)
    assert "error" not in response
    assert len(manager.get_board(_GUILD).get_player("France").centers) == starting_count - 1

    # set order
    player_context = mock.context(_GUILD, "france-orders", "france", """disband Marseille""")
    manager = Manager()
    response = command.order(player_context, manager)
    assert "error" not in response
    assert manager.get_board(_GUILD).get_player("France").build_orders

    # remove order
    player_context = mock.context(_GUILD, "france-orders", "france", """Marseille""")
    manager = Manager()
    response = command.remove_order(player_context, manager)
    assert "error" not in response
    assert not manager.get_board(_GUILD).get_player("France").build_orders


def test_view_orders() -> None:
    # TODO: (!)
    pass


def test_adjudicate() -> None:
    # TODO: (!)
    pass


def test_rollback() -> None:
    # TODO: (!)
    pass


def test_get_scoreboard() -> None:
    # TODO: (!)
    pass


def test_edit() -> None:
    # TODO: (!)
    pass


def test_create_game() -> None:
    # TODO: (!)
    pass


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
