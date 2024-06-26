import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
from youtubesearchpython import VideosSearch
import asyncio

bot = commands.Bot(command_prefix=['/', '.'],
                   activity=discord.Streaming(name=":3", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
                   intents=discord.Intents.all())


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = dict()
        self.is_paused = dict()
        self.queue = dict()
        self.vc = dict()
        self.ffmpeg_opt = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                           'options': '-vn'}
        self.ydl_opt = {'format': "bestaudio/best",
                        'source_address': '0.0.0.0',
                        'noplaylist': 'False',
                        'cookiefile': 'cookies.txt',
                        'ignoreerrors': True}
        self.ydl = YoutubeDL(self.ydl_opt)

    def search(self, req):
        if req.startswith(("https://", "http://")):
            title = self.ydl.extract_info(req, download=False)["title"]
            return {'source': req, 'title': title}
        search = VideosSearch(req, limit=1)
        if search.result()["result"]:
            return {'source': search.result()["result"][0]["link"], 'title': search.result()["result"][0]["title"]}
        else:
            return False

    async def parse_playlist(self, ctx, playlist):
        upload = await ctx.send("```♻️ Uploading a playlist...```")
        for track in self.ydl.extract_info(playlist, download=False)['entries']:
            if track:
                await self.play(ctx, track['webpage_url'], message=False)
        await upload.delete()

    async def play_next(self, ctx):
        if len(self.queue[ctx.guild.id]) > 0:
            self.is_playing[ctx.guild.id] = True
            # get the first url
            m_url = self.queue[ctx.guild.id][0][0]['source']

            # remove the first element as you are currently playing it
            self.queue[ctx.guild.id].pop(0)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ydl.extract_info(m_url, download=False))
            song = data['url']
            self.vc[ctx.guild.id].play(discord.FFmpegPCMAudio(song, executable="ffmpeg.exe", **self.ffmpeg_opt),
                                       after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx),
                                                                                        self.bot.loop))
        else:
            self.is_playing[ctx.guild.id] = False

    async def play_music(self, ctx):
        if len(self.queue[ctx.guild.id]) > 0:
            self.is_playing[ctx.guild.id] = True
            m_url = self.queue[ctx.guild.id][0][0]['source']
            # try to connect to voice channel if you are not already connected
            if self.vc.get(ctx.guild.id) is None or not self.vc.get(ctx.guild.id).is_connected():
                self.vc[ctx.guild.id] = await self.queue[ctx.guild.id][0][1].connect()
                # in case we fail to connect
                if self.vc.get(ctx.guild.id) is None:
                    await ctx.send("```Could not connect to the voice channel```")
                    return
            else:
                await self.vc[ctx.guild.id].move_to(self.queue[ctx.guild.id][0][1])  # 111
            # remove the first element as you are currently playing it
            self.queue[ctx.guild.id].pop(0)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ydl.extract_info(m_url, download=False))
            song = data['url']
            self.vc[ctx.guild.id].play(discord.FFmpegPCMAudio(song, executable="ffmpeg.exe", **self.ffmpeg_opt),
                                       after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx),
                                                                                        self.bot.loop))

        else:
            self.is_playing[ctx.guild.id] = False

    @bot.command(name="play", aliases=["p", "playing", "з", "здфн"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args, message=True):
        query = " ".join(args)
        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send("```❌ You are not in voice channel!```")
            return
        if self.is_paused.get(ctx.guild.id):
            await self.resume(ctx)
            await self.play(ctx, query)
        else:
            if "playlist" in query or ("album" in query and "track" not in query):  # playlist func
                """upload = await ctx.send("```♻️ Uploading a playlist...```")"""
                await self.parse_playlist(ctx, query)
                await ctx.send("```✅ Tracks from the playlist have loaded```")
                return
            song = self.search(query)
            if not song:
                await ctx.send("```❌ Incorrect format!```")
            else:
                if self.is_playing.get(ctx.guild.id):
                    self.queue[ctx.guild.id] += [[song, voice_channel]]
                    if message:
                        await ctx.send(f"**#{len(self.queue[ctx.guild.id])} '{song['title']}'** added to the queue")
                else:
                    self.queue[ctx.guild.id] = [[song, voice_channel]]
                    if message:
                        await ctx.send(f"**'{song['title']}'** added to the queue")
                if not self.is_playing.get(ctx.guild.id):
                    await self.play_music(ctx)

    @bot.command(name="pause", aliases=["зфгыу"], help="Pauses the current song being played")
    async def pause(self, ctx):
        if self.vc.get(ctx.guild.id).is_connected():
            if self.is_playing.get(ctx.guild.id):
                self.is_playing[ctx.guild.id] = False
                self.is_paused[ctx.guild.id] = True
                self.vc[ctx.guild.id].pause()
            elif self.is_paused.get(ctx.guild.id):
                self.is_playing[ctx.guild.id] = True
                self.is_paused[ctx.guild.id] = False
                self.vc[ctx.guild.id].resume()
            await ctx.send("```⏸️ Paused```")

    @bot.command(name="resume", aliases=["r", "куыгьу", "continue", "unpause"], help="Resumes playing")
    async def resume(self, ctx):
        if self.vc.get(ctx.guild.id).is_connected():
            if self.is_paused.get(ctx.guild.id):
                self.is_paused[ctx.guild.id] = False
                self.is_playing[ctx.guild.id] = True
                self.vc[ctx.guild.id].resume()
            await ctx.send("```▶️ Resumed```")

    @bot.command(name="skip", aliases=["s", "ылшз", "ы"], help="Skips the current song being played")
    async def skip(self, ctx):
        if self.vc.get(ctx.guild.id).is_connected():
            self.vc[ctx.guild.id].stop()
            # try to play next in the queue if it exists
            await self.play_music(ctx)
            await ctx.send("```⏭️ Skipped```")

    @bot.command(name="queue", aliases=["q", "й", "йгугу", "list", "дшые", "l", "д"],
                 help="Displays the current songs in queue")
    async def queue(self, ctx):
        if self.vc.get(ctx.guild.id).is_connected():
            retval = ""
            for i in range(0, len(self.queue[ctx.guild.id])):
                retval += f"{i + 1}. " + self.queue[ctx.guild.id][i][0]['title'] + "\n"

            if retval != "":
                await ctx.send(f"```queue:\n{retval}```")
            else:
                await ctx.send("```No music in queue```")

    @bot.command(name="remove", aliases=["re", "ку", "куьщму"], help="Removes song from queue")
    async def remove(self, ctx, position=0):
        if self.vc.get(ctx.guild.id).is_connected():
            if len(self.queue[ctx.guild.id]) == 0:
                await ctx.send("```❌ Queue is empty!```")
                return
            if not 0 <= position <= len(self.queue[ctx.guild.id]):
                await ctx.send("```❌ Incorrect number of song!```")
                return
            self.queue[ctx.guild.id].pop(position - 1)
            if position != 0:
                await ctx.send(f"```✅ Song #{position} removed```")
            else:
                await ctx.send("```✅ Last song removed```")

    @bot.command(name="clear", aliases=["c", "сдуфк"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        if self.vc.get(ctx.guild.id).is_connected():
            if not self.queue[ctx.guild.id]:
                await ctx.send("```✅ Queue is already empty```")
            else:
                self.queue[ctx.guild.id] = []
                await ctx.send("```✅ Queue cleared```")

    @bot.command(name="leave", aliases=["disconnect", "d", "дуфму"], help="Kick the bot from VC")
    async def leave(self, ctx):
        if self.vc.get(ctx.guild.id).is_connected():
            self.is_playing[ctx.guild.id] = False
            self.is_paused[ctx.guild.id] = False
            await self.clear(ctx)
            await ctx.send("```💔```")
            await self.vc[ctx.guild.id].disconnect()
