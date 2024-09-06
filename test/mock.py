class Context:
    """Mock Discord context"""

    def __init__(self, guild: int, channel: str, role: str, content: str = ""):
        self.guild: _Guild = _Guild(guild)
        self.channel: _Channel = _Channel(channel)
        self.message: _Message = _Message(role, content)


class _Guild:
    """Mock Discord Context.Guild"""

    def __init__(self, id: int):
        self.id: int = id


class _Channel:
    """Mock Discord Context.Channel"""

    def __init__(self, name: str):
        self.name = name


class _Message:
    """Mock Discord Context.Message"""

    def __init__(self, role: str, content: str):
        self.author: _Author = _Author(role)
        self.content: str = content


class _Author:
    """Mock Discord Context.Message.Author"""

    def __init__(self, role: str):
        self.nick = "author nick"
        self.roles: list[_Role] = [_Role(role)]


class _Role:
    """Mock Discord Context.Message.Author.Role"""

    def __init__(self, name: str):
        self.name: str = name


def context(guild: int, channel: str, role: str, content: str = "") -> Context:
    return Context(guild, channel, role, content)
