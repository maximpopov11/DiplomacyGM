import discord

from discord.ext import commands

from _token import DISCORD_TOKEN
from bot import orders

intent = discord.Intents.default()
intent.message_content = True
bot = discord.Client(intents=intent, command_prefix='.', help_command=None)


@bot.event
async def on_ready():
    print('Bot is ready!')


@commands.command
async def ping(ctx):
    await ctx.channel.send('Beep Boop')


@commands.command
async def order(ctx):
    response = orders.parse(ctx.message)
    await ctx.channel.send(response)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)

# TODO: test commands
# TODO: commands
#  .order
#  .view_orders
#  .adjudicate
#  .rollback
#  .scoreboard
#  .help
