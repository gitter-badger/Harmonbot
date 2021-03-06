
import discord
from discord.ext import commands

import inspect
import urllib

import credentials
from utilities import checks
from utilities import audio_player
from clients import aiohttp_session

def setup(bot):
	bot.add_cog(Audio(bot))

class Audio:
	
	def __init__(self, bot):
		self.bot = bot
		self.players = {}
		for name, command in inspect.getmembers(self):
			if isinstance(command, commands.Command) and command.parent is None and name != "audio":
				self.bot.add_command(command)
				self.audio.add_command(command)
	
	@commands.group(pass_context = True, aliases = ["yt", "youtube", "soundcloud", "voice", "stream", "play", "playlist", "spotify", "budio"], 
		invoke_without_command = True, no_pm = True)
	@checks.is_voice_connected()
	@checks.not_forbidden()
	async def audio(self, ctx, *, song : str = ""): #elif options[0] == "full":
		'''
		Audio System
		All audio subcommands are also commands
		Supported sites: https://rg3.github.io/youtube-dl/supportedsites.html and Spotify
		'''
		if not song:
			await self.bot.reply(":grey_question: What would you like to play?")
		elif "playlist" in song:
			await self.players[ctx.message.server.id].add_playlist(song, ctx.message.author)
		else:
			if "spotify" in song:
				song = await self.spotify_to_youtube(song)
				if not song:
					await self.bot.reply(":warning: Error")
					return
			response = await self.bot.reply(":cd: Loading..")
			try:
				title = await self.players[ctx.message.server.id].add_song(song, ctx.message.author)
			except Exception as e:
				try:
					await self.bot.edit_message(response, "{}: :warning: Error\n{}: {}".format(ctx.message.author.mention, type(e).__name__, e))
				except discord.errors.HTTPException:
					await self.bot.edit_message(response, "{}: :warning: Error".format(ctx.message.author.mention))
			else:
				await self.bot.edit_message(response, "{}: :ballot_box_with_check: `{}` has been added to the queue.".format(ctx.message.author.mention, title))
	
	@commands.command(aliases = ["summon"], pass_context = True, no_pm = True)
	@checks.is_permitted()
	async def join(self, ctx, *channel : str):
		'''Get me to join a voice channel'''
		if ctx.message.server.id not in self.players:
			self.players[ctx.message.server.id] = audio_player.AudioPlayer(self.bot, ctx.message.channel)
		await self.players[ctx.message.server.id].join_channel(ctx.message.author, channel)
		'''
		if ctx.message.server.id not in self.players or not ctx.message.server.voice_client:
			self.players[ctx.message.server.id] = audio_player.AudioPlayer(self.bot, ctx.message.channel)
			await self.players[ctx.message.server.id].join_channel(ctx.message.author, channel)
		elif checks.is_permitted_check(ctx):
			await self.players[ctx.message.server.id].join_channel(ctx.message.author, channel)
		else:
			await self.bot.reply(":no_entry: You don't have permission to move me")
		'''
	
	@commands.command(pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def leave(self, ctx):
		'''Tell me to leave the voice channel'''
		# await self.players[ctx.message.server.id].leave_channel()
		# del self.players[ctx.message.server.id]
		await self.bot.reply("The leave command is currently disabled right now, due to an issue/bug with Discord.")
	
	@commands.command(pass_context = True, aliases = ["stop"], no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def pause(self, ctx):
		'''Pause the current song'''
		paused = self.players[ctx.message.server.id].pause()
		if paused:
			await self.bot.say(":pause_button: Song paused")
		elif paused is False:
			await self.bot.reply(":no_entry: There is no song to pause")
		elif paused is None:
			await self.bot.reply(":no_entry: The song is already paused")
	
	@commands.command(pass_context = True, aliases = ["start"], no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def resume(self, ctx):
		'''Resume the current song'''
		resumed = self.players[ctx.message.server.id].resume()
		if resumed:
			await self.bot.say(":play_pause: Song resumed")
		elif resumed is False:
			await self.bot.reply(":no_entry: There is no song to resume")
		elif resumed is None:
			await self.bot.reply(":no_entry: The song is already playing")
	
	@commands.group(pass_context = True, aliases = ["next", "remove"], no_pm = True, invoke_without_command = True)
	@checks.not_forbidden()
	@checks.is_voice_connected()
	async def skip(self, ctx, *number : int):
		'''
		Skip a song
		Skip or vote to skip the current song or skip a song number in the queue
		The server owner and the person who requested the song can immediately skip the song and skip songs in the queue
		Otherwise, a majority vote of the people in the voice channel is required
		'''
		# implement override permission
		if ctx.message.author.id in (ctx.message.server.owner.id, credentials.myid) or checks.is_permitted_check(ctx):
			if number:
				song = await self.players[ctx.message.server.id].skip_specific(number[0])
				if song:
					await self.bot.say(":put_litter_in_its_place: Skipped #{} in the queue: `{}`".format(number[0], song["info"]["title"]))
					del song
				else:
					await self.bot.reply(":no_entry: There's not that many songs in the queue")
			elif self.players[ctx.message.server.id].skip():
				await self.bot.say(":next_track: Song skipped")
			else:
				await self.bot.reply(":no_entry: There is no song to skip")
		elif ctx.message.author in self.bot.voice_client_in(ctx.message.server).channel.voice_members:
			player = self.players[ctx.message.server.id]
			vote = player.vote_skip(ctx.message.author)
			if vote is False:
				await self.bot.reply(":no_entry: There is no song to skip")
			elif vote is None:
				await self.bot.reply(":no_entry: You've already voted to skip. Skips: {}/{}".format(len(player.skip_votes), player.skip_votes_required))
			elif vote is True:
				await self.bot.say(":next_track: Song skipped")
			else:
				await self.bot.reply(":white_check_mark: You voted to skip the current song. Skips: {}/{}".format(vote, player.skip_votes_required))
		else:
			await self.bot.reply(":no_entry: You're not even listening!")
	
	@skip.command(name = "to", pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def skip_to(self, ctx, number : int):
		'''
		Skip to a song in the queue
		Skips every song before number
		'''
		songs = await self.players[ctx.message.server.id].skip_to_song(number)
		if songs:
			await self.bot.say(":put_litter_in_its_place: Skipped to #{} in the queue".format(number))
			del songs
		else:
			await self.bot.reply(":no_entry: There's not that many songs in the queue")
	
	@commands.command(pass_context = True, aliases = ["repeat"], no_pm = True) # "restart"
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def replay(self, ctx):
		'''Repeat the current song'''
		response = await self.bot.reply(":repeat_one: Restarting song...")
		if (await self.players[ctx.message.server.id].replay()):
			await self.bot.edit_message(response, ctx.message.author.mention + ": :repeat_one: Restarted song")
		else:
			await self.bot.edit_message(response, ctx.message.author.mention + ": :no_entry: There is nothing to replay")
	
	@commands.command(pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def insert(self, ctx, position_number : int, *, song : str):
		'''Insert a song into the queue'''
		if "spotify" in song:
			song = await self.spotify_to_youtube(song)
			if not song:
				await self.bot.reply(":warning: Error")
				return
		response = await self.bot.reply(":cd: Loading..")
		try:
			title = await self.players[ctx.message.server.id].insert_song(song, ctx.message.author, position_number)
		except Exception as e:
			try:
				await self.bot.edit_message(response, "{}: :warning: Error\n{}: {}".format(ctx.message.author.mention, type(e).__name__, e))
			except discord.errors.HTTPException:
				await self.bot.edit_message(response, "{}: :warning: Error".format(ctx.message.author.mention))
		else:
			await self.bot.edit_message(response, "{}: :ballot_box_with_check: `{}` has been inserted into position #{} in the queue.".format(ctx.message.author.mention, title, position_number))
	
	@commands.command(pass_context = True, aliases = ["clear"], no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def empty(self, ctx):
		'''Empty the queue'''
		await self.players[ctx.message.server.id].empty_queue()
		await self.bot.say(":wastebasket: Queue emptied")
	
	@commands.command(pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def shuffle(self, ctx):
		'''Shuffle the queue'''
		response = await self.bot.reply(":twisted_rightwards_arrows: Shuffling...")
		await self.players[ctx.message.server.id].shuffle_queue()
		await self.bot.edit_message(response, ":twisted_rightwards_arrows: Songs shuffled")
	
	@commands.group(pass_context = True, no_pm = True, invoke_without_command = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def radio(self, ctx):
		'''
		Radio station based on the current song
		No input to turn on/off
		'''
		if self.players[ctx.message.server.id].radio_flag:
			self.players[ctx.message.server.id].radio_off()
			await self.bot.say(":stop_sign: Turned radio off")
		elif (await self.players[ctx.message.server.id].radio_on(ctx.message.author)) is False:
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@radio.command(name = "on", pass_context = True, aliases = ["start"], no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def radio_on(self, ctx):
		'''Turn radio on'''
		if self.players[ctx.message.server.id].radio_flag:
			await self.bot.reply(":no_entry: Radio is already on")
		elif (await self.players[ctx.message.server.id].radio_on(ctx.message.author)) is False:
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@radio.command(name = "off", pass_context = True, aliases = ["stop"], no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def radio_off(self, ctx):
		'''Turn radio off'''
		if self.players[ctx.message.server.id].radio_flag:
			self.players[ctx.message.server.id].radio_off()
			await self.bot.say(":stop_sign: Turned radio off")
		else:
			await self.bot.reply(":no_entry: Radio is already off")
	
	@commands.command(pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def settext(self, ctx):
		'''Set text channel for messages'''
		self.players[ctx.message.server.id].text_channel = ctx.message.channel
		await self.bot.say(":writing_hand::skin-tone-2: Text channel changed.")
	
	@commands.group(pass_context = True, no_pm = True, invoke_without_command = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def tts(self, ctx, *, message : str):
		'''Text to speech'''
		if not (await self.players[ctx.message.server.id].play_tts(message, ctx.message.author)):
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@tts.command(name = "options", pass_context = True, no_pm = True)
	@checks.not_forbidden()
	@checks.is_voice_connected()
	async def tts_options(self, ctx, amplitude: int, pitch: int, speed: int, word_gap: int, voice: str, *, message : str):
		'''
		Text to speech with options
		amplitude, pitch, speed, word_gap, voice
		defaults: 100, 50, 150, 0, en-us+f1 (input -1 for defaults)
		limits: 0-1000, 0-99, 80-9000, 0-1000, valid voice
		word_gap: length of pause between words, in units of 10 ms
		voice: see http://espeak.sourceforge.net/languages.html
		'''
		if amplitude == -1: amplitude = 100
		if pitch == -1: pitch = 50
		if speed == -1: speed = 150
		if word_gap == -1: word_gap = 0
		if voice == "-1": voice = "en-us+f1"
		if amplitude > 1000: amplitude = 1000
		if speed > 9000: speed = 9000
		if word_gap > 1000: word_gap = 1000
		if not (await self.players[ctx.message.server.id].play_tts(message, ctx.message.author, amplitude = amplitude, pitch = pitch, speed = speed, word_gap = word_gap, voice = voice)):
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@commands.command(pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def file(self, ctx, *, filename : str = ""):
		'''Play an audio file'''
		if not (await self.players[ctx.message.server.id].play_file(filename, ctx.message.author)):
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@commands.command(pass_context = True, no_pm = True)
	@checks.not_forbidden()
	@checks.is_voice_connected()
	async def files(self, ctx):
		'''List existing audio files'''
		await self.bot.reply(self.players[ctx.message.server.id].list_files())
	
	@commands.group(pass_context = True, no_pm = True, invoke_without_command = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def library(self, ctx):
		'''Start/stop playing songs from my library'''
		if self.players[ctx.message.server.id].library_flag:
			self.players[ctx.message.server.id].stop_library()
			await self.bot.say(":stop_sign: Stopped playing songs from my library")
		elif not (await self.players[ctx.message.server.id].play_library(ctx.message.author)):
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@library.command(name = "play", aliases = ["start"], pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def library_play(self, ctx):
		'''Start playing songs from my library'''
		if self.players[ctx.message.server.id].library_flag:
			await self.bot.reply(":no_entry: I'm already playing songs from my library")
		elif not (await self.players[ctx.message.server.id].play_library(ctx.message.author)):
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@library.command(name = "stop", pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def library_stop(self, ctx):
		'''Stop playing songs from my library'''
		if self.players[ctx.message.server.id].library_flag:
			self.players[ctx.message.server.id].stop_library()
			await self.bot.say(":stop_sign: Stopped playing songs from my library")
		else:
			await self.bot.reply(":no_entry: Not currently playing songs from my library")
	
	@library.command(name = "song", pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def library_song(self, ctx, *, filename : str = ""):
		'''Play a song from my library'''
		if not (await self.players[ctx.message.server.id].play_from_library(filename, ctx.message.author)):
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@library.command(name = "files", pass_context = True, no_pm = True) # enable for DMs?
	@checks.not_forbidden()
	@checks.is_voice_connected()
	async def library_files(self, ctx):
		'''List song files in the library'''
		if not ctx.message.channel.is_private:
			await self.bot.reply("Check your DMs.")
		output = "```"
		for filename in self.players[ctx.message.server.id].library_files:
			if len(output) + len(filename) > 1997: # 2000 - 3
				await self.bot.whisper(output[:-2] + "```")
				output = "```" + filename + ", "
			else:
				output += filename + ", "
	
	@library.command(name = "search", pass_context = True, no_pm = True)
	@checks.not_forbidden()
	@checks.is_voice_connected()
	async def library_search(self, ctx, *, search : str):
		'''Search songs in the library'''
		results = [filename for filename in self.players[ctx.message.server.id].library_files if search.lower() in filename.lower()]
		if not results:
			await self.bot.reply(":no_entry: No songs matching that search found")
			return
		try:
			await self.bot.reply("```\n{}\n```".format(", ".join(results)))
		except discord.errors.HTTPException:
			await self.bot.reply(":no_entry: Too many results. Try a more specific search.")
	
	@commands.group(pass_context = True, no_pm = True, invoke_without_command = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def volume(self, ctx, *, volume_setting : float = None):
		'''
		Change the volume of the current song
		volume_setting: 0 - 200
		'''
		if volume_setting is None:
			await self.bot.say(":sound: Current volume: {}".format(self.players[ctx.message.server.id].get_volume()))
		elif self.players[ctx.message.server.id].set_volume(volume_setting):
			if volume_setting > 200: volume_setting = 200.0
			elif volume_setting < 0: volume_setting = 0.0
			await self.bot.say(":sound: Volume set to {}".format(volume_setting))
		else:
			await self.bot.reply(":no_entry: There's nothing playing right now.")
	
	@volume.command(name = "default", pass_context = True, no_pm = True)
	@checks.is_permitted()
	@checks.is_voice_connected()
	async def volume_default(self, ctx, *, volume_setting : float = None):
		'''
		Change the default volume for the current player
		volume_setting: 0 - 200
		'''
		if volume_setting is None:
			await self.bot.say(":sound: Current default volume: {}".format(self.players[ctx.message.server.id].default_volume))
		else:
			if volume_setting > 200: volume_setting = 200.0
			elif volume_setting < 0: volume_setting = 0.0
			self.players[ctx.message.server.id].default_volume = volume_setting
			await self.bot.say(":sound: Default volume set to {}".format(volume_setting))
	
	@commands.group(pass_context = True, aliases = ["current"], no_pm = True, invoke_without_command = True)
	@checks.is_voice_connected()
	@checks.not_forbidden()
	async def playing(self, ctx):
		'''See the currently playing song'''
		await self.bot.say(self.players[ctx.message.server.id].current_output())
	
	@commands.command(pass_context = True, no_pm = True)
	@checks.is_voice_connected()
	@checks.not_forbidden()
	async def queue(self, ctx):
		'''See the current queue'''
		await self.bot.say(self.players[ctx.message.server.id].queue_output())
	
	# Voice Input
	
	@commands.group(pass_context = True, invoke_without_command = True, hidden = True)
	@checks.is_voice_connected()
	@checks.is_permitted()
	async def listen(self, ctx):
		if self.players[ctx.message.server.id].listener:
			await self.players[ctx.message.server.id].stop_listening()
		elif not (await self.players[ctx.message.server.id].start_listening()):
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@listen.command(name = "start", aliases = ["on"], pass_context = True)
	@checks.is_voice_connected()
	@checks.is_permitted()
	async def listen_start(self, ctx):
		if self.players[ctx.message.server.id].listener:
			await self.bot.reply(":no_entry: I'm already listening")
		elif not (await self.players[ctx.message.server.id].start_listening()):
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@listen.command(name = "stop", aliases = ["off"], pass_context = True)
	@checks.is_voice_connected()
	@checks.is_permitted()
	async def listen_stop(self, ctx):
		if self.players[ctx.message.server.id].listener:
			await self.players[ctx.message.server.id].stop_listening()
		else:
			await self.bot.reply(":no_entry: I'm not listening")
	
	@listen.command(name = "once", pass_context = True)
	@checks.is_voice_connected()
	@checks.is_permitted()
	async def listen_once(self, ctx):
		if self.players[ctx.message.server.id].listener:
			await self.bot.reply(":no_entry: I'm already listening")
		elif (await self.players[ctx.message.server.id].listen_once()) is False:
			await self.bot.reply(":warning: Something else is already playing. Please stop it first.")
	
	@listen.command(name = "finish", pass_context = True)
	@checks.is_voice_connected()
	@checks.is_permitted()
	async def listen_finish(self, ctx):
		if self.players[ctx.message.server.id].listener:
			await self.players[ctx.message.server.id].finish_listening()
		else:
			await self.bot.reply(":no_entry: I'm not listening")
	
	@listen.command(name = "process", pass_context = True)
	@checks.is_voice_connected()
	@checks.is_permitted()
	async def listen_process(self, ctx):
		await self.players[ctx.message.server.id].process_listen()
	
	# Utility

	async def spotify_to_youtube(self, link):
		path = urllib.parse.urlparse(link).path
		if path[:7] == "/track/":
			url = "https://api.spotify.com/v1/tracks/{}".format(path[7:])
			async with aiohttp_session.get(url) as resp:
				data = await resp.json()
			if "name" in data:
				songname = "+".join(data["name"].split())
			else:
				return False
			artistname = "+".join(data["artists"][0]["name"].split())
			url = "https://www.googleapis.com/youtube/v3/search?part=snippet&q={}+by+{}&key={}".format(songname, artistname, credentials.google_apikey)
			async with aiohttp_session.get(url) as resp:
				data = await resp.json()
			data = data["items"][0]
			if "videoId" not in data["id"]:
				async with aiohttp_session.get(url) as resp:
					data = await resp.json()
				data = data["items"][1]
			link = "https://www.youtube.com/watch?v=" + data["id"]["videoId"]
			return link
		else:
			return False
	
	# Termination
	
	def cancel_all_tasks(self):
		for player in self.players.values():
			player.player.cancel()
	
	def save_voice_channels(self):
		voice_channels = [[voice_client.channel.id, self.players[voice_client.server.id].text_channel.id] for voice_client in self.bot.voice_clients]
		return voice_channels

