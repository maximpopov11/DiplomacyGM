import logging
import random
import time
from diplomacy.persistence.manager import Manager
from scipy.integrate import odeint

from discord.ext import commands

from bot import perms
from bot.config import ERROR_COLOUR, is_bumble, temporary_bumbles
from bot.utils import fish_pop_model, log_command, send_message_and_file

from diplomacy.persistence.db.database import get_connection

logger = logging.getLogger(__name__)
manager = Manager()

ping_text_choices = [
    "proudly states",
    "fervently believes in the power of",
    "is being mind controlled by",
]

# Fetch the 115 philosophical advice points created by Hobbit for the World of Chaos event
# Intended use: to extend the possibilities within .advice
WOC_ADVICE = ["Maybe the real friends were the dots we claimed along the way."]
try:
    with open("bot/assets/advice.txt", "r") as f:
        WOC_ADVICE.extend(f.readlines())
except FileNotFoundError:
    pass


class PartyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @perms.gm_only("botsay")
    async def botsay(self, ctx: commands.Context) -> None:
        # noinspection PyTypeChecker
        if len(ctx.message.channel_mentions) == 0:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="No Channel Given",
                embed_colour=ERROR_COLOUR,
            )
            return
        channel = ctx.message.channel_mentions[0]
        content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        content = content.replace(channel.mention, "").strip()
        if len(content) == 0:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="No Message Given",
                embed_colour=ERROR_COLOUR,
            )
            return

        message = await send_message_and_file(channel=channel, message=content)
        log_command(logger, ctx, f"Sent Message into #{channel.name}")
        await send_message_and_file(
            channel=ctx.channel,
            title=f"Sent Message",
            message=message.jump_url,
        )

    @commands.command(help="Checks bot listens and responds.")
    async def ping(self, ctx: commands.Context):
        response = "Beep Boop"
        if random.random() < 0.1:
            author = ctx.message.author
            content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
            if content == "":
                content = " nothing"
            name = author.nick
            if not name:
                name = author.name
            response = name + " " + random.choice(ping_text_choices) + content
        await send_message_and_file(channel=ctx.channel, title=response)

    @commands.command(hidden=True)
    async def bumble(self, ctx: commands.Context) -> None:
        list_of_bumble = list("bumble")
        random.shuffle(list_of_bumble)
        word_of_bumble = "".join(list_of_bumble)

        if is_bumble(ctx.author.name) and random.randrange(0, 10) == 0:
            word_of_bumble = "bumble"

        if word_of_bumble == "bumble":
            word_of_bumble = "You are the chosen bumble"

            if ctx.author.name not in temporary_bumbles:
                # no keeping temporary bumbleship easily
                temporary_bumbles.add(ctx.author.name)
        if word_of_bumble == "elbmub":
            word_of_bumble = "elbmub nesohc eht era uoY"

        board = manager.get_board(ctx.guild.id)
        board.fish -= 1
        await send_message_and_file(channel=ctx.channel, title=word_of_bumble)

    @commands.command(hidden=True)
    async def pelican(self, ctx: commands.Context) -> None:
        pelican_places = {
            "your home": 15,
            "a kebab store": 12,
            "a jungle": 10,
            "a cursed IKEA": 10,
            "a supermarket": 9,
            "Formosa": 8,
            "the Vatican at night": 7,
            "your dreams": 5,
            "a german bureaucracy office": 5,
            "a karaoke bar in Tokyo": 5,
            "a quantum physics lecture": 4,
            "your own mind": 3,
            "Area 51": 2,
            "the Teletubbies’ homeland": 0.9,
            "Summoners’ Rift": 0.1,
        }
        chosen_place = random.choices(
            list(pelican_places.keys()), weights=list(pelican_places.values()), k=1
        )[0]
        message = f"A pelican is chasing you through {chosen_place}!"
        await send_message_and_file(channel=ctx.channel, title=message)

    @commands.command(hidden=True)
    async def cheat(self, ctx: commands.Context) -> None:
        message = "Cheating is disabled for this user."
        author = ctx.message.author.name
        board = manager.get_board(ctx.guild.id)
        if is_bumble(author):
            sample = random.choice(
                [
                    f"It looks like {author} is getting coalitioned this turn :cry:",
                    f"{author} is talking about stabbing {random.choice(list(board.players)).name} again",
                    f"looks like he's throwing to {author}... shame",
                    "yeah",
                    "People in this game are not voiding enough",
                    f"I can't believe {author} is moving to {random.choice(list(board.provinces)).name}",
                    f"{author} has a bunch of invalid orders",
                    f"No one noticed that {author} overbuilt?",
                    f"{random.choice(list(board.players)).name} is in a perfect position to stab {author}",
                    ".bumble",
                ]
            )
            message = f'Here\'s a helpful message I stole from the spectator chat: \n"{sample}"'
        await send_message_and_file(channel=ctx.channel, title=message)

    @commands.command(hidden=True)
    async def phish(self, ctx: commands.Context) -> None:
        await ctx.message.add_reaction("🐟")

        message = "No! Phishing is bad!"
        if is_bumble(ctx.author.name):
            message = "Please provide your firstborn pet and your soul for a chance at winning your next game!"
        await send_message_and_file(channel=ctx.channel, title=message)

    @commands.command(hidden=True)
    async def advice(self, ctx: commands.Context) -> None:
        message = "You are not worthy of advice."
        chance = random.randrange(0, 5)

        if is_bumble(ctx.author.name):
            message = "Bumble suggests that you go fishing, although typically blasphemous, today is your lucky day!"
        elif chance == 0:
            message = random.choice(
                [
                    "Bumble was surprised you asked him for advice and wasn't ready to give you any, maybe if you were a true follower...",
                    "Icecream demands that you void more and will not be giving any advice until sated.",
                    "Salt suggests that stabbing all of your neighbors is a good play in this particular situation.",
                    "Ezio points you to an ancient proverb: see dot take dot.",
                    "CaptainMeme advises balance of power play at this instance.",
                    "Ash Lael deems you a sufficiently apt liar, go use those skills!",
                    "Kwiksand suggests winning.",
                    "Ambrosius advises taking the opportunity you've been considering, for more will ensue.",
                    "The GMs suggest you input your orders so they don't need to hound you for them at the deadline.",
                ]
            )
        elif chance == 1:
            index = random.randrange(0, len(WOC_ADVICE))
            message = f"{index}. {WOC_ADVICE[index]}"

        await send_message_and_file(channel=ctx.channel, title=message)

    @commands.command(hidden=True)
    async def fish(self, ctx: commands.Context) -> None:
        await ctx.message.add_reaction("🐟")

        board = manager.get_board(ctx.guild.id)
        fish_num = random.randrange(0, 20)

        # overfishing model
        # https://www.maths.gla.ac.uk/~nah/2J/ch1.pdf
        # figure 1.9
        growth_rate = 0.001
        carrying_capacity = 1000
        args = (growth_rate, carrying_capacity)

        time_now = time.time()
        delta_t = time_now - board.fish_pop["time"]

        board.fish_pop["time"] = time_now
        board.fish_pop["fish_pop"] = odeint(
            fish_pop_model, board.fish_pop["fish_pop"], [0, delta_t], args=args
        )[1]

        if board.fish_pop["fish_pop"] <= 200:
            fish_num += 5
        if board.fish_pop["fish_pop"] <= 50:
            fish_num += 20

        debumblify = False
        if is_bumble(ctx.author.name) and random.randrange(0, 10) == 0:
            # Bumbles are good fishers
            if fish_num == 1:
                fish_num = 0
            elif fish_num > 15:
                fish_num -= 5

        if 0 == fish_num:
            # something special
            rare_fish_options = [
                ":dolphin:",
                ":shark:",
                ":duck:",
                ":goose:",
                ":dodo:",
                ":flamingo:",
                ":penguin:",
                ":unicorn:",
                ":swan:",
                ":whale:",
                ":seal:",
                ":sheep:",
                ":sloth:",
                ":hippopotamus:",
            ]
            board.fish += 10
            board.fish_pop["fish_pop"] -= 10
            fish_message = f"**Caught a rare fish!** {random.choice(rare_fish_options)}"
        elif fish_num < 16:
            fish_num = (fish_num + 1) // 2
            board.fish += fish_num
            board.fish_pop["fish_pop"] -= fish_num
            fish_emoji_options = [
                ":fish:",
                ":tropical_fish:",
                ":blowfish:",
                ":jellyfish:",
                ":shrimp:",
            ]
            fish_weights = [8, 4, 2, 1, 2]
            fish_message = f"Caught {fish_num} fish! " + " ".join(
                random.choices(fish_emoji_options, weights=fish_weights, k=fish_num)
            )
        elif fish_num < 21:
            fish_num = (21 - fish_num) // 2

            if is_bumble(ctx.author.name):
                if random.randrange(0, 20) == 0:
                    # Sometimes Bumbles are so bad at fishing they debumblify
                    debumblify = True
                    fish_num = random.randrange(10, 20)
                    return
                else:
                    # Bumbles that lose fish lose a lot of them
                    fish_num *= random.randrange(3, 10)

            board.fish -= fish_num
            board.fish_pop["fish_pop"] += fish_num
            fish_kind = "captured" if board.fish >= 0 else "future"
            fish_message = f"Accidentally let {fish_num} {fish_kind} fish sneak away :("
        else:
            fish_message = f"You find nothing but barren water and overfished seas, maybe let the population recover?"
        fish_message += f"\nIn total, {board.fish} fish have been caught!"
        if random.randrange(0, 5) == 0:
            get_connection().execute_arbitrary_sql(
                """UPDATE boards SET fish=? WHERE board_id=? AND phase=?""",
                (board.fish, board.board_id, board.get_phase_and_year_string()),
            )

        if debumblify:
            temporary_bumbles.remove(ctx.author.name)
            fish_message = f"\n Your luck has run out! {fish_message}\nBumble is sad, you must once again prove your worth by Bumbling!"

        await send_message_and_file(channel=ctx.channel, title=fish_message)

    @commands.command(brief="Show global fishing leaderboard")
    async def global_leaderboard(self, ctx: commands.Context) -> None:
        sorted_boards = sorted(
            manager._boards.items(), key=lambda board: board[1].fish, reverse=True
        )
        raw_boards = tuple(map(lambda b: b[1], sorted_boards))
        try:
            this_board = manager.get_board(ctx.guild.id)
        except Exception:
            this_board = None
        sorted_boards = sorted_boards[:9]
        text = ""
        if this_board is not None:
            index = str(raw_boards.index(this_board) + 1)
        else:
            index = "NaN"

        max_fishes = len(str(sorted_boards[0][1].fish))

        for i, board in enumerate(sorted_boards):
            bold = "**" if this_board == board[1] else ""
            guild = ctx.bot.get_guild(board[0])
            if guild:
                text += f"\\#{i + 1: >{len(index)}} | {board[1].fish: <{max_fishes}} | {bold}{guild.name}{bold}\n"
        if this_board is not None and this_board not in raw_boards[:9]:
            text += (
                f"\n\\#{index} | {this_board.fish: <{max_fishes}} | {ctx.guild.name}"
            )

        await send_message_and_file(
            channel=ctx.channel, title="Global Fishing Leaderboard", message=text
        )


async def setup(bot):
    cog = PartyCog(bot)
    await bot.add_cog(cog)
