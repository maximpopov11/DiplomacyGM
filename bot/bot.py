import discord

from _token import DISCORD_TOKEN


# @client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        print(f'guild {guild.name}')


if __name__ == "__main__":
    print('ro')
    client = discord.Client()
    client.run(DISCORD_TOKEN)
