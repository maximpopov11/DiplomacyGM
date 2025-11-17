1.0.0
=====
First versioned release - though there has been many prior releases.

Released: 2025/11/16

Contributors to this release:
- Chloe
- a(dev)ahoughton

# Changelog and repository updates
- Repository moved to https://github.com/Imperial-Diplomacy/DiplomacyGM
- updated README.md with changelog, versioning and release information.
- added `Changelog.md`
- `dev` now acts as a staging branch where PRs should be opened to.


# Hellenic Diplomacy
HellaDip should be fully supported by the bot.
- Support for years before 1 A.D.
- New way of detecting units for Helladip, you now get some fleets.

# GM changes
These most likely won't be relevant to you unless you're a GM/Angel
- `.schedule` will now correctly ping you if an error occurs.

# New Superuser
Golden Kumquat is now a superuser, [per](https://discord.com/channels/1262215477237645314/1262215478072447019/1439753744072970460). Another one to stand up to the tyranny of DiploGM!

# Developer changes
These most likely won't be relevant to you unless you're a Developer and/or a Superuser.

**DEVELOPERS: you will need to create a `config.toml` and put your discord token in it. `.env` has been depreciated.**


## Development Cog
New Cog for developer commands
- `.su_dashboard command` dashboard for the bot - currently only shows loaded extensions and cogs.
- `extension_load`, `extension_unload` & `extension_reload` Can be used to reload extensions and their Cogs.
- `shutdown_the_bot_yes_i_want_to_do_this` command to shutdown the bot.

## Other changes
- Switch to `config.toml` instead of `.env`.
- A lot of hardcoded values have also been moved to `config.toml`.
- Supports logging levels of `CRITICAL` and `INFO` in config.
- Only Extensions in `config.toml` - extensions.load_on_startup are loaded on startup.
- terminology for admin's for the bot have been changed from "bot" to "superuser" to avoid confusion with community admins.
- scheduled commands are saved and deleted from disk instantly.
- commands scheduled in deleted channels are now automatically deleted.
- commands scheduled by users that can't be found are now not run and are deleted.
- scheduled commands now create an artificial Message to invoke a command instead of sending a message to create a new on. This lets superusers schedule superuser commands.
- scheduled commands have better error reporting.
- helladip didn't use the new or old system of unit detection. I didn't want to mess around with the svg so now it checks for what the unit is called in the svg.
- adding logging for SVG -> PNG conversion.
- deleted `_command.py`. Cogs are now stable.

