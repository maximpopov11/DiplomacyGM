# Archived
This repo is archived in favor of https://github.com/Imperial-Diplomacy/DiplomacyGM which continues this work under the official ImperialDiplomacy organization.

### Sample Map Generation Output

<img width="11047" height="4548" alt="ImpDip" src="https://github.com/user-attachments/assets/fb43ec57-d449-4dac-87ba-20560437076f" />

### DiplomacyGM

This project is designed to fully automate the adjudication of Diplomacy games over Discord. The step-by-step process to
use this bot will be outlined in the near future.

Current limitations:

- The only variant you may play at this time is Imperial Diplomacy. An interface for easily adding variants will be
  added in the near future.

If you find any bugs or inconsistencies or wish to see new features (for game-running work you would rather not do
yourself or rather not subject your players to), please message icecream_guy on Discord.

### Prerequisites - 

- [python3.12 or newer](https://realpython.com/installing-python/)

- [Git](https://github.com/git-guides/install-git)

- [Pip package installer for Python](https://phoenixnap.com/kb/install-pip-windows)

### Installation

You should use [virtual environments](https://docs.python.org/3/tutorial/venv.html) to manage python packages. 

To clone the repo and install dependencies, run the following on the Command Line (example commands are for Ubuntu 24.04) -

```bash
#Clone the bot locally
git clone https://github.com/maximpopov11/DiplomacyGM.git
cd DiplomacyGM

#Create virtual environment
virtualenv venv -p=3.12 

#Start virtual environment
source venv/bin/activate

#This installs all the python dependancies the bot needs, only needed once.
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
