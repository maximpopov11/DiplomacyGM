import logging

import discord
from discord.ext import commands
from discord.utils import find as discord_find

from bot import perms
from bot.config import ERROR_COLOUR, IMPDIP_SERVER_ID
from bot.utils import send_message_and_file
from diplomacy.persistence.manager import Manager

logger = logging.getLogger(__name__)
manager = Manager()


class SpecView(discord.ui.View):
    def __init__(
        self,
        member: discord.Member,
        game_name: str,
        admin_channel: discord.TextChannel,
        channel_url: str,
        role: discord.Role,
        cspec_role: discord.Role,
    ):
        super().__init__(timeout=None)
        self.member = member
        self.game_name = game_name
        self.admin_channel = admin_channel
        self.url = channel_url
        self.power_role = role
        self.spec_role = cspec_role

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # check if player has country spectator role already (HAS NOT LEFT THE SERVER AFTER SPECTATING)
        if self.spec_role in self.member.roles:
            await interaction.response.send_message(
                f"{self.member.mention} is already spectating a player!", ephemeral=True
            )
            if interaction.message:
                await interaction.message.delete()

            return

        # check if db has a log of requesting player being accepted (HAS LEFT AND REJOINED THE SERVER AFTER SPECTATING)
        if manager.get_spec_request(interaction.guild.id, self.member.id):
            await interaction.response.send_message(
                f"{self.member.mention} has previously been accepted as a Spectator.",
                ephemeral=True,
            )
            if interaction.message:
                await interaction.message.delete()

            return

        try:
            await self.member.send(
                f"Response from: {self.game_name}\n"
                + f"You have been accepted as a spectator for: @{self.power_role.name}\n"
                + f"Go to {self.url} to watch them play!"
            )
            await interaction.response.send_message(
                f"Accept response sent to {self.member.mention}!", ephemeral=True
            )
        except:
            logger.warning(
                f"Unable to send a message to direct message. The user might have DMs blocked."
            )
        await self.member.add_roles(self.power_role, self.spec_role)

        out = f"[SPECTATOR LOG] {self.member.mention} approved for power {self.power_role.mention}"
        await self.admin_channel.send(out)

        # record acceptance to db and manager
        resp = manager.save_spec_request(
            interaction.guild.id, self.member.id, self.power_role.id
        )
        await self.admin_channel.send(
            f"[SPECTATOR LOG] for {self.member.mention}: {resp}"
        )

        if interaction.message:
            await interaction.message.delete()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.member.send(
                f"Response from: {self.game_name}\n"
                + f"You have been rejected as a spectator for: @{self.power_role.name}\n"
            )
            await interaction.response.send_message(
                f"Reject response sent to {self.member.mention}!", ephemeral=True
            )
        except:
            logger.warning(
                f"Unable to send a message to direct message. The user might have DMs blocked."
            )

        out = f"[SPECTATOR LOG] {self.member.mention} rejected for power {self.power_role.mention}"
        await self.admin_channel.send(out)

        if interaction.message:
            await interaction.message.delete()


class SpectatorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="spec",
        description="Specatate a Player",
    )
    async def spec(self, interaction: discord.Interaction, power_role: discord.Role):
        guild = interaction.guild
        if not guild:
            return

        if not self.bot.user:
            return

        # server ignore list
        if guild.id in [IMPDIP_SERVER_ID]:
            await interaction.response.send_message(
                "Can't request to spectate in the Hub server!", ephemeral=True
            )
            return

        # ignore if DM channel
        if isinstance(interaction.channel, discord.DMChannel):
            await interaction.response.send_message(
                "Please use the spectate command in a Game server!"
            )
            return
        elif not interaction.channel:
            return

        # check bot is on the gm team (for add_roles permissions)
        _member = guild.get_member(self.bot.user.id)
        if not _member:
            return

        _team = discord.utils.get(guild.roles, name="GM Team")
        _team_roles = [
            _team,
            discord.utils.get(guild.roles, name="GM"),
            discord.utils.get(guild.roles, name="Heavenly Angel"),
        ]
        _elle = discord.utils.get(guild.members, name="eelisha")

        if not any([_role in _member.roles for _role in _team_roles]):
            if _elle is not None:
                await interaction.response.send_message(
                    f"Bot is not on GM Team! Alerting {_team.mention} and {_elle.mention}!"
                )
            else:
                await interaction.response.send_message(
                    f"Bot is not on GM Team! Alerting {_team.mention}!"
                )

            return

        # check public square
        if interaction.channel.name != "the-public-square":
            channel = discord.utils.find(
                lambda c: c.name == "the-public-square", guild.text_channels
            )
            if channel:
                await interaction.response.send_message(
                    f"Can't request here! Go to the public square: {channel.mention}",
                    ephemeral=True,
                )

            return

        requester = guild.get_member(interaction.user.id)
        if not requester:
            return

        # check for membership and verification on the hub Server
        hub = self.bot.get_guild(IMPDIP_SERVER_ID)
        if not hub:
            return
        hub_requester = discord.utils.get(hub.members, name=interaction.user.name)
        if not hub_requester:
            await interaction.response.send_message(
                f"You are not a member of the Hub Server! Notifying {_team.mention}!"
            )
            return

        if not discord.utils.get(hub_requester.roles, name="ImpDip Verified"):
            await interaction.response.send_message(
                f"You are not verified on the Hub Server! Notifying {_team.mention}!"
            )
            return

        admin_channel = discord.utils.find(
            lambda c: c.name == "admin-chat", guild.text_channels
        )
        if not admin_channel:
            logger.warning(
                f"Server: {guild.name} does not have an #admin-chat channel."
            )
            await interaction.response.send_message(
                "Could not process your request. (Contact Admin)", ephemeral=True
            )
            return

        # CHECK IF USER HAS BEEN ACCEPTED IN THIS SERVER BEFORE
        prev_request = manager.get_spec_request(guild.id, interaction.user.id)
        if prev_request:
            prev_role = guild.get_role(prev_request.role_id)
            if prev_role:
                await admin_channel.send(
                    f"[SPECTATOR LOG] {interaction.user.mention} has requested to spectate {power_role.mention} after already being accepted for role: {prev_role.mention}"
                )

                await interaction.response.send_message(
                    "You have already been approved as a spectator in this server.",
                    ephemeral=True,
                )
            return

        # prevent spectating non-power roles
        if (
            power_role.name
            in [
                "Admin",
                "Moderators",
                "GM",
                "Heavenly Angel",
                "GM Team",
                "Player",
                "Spectator",
                "Country Spectator",
                "Dead",
                "DiploGM",
            ]
            or power_role.name.find("-orders") != -1
        ):
            await interaction.response.send_message(
                "Can't spectate that role!", ephemeral=True
            )
            return

        # get country spectator role
        cspec_role = discord.utils.find(
            lambda r: r.name == "Country Spectator", guild.roles
        )
        if not cspec_role:
            await interaction.response.send_message(
                "Could not find country spectator role! Contact GM."
            )
            return

        # if player already a player or country spec
        if any(
            map(
                lambda r: r.name
                in ["Player", "Spectator", "Country Spectator", "Dead"],
                requester.roles,
            )
        ):
            await interaction.response.send_message(
                "Can't request to spectate that power, you are either a Player or already a Spectator.",
                ephemeral=True,
            )

            return

        # get power channel to send request
        role_channel = discord.utils.find(
            lambda c: c.name == f"{power_role.name.lower()}-orders", guild.text_channels
        )
        role_void = discord.utils.find(
            lambda c: c.name == f"{power_role.name.lower()}-void", guild.text_channels
        )
        if not role_channel or not role_void:
            await interaction.response.send_message(
                "Please specify a playable power.", ephemeral=True
            )
            return

        out = f"[SPECTATOR LOG] {requester.mention} requested for power {power_role.mention}"
        await admin_channel.send(out)

        # send request message to player
        out = (
            f"{power_role.mention}: Spectator request from {interaction.user.mention}\n"
            + "- (if the buttons do not work, contact your GM)"
        )
        url = f"https://discord.com/channels/{guild.id}/{role_void.id}"  # link to void channel (for accept message)
        await role_channel.send(
            content=out,
            view=SpecView(
                requester, guild.name, admin_channel, url, power_role, cspec_role
            ),
        )

        # send ack to requesting user
        await interaction.response.send_message(
            "Spectator application sent! You should hear a response via DM.",
            ephemeral=True,
        )

    @commands.command(
        brief="Records the approval of a spec request",
        description="""[Only to be used by GMs]
        Used to record an approved spectator request if /spec fails.
        Usage: .record_spec @User @Nation""",
    )
    @perms.gm_only("record a spec")
    async def record_spec(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        if not guild:
            return

        if len(ctx.message.role_mentions) == 0:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Did not mention a nation.",
                embed_colour=ERROR_COLOUR,
            )
            return

        if len(ctx.message.mentions) == 0:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Did not mention a user.",
                embed_colour=ERROR_COLOUR,
            )
            return

        user = ctx.message.mentions[0]
        user_id = user.id

        power_role = ctx.message.role_mentions[0]
        power_id = power_role.id

        out = manager.save_spec_request(guild.id, user_id, power_id, override=True)
        await send_message_and_file(channel=ctx.channel, message=out)

    @commands.command(
        brief="Backlogs the approval for all current Country Spectators", hidden=True
    )
    @perms.gm_only("backlog spectators")
    async def backlog_specs(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        if not guild:
            return

        cspec = discord_find(lambda r: r.name == "Country Spectator", guild.roles)
        if cspec is None:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="There is no Country Spectator role in this server.",
            )
            return

        out = ""
        for member in guild.members:
            if cspec not in member.roles:
                continue

            power_role = None
            for role in member.roles:
                if discord_find(
                    lambda c: c.name == f"{role.name.lower()}-orders",
                    guild.text_channels,
                ):
                    power_role = role
                    break

            if power_role is None:
                continue

            result = manager.save_spec_request(guild.id, member.id, power_role.id)
            out += f"{member.mention} -> {power_role.mention}: {result}\n"

        await send_message_and_file(
            channel=ctx.channel, title="Spectator Backlog Results", message=out
        )


async def setup(bot):
    cog = SpectatorCog(bot)
    await bot.add_cog(cog)
