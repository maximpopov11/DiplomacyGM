# Discord roles which are allowed full access to bot commands
gm_roles: set[str] = {
    "Admin",
    "GM",
    "Heavenly Angel",
    "Emergency GM",
}

# Discord channels in which GMs are allowed to use non-public commands (ex. adjudication)
gm_channels: set[str] = {
    "admin-chat",
}

# Channel suffix for player orders channels.
# E.g. if the player is "france" and the suffix is "-orders", the channel is "france-orders"
player_channel_suffix: str = "-orders"
