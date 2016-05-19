
import discord
from discord.ext import commands

import builtins
import datetime
import json
import subprocess

import keys
from modules import utilities
from utilities import checks
from client import client
from client import online_time

def setup(bot):
	bot.add_cog(Meta())

class Meta:
	
	'''
	@client.command(hidden = True)
	@checks.is_owner()
	async def eval(*code : str):
		await client.reply("\n```" + str(builtins.eval(" ".join(code))) + "```")
	
	@client.command(hidden = True)
	@checks.is_owner()
	async def exec(*code : str):
		builtins.exec(" ".join(code))
		await client.reply("Successfully executed.")
	'''
	
	@commands.command(hidden = True)
	async def libraryversion(self):
		await client.reply(discord.__version__)
	
	@commands.command(aliases = ["oauth"], hidden = True)
	async def invite(self):
		await client.reply(discord.utils.oauth_url(keys.bot_clientid))
	
	@commands.command(hidden = True)
	@checks.is_owner()
	async def servers(self):
		for server in client.servers:
			server_info = "```Name: " + server.name + "\n"
			server_info += "ID: " + server.id + "\n"
			server_info += "Owner: " + server.owner.name + "\n"
			server_info += "Server Region: " + str(server.region) + "\n"
			server_info += "Members: " + str(server.member_count) + "\n"
			server_info += "Created at: " + str(server.created_at) + "\n```"
			server_info += "Icon: " + server.icon_url
			await client.whisper(server_info)
	
	# Public Stats
	
	@commands.command()
	async def stats(self, *option : str):
		'''Bot stats'''
		if not option:
			with open("data/stats.json", "r") as stats_file:
				stats = json.load(stats_file)
			total_uptime = stats["uptime"]
			restarts = stats["restarts"]
			await client.reply("\nTotal Recorded Uptime: " + utilities.duration_to_letter_format(utilities.secs_to_duration(int(total_uptime))) + \
				"\nTotal Recorded Restarts: " + str(restarts))
		elif option[0] == "uptime": # since 4/17/16, fixed 5/10/16
			with open("data/stats.json", "r") as stats_file:
				stats = json.load(stats_file)
			total_uptime = stats["uptime"]
			await client.reply("Total Recorded Uptime: " + utilities.duration_to_letter_format(utilities.secs_to_duration(int(total_uptime))))
		elif option[0] == "restarts": # since 4/17/16, fixed 5/10/16
			with open("data/stats.json", "r") as stats_file:
				stats = json.load(stats_file)
			restarts = stats["restarts"]
			await client.reply("Total Recorded Restarts: " + str(restarts))
	
	@commands.command()
	async def uptime(self):
		'''Bot uptime'''
		now = datetime.datetime.utcnow()
		uptime = now - online_time
		await client.reply(utilities.duration_to_letter_format(utilities.secs_to_duration(int(uptime.total_seconds()))))
	
	# Update Bot Stuff
	
	@commands.command(pass_context = True, hidden = True)
	@checks.is_owner()
	async def changenickname(self, ctx, *nickname : str):
		await client.change_nickname(ctx.message.server.me, ' '.join(nickname))
	
	@commands.command(hidden = True)
	@checks.is_owner()
	async def updateavatar(self):
		with open("data/discord_harmonbot_icon.png", "rb") as avatar_file:
			await client.edit_profile(avatar = avatar_file.read())
		await client.reply("Avatar updated.")
	
	@commands.command(hidden = True)
	async def randomgame(self):
		await utilities.random_game_status()
		# await send_mention_space(message, "I changed to a random game status.")
	
	@commands.command(pass_context = True, aliases = ["updateplaying", "updategame", "changeplaying", "changegame", "setplaying"], hidden = True)
	@checks.is_owner()
	async def setgame(self, ctx, *game_name : str):
		updated_game = ctx.message.server.me.game
		if not updated_game:
			updated_game = discord.Game(name = " ".join(game_name))
		else:
			updated_game.name = " ".join(game_name)
		await client.change_status(game = updated_game)
		await client.reply("Game updated.")
	
	@commands.command(pass_context = True, hidden = True)
	@checks.is_owner()
	async def setstreaming(self, ctx, option : str, *url : str):
		if option == "on" or option == "true":
			if not url:
				await utilities.set_streaming_status()
				return
			else:
				updated_game = ctx.message.server.me.game
				if not updated_game:
					updated_game = discord.Game(url = url[0], type = 1)
				else:
					updated_game.url = url[0]
					updated_game.type = 1
		else:
			updated_game = ctx.message.server.me.game
			updated_game.type = 0
		await client.change_status(game = updated_game)
	
	@commands.command(pass_context = True, aliases = ["!clearplaying"], hidden = True)
	@checks.is_owner()
	async def cleargame(self, ctx):
		updated_game = ctx.message.server.me.game
		if updated_game and updated_game.name:
			updated_game.name = None
			await client.change_status(game = updated_game)
			await client.reply("Game status cleared.")
		else:
			await client.reply("There is no game status to clear.")
	
	@commands.command(pass_context = True, hidden = True)
	@checks.is_owner()
	async def clearstreaming(self, ctx, *option : str):
		updated_game = ctx.message.server.me.game
		if updated_game and (updated_game.url or updated_game.type):
			updated_game.url = None
			if option and option[0] == "url":
				await client.change_status(game = updated_game)
				await client.reply("Streaming url cleared.")
				return
			updated_game.type = 0
			await client.change_status(game = updated_game)
			await client.reply("Streaming status and url cleared.")
		else:
			await client.reply("There is no streaming status or url to clear.")
	
	# Restart/Shutdown
	
	@commands.command(pass_context = True, hidden = True)
	@checks.is_owner()
	async def restart(self, ctx):
		await client.say("Restarting...")
		with open("data/restart_channel.json", "x+") as restart_channel_file:
			json.dump({"restart_channel" : ctx.message.channel.id}, restart_channel_file)
		raise KeyboardInterrupt
	
	@commands.command(aliases = ["crash", "panic"], hidden = True)
	@checks.is_owner()
	async def shutdown(self):
		await client.say("Shutting down.")
		await utilities.shutdown_tasks()
		subprocess.call(["taskkill", "/f", "/im", "cmd.exe"])
		subprocess.call(["taskkill", "/f", "/im", "python.exe"])
	
	# Testing
	
	@commands.command(hidden = True)
	async def test(self):
		'''Basic test command'''
		await client.say("Hello, World!")
	
	@commands.command(pass_context = True, hidden = True)
	async def echo(self, ctx):
		'''Echoes the message'''
		await client.say(ctx.message.content)
	
	@commands.command(hidden = True)
	@checks.is_owner()
	async def deletetest(self):
		'''Sends 100 messages'''
		for i in range(1, 101):
			await client.say(str(i))
	
	@commands.command(hidden = True)
	@checks.is_owner()
	async def load(self):
		counter = 0
		bar = chr(9633) * 10
		loading_message = await client.say("Loading: [" + bar + "]")
		while counter <= 10:
			counter += 1
			bar = chr(9632) + bar[:-1] #9608
			await asyncio.sleep(1)
			await client.edit_message(loading_message, "Loading: [" + bar + "]")

