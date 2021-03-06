
import discord
from discord.ext import commands

import collections
import copy
import inspect
import json
import random

import clients
import credentials
from utilities import checks
from modules.maze import maze

def setup(bot):
	bot.add_cog(Reactions(bot))

class Reactions:
	
	def __init__(self, bot):
		self.bot = bot
		self.reaction_messages = {}
		self.mazes = {}
		
		self.numbers = {'\N{KEYCAP TEN}': 10}
		for number in range(9):
			self.numbers[chr(ord('\u0031') + number) + '\N{COMBINING ENCLOSING KEYCAP}'] = number + 1 # '\u0031' - 1
		
		self.arrows = collections.OrderedDict([('\N{LEFTWARDS BLACK ARROW}', 'W'), ('\N{UPWARDS BLACK ARROW}', 'N'), ('\N{DOWNWARDS BLACK ARROW}', 'S'), ('\N{BLACK RIGHTWARDS ARROW}', 'E')]) # tuple?
		
		self.reaction_commands = ((self.guessr, self.bot.cogs["Games"].guess), (self.newsr, self.bot.cogs["Resources"].news), (self.mazer, self.bot.cogs["Games"].maze))
		for command, parent in self.reaction_commands:
			subcommand = copy.copy(command)
			subcommand.name = "reactions"
			subcommand.aliases = ["reaction", 'r']
			async def wrapper(ctx, *args, **kwargs):
				await command.callback(self, ctx, *args, **kwargs)
			subcommand.callback = wrapper
			subcommand.params = inspect.signature(subcommand.callback).parameters.copy()
			parent.add_command(subcommand)
	
	def __del__(self):
		for command, parent in self.reaction_commands:
			parent.remove_command("reactions")
	
	@commands.command(aliases = ["guessreactions", "guessreaction"], pass_context = True)
	@checks.not_forbidden()
	async def guessr(self, ctx):
		'''
		Guessing game
		With reactions
		'''
		guess_message, embed = await self.bot.embed_reply("Guess a number between 1 to 10")
		answer = random.randint(1, 10)
		for number_emote in sorted(self.numbers.keys()):
			await self.bot.add_reaction(guess_message, number_emote)
		self.reaction_messages[guess_message.id] = lambda reaction, user: self.guessr_processr(ctx.message.author, answer, embed, reaction, user)
	
	async def guessr_processr(self, player, answer, embed, reaction, user):
		if user == player and reaction.emoji in self.numbers:
			if self.numbers[reaction.emoji] == answer:
				embed.description = "{}: It was {}!".format(player.display_name, self.numbers[reaction.emoji])
				await self.bot.edit_message(reaction.message, embed = embed)
				del self.reaction_messages[reaction.message.id]
			else:
				embed.description = "{}: Guess a number between 1 to 10. No, it's not {}".format(player.display_name, self.numbers[reaction.emoji])
				await self.bot.edit_message(reaction.message, embed = embed)
	
	@commands.command(pass_context = True, invoke_without_command = True)
	@checks.not_forbidden()
	async def newsr(self, ctx, source : str):
		'''
		News
		With Reactions
		Powered by NewsAPI.org
		'''
		async with clients.aiohttp_session.get("https://newsapi.org/v1/articles?source={}&apiKey={}".format(source, credentials.news_api_key)) as resp:
			data = await resp.json()
		if data["status"] != "ok":
			await self.bot.embed_reply(":no_entry: Error: {}".format(data["message"]))
			return
		response, embed = await self.bot.reply("React with a number from 1 to 10 to view each news article")
		numbers = {'\N{KEYCAP TEN}': 10}
		for number in range(9):
			numbers[chr(ord('\u0031') + number) + '\N{COMBINING ENCLOSING KEYCAP}'] = number + 1 # '\u0031' - 1
		for number_emote in sorted(numbers.keys()):
			await self.bot.add_reaction(response, number_emote)
		while True:
			emoji_response = await self.bot.wait_for_reaction(user = ctx.message.author, message = response, emoji = numbers.keys())
			reaction = emoji_response.reaction
			number = numbers[reaction.emoji]
			article = data["articles"][number - 1]
			output = "Article {}:".format(number)
			output += "\n**{}**".format(article["title"])
			if article.get("publishedAt"):
				output += " ({})".format(article.get("publishedAt").replace('T', " ").replace('Z', ""))
			# output += "\n{}".format(article["description"])
			# output += "\n<{}>".format(article["url"])
			output += "\n{}".format(article["url"])
			output += "\nSelect a different number for another article"
			await self.bot.edit_message(response, "{}: {}".format(ctx.message.author.display_name, output))
	
	# urband
	# rtg
	
	@commands.command(pass_context = True)
	@checks.not_forbidden()
	async def mazer(self, ctx, width : int = 5, height : int = 5, random_start : bool = False, random_end : bool = False):
		'''
		Maze game
		With reactions
		width: 2 - 100
		height: 2 - 100
		React with an arrow key to move
		'''
		maze_instance = maze(width, height, random_start = random_start, random_end = random_end)
		maze_message, embed = await self.bot.embed_reply(clients.code_block.format(maze_instance.print_visible()), footer_text = "Your current position: {}, {}".format(maze_instance.column + 1, maze_instance.row + 1))
		self.mazes[maze_message.id] = maze_instance
		for emote in tuple(self.arrows.keys()) + ("\N{PRINTER}",):
			await self.bot.add_reaction(maze_message, emote)
		self.reaction_messages[maze_message.id] = lambda reaction, user: self.mazer_processr(ctx.message.author, reaction, user)
	
	async def mazer_processr(self, player, reaction, user):
		if user == player and reaction.emoji in tuple(self.arrows.keys()) + ("\N{PRINTER}",):
			maze_instance = self.mazes[reaction.message.id]
			if reaction.emoji == "\N{PRINTER}":
				with open("data/temp/maze.txt", 'w') as maze_file:
					maze_file.write('\n'.join(maze_instance.visible))
				await self.bot.send_file(reaction.message.channel, "data/temp/maze.txt", content = "{}:\nYour maze is attached".format(player.display_name))
				return
			embed = discord.Embed(color = clients.bot_color)
			avatar = player.avatar_url or player.default_avatar_url
			embed.set_author(name = player.display_name, icon_url = avatar)
			moved = maze_instance.move(self.arrows[reaction.emoji].lower())
			embed.set_footer(text = "Your current position: {}, {}".format(maze_instance.column + 1, maze_instance.row + 1))
			if moved:
				if maze_instance.reached_end():
					embed.description = "{}\nCongratulations! You reached the end of the maze in {} moves".format(clients.code_block.format(maze_instance.print_visible()), maze_instance.move_counter)
					del self.reaction_messages[reaction.message.id]
				else:
					embed.description = "{}".format(clients.code_block.format(maze_instance.print_visible()))
			else:
				embed.description = "{}\n:no_entry: You can't go that way".format(clients.code_block.format(maze_instance.print_visible()))
			await self.bot.edit_message(reaction.message, embed = embed)
	
	
async def process_reactions(reaction, user):
	await clients.client.cogs["Reactions"].reaction_messages[reaction.message.id](reaction, user)
	with open("data/stats.json", 'r') as stats_file:
		stats = json.load(stats_file)
	stats["reaction_responses"] += 1
	with open("data/stats.json", 'w') as stats_file:
		json.dump(stats, stats_file, indent = 4)
	
@clients.client.event
async def on_reaction_add(reaction, user):
	if "Reactions" in clients.client.cogs and reaction.message.id in clients.client.cogs["Reactions"].reaction_messages:
		await process_reactions(reaction, user)

@clients.client.event
async def on_reaction_remove(reaction, user):
	if "Reactions" in clients.client.cogs and reaction.message.id in clients.client.cogs["Reactions"].reaction_messages:
		await process_reactions(reaction, user)

