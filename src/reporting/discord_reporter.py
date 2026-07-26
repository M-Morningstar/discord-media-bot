from __future__ import annotations

import datetime

import discord


class DiscordReporter:
    """Builds and sends Discord embeds for Radarr/Sonarr results."""

    SUCCESS_COLOR = 0x57F287
    ALREADY_EXISTS_COLOR = 0xFEE75C
    ERROR_COLOR = 0xED4245
    STARTUP_COLOR = 0x5865F2

    _TRUNCATE_OVERVIEW = 200

    async def send_success(
        self,
        message: discord.Message,
        *,
        title: str,
        imdb_id: str,
        media_type: str,
        year: int | None = None,
        poster_url: str | None = None,
        overview: str | None = None,
    ) -> None:
        """Send a green success embed after media was added.

        Args:
            message: The user's original Discord message to reply to.
            title: The media title from the lookup result.
            imdb_id: The IMDB ID that was requested.
            media_type: ``"movie"`` or ``"series"`` for the embed copy.
            year: Release year, if available from lookup.
            poster_url: Remote poster URL, shown as thumbnail.
            overview: Plot summary, truncated to 200 chars.
        """
        embed = discord.Embed(
            title=title,
            color=self.SUCCESS_COLOR,
            timestamp=datetime.datetime.now(datetime.UTC),
        )

        status_text = "Added ✓"
        if year is not None:
            status_text = f"{status_text} ({year})"
        embed.add_field(name="Status", value=status_text, inline=True)

        if overview:
            truncated = (
                overview[: self._TRUNCATE_OVERVIEW] + "..."
                if len(overview) > self._TRUNCATE_OVERVIEW
                else overview
            )
            embed.description = truncated

        if poster_url:
            embed.set_thumbnail(url=poster_url)

        embed.set_footer(
            text=f"{media_type} . {imdb_id}",
        )

        await message.channel.send(embed=embed)

    async def send_already_exists(
        self,
        message: discord.Message,
        *,
        title: str,
        imdb_id: str,
        media_type: str,
    ) -> None:
        """Send a yellow embed when media is already in the library.

        Args:
            message: The user's original Discord message to reply to.
            title: The media title.
            imdb_id: The IMDB ID that was requested.
            media_type: ``"movie"`` or ``"series"``.
        """
        embed = discord.Embed(
            description=f"**{title}** is already in your {media_type} library.",
            color=self.ALREADY_EXISTS_COLOR,
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        embed.set_footer(text=f"{media_type} . {imdb_id}")
        await message.channel.send(embed=embed)

    async def send_not_found(
        self,
        message: discord.Message,
        *,
        imdb_id: str,
        media_type: str,
    ) -> None:
        """Send a red embed when no media is found for the IMDB ID.

        Args:
            message: The user's original Discord message to reply to.
            imdb_id: The IMDB ID that was requested.
            media_type: ``"movie"`` or ``"series"``.
        """
        embed = discord.Embed(
            description=(
                f"No {media_type} was found for `{imdb_id}`. \n\n"
                "Check the IMDB ID or try searching manually in "
                f"{'Radarr' if media_type == 'movie' else 'Sonarr'}."
            ),
            color=self.ERROR_COLOR,
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        embed.set_footer(text=f"{media_type} . {imdb_id}")
        await message.channel.send(embed=embed)

    async def send_validation_error(
        self,
        message: discord.Message,
        *,
        reason: str,
    ) -> None:
        """Send a red embed explaining why the message was rejected.

        Args:
            message: The user's original Discord message to reply to.
            reason: One of ``"empty"``, ``"no_id"``, or ``"multiple_ids"``.
        """
        descriptions = {
            "empty": "Your message doesn't contain any text.",
            "no_id": "No IMDB ID found in your message.",
            "multiple_ids": "Please post only one IMDB ID per message.",
        }
        description = descriptions.get(reason, descriptions["no_id"])

        embed = discord.Embed(
            description=(
                f"{description} \n\nPost an IMDB ID like `tt1234567` to add a movie or series."
            ),
            color=self.ERROR_COLOR,
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        await message.channel.send(embed=embed)

    async def send_startup_message(self, channel: discord.TextChannel) -> None:
        """Send a blue embed when the bot comes online in a configured channel.

        Args:
            channel: The Discord text channel to send the message to.
        """
        embed = discord.Embed(
            title="Media Bot Online",
            description=(
                "Listening for IMDB IDs in this channel.\n\n"
                "Post an IMDB ID like 'tt1234567' to add a movie or series."
            ),
            color=self.STARTUP_COLOR,
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        await channel.send(embed=embed)


__all__ = ["DiscordReporter"]
