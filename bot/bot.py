import discord

from _token import DISCORD_TOKEN

client = discord.Client(intents=discord.Intents.default(), command_prefix='.', help_command=None)


@client.event
async def on_ready():
    print('Bot is ready!')


@client.event
async def on_message(message):
    channel = message.channel
    await channel.send('Beep Boop')


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)

# TODO: commands
#  .ping
#  .order
#  .view_orders
#  .adjudicate
#  .rollback
#  .help
