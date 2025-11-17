<img width="11047" height="4548" alt="ImpDip" src="https://github.com/user-attachments/assets/fb43ec57-d449-4dac-87ba-20560437076f" />

# DiplomacyGM

This project is designed to fully automate the adjudication of Diplomacy games over Discord. The step-by-step process to
use this bot will be outlined in the near future.

Current limitations:

- The only variant you may play at this time is Imperial Diplomacy. An interface for easily adding variants will be
  added in the near future.

If you find any bugs or inconsistencies or wish to see new features (for game-running work you would rather not do
yourself or rather not subject your players to), please message icecream_guy on Discord.

## Installation

### Prerequisites - 

- [python3.12 or newer](https://realpython.com/installing-python/)

- [Git](https://github.com/git-guides/install-git)

- [Pip package installer for Python](https://phoenixnap.com/kb/install-pip-windows)

You should use [virtual environments](https://docs.python.org/3/tutorial/venv.html) to manage python packages. 

To clone the repo and install dependencies, run the following on the Command Line (example commands are for Ubuntu 24.04) -

```bash
#Clone the bot locally
git clone https://github.com/Imperial-Diplomacy/DiplomacyGM.git
cd DiplomacyGM

#Create virtual environment
virtualenv venv -p=3.12 

#Start virtual environment
source venv/bin/activate

#This installs all the python dependencies the bot needs, only needed once.
pip install -r requirements.txt

#Copies 
cp .env.template .env
# Now edit .env and add the right inputs
```

### Running the bot

```bash
#Start virtual environment
source venv/bin/activate

#Run the bot
python main.py

#Stop virtual environment
deactivate
```

### Discord Game Setup

Use `.help` on your server to test the bot works. It also lists all the commands available.

GM commands such as `.create_game` can only be used if you have a "GM role". This is any role with the name "heavenly angel", "gm" etc (See [bot/config.py](/bot/config.py) for full list)

GM commands can also only be called in a channel named "admin-chat" in "gm channels" category.

Player commands can only be called in "orders" category in channels named "france-orders" etc.

# Changelog

When you make commits, add your changes to `Changelog.md`.

It is suggested to split into the following sections but use your own judgement:
- A section each set of major changes/features.
- Changes only affecting GMs
- Changes only affecting Developers and/or superusers
  - Most under the hood bugfixes and minor code changes should end up here


# Versioning

Versioning loosely follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Here's the brief overview:
```
Given a version number MAJOR.MINOR.PATCH, increment the:
1. MAJOR version when you make incompatible API changes
2. MINOR version when you add functionality in a backward compatible manner
3. PATCH version when you make backward compatible bug fixes
Additional labels for pre-release and build metadata are available as extensions to the MAJOR.MINOR.PATCH format.
```
For our purposes our API counts as our forward facing commands: any method to interact with our systems by non-superusers.

Please ensure version numbers are correct as the bot uses them

# Releasing a new version
To release a new version you must:
- Be a superuser.
- Have Github access.
- Have VPS access.

To release a new version:
1. Change the version in this file to be underlined with `=` signs and remove the `#` prefix. This is what the bot uses to detect released versions.
2. Ensure the dev branch has been suitably tested.
3. Create a PR to merge `dev` into `main`. (you can do this ahead of time).

    N.B. This will require approval from 2 contributors
4. Create a version tag with the semantic version eg `1.0.0` NOT `v1.0.0`
5. On the server use `cd /opt/DiplomacyGM` followed by `git fetch && git checkout <Version>` eg `git fetch && git checkout 1.0.0`
     
    N.B. This drops local changes to unstaged tracked files (Not the database or config.toml)
6. Run the bot command `.shutdown_the_bot_yes_i_want_to_do_this` to shutdown the bot 
7. On the server run `sudo systemctl restart DiploGM.service`
8. Monitor the Bot and ensure it restarts correctly.
9. Post the changelog into the [changelog channel](https://discord.com/channels/1262215477237645314/1439702852393111562) in the Developer Hub server. 

## HotFixes
On occasion, it may be required to push a change out faster than this process allows. If this is the case the version and changes should be documented after the fact. A full process for this is not currently documented.
