import discord

from _token import DISCORD_TOKEN

client = discord.Client(intents=discord.Intents.default(), command_prefix='.', help_command=None)


@client.event
async def on_ready():
    print('Bot is ready!')


@client.event
async def on_message(message):
    author = message.author
    await client.send_message(message.channel, 'Welcome again {}!'.format(author))


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
