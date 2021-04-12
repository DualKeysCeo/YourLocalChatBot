import datetime

import discord
from discord.ext import commands

from .extension import Extension
from .utilities import Config, debugging
from .utilities import logger as l
from .utilities import prefix, secrets
from .utilities import utilities as u
from .utilities import ylcb_config


_guild = 0
_member_role = 0
_streamer_role = 0
_welcome_channel = 0
_changelog_channel = 0
_suggestion_channel = 0
_announcement_channel = 0


class Bot(commands.Cog):
	"""Base bot commands and functions"""
	def __init__(self, bot: commands.Bot):
		"""
		Bot(bot)

		Args:
			bot (`commands.Bot`): commands.Bot instance
		"""
		self.bot: commands.Bot = bot
		self.version: str = ylcb_config.data["meta"]["version"]
		self.build_num: int = ylcb_config.data["meta"]["build_number"]
		self.bot.remove_command("help")
	
	
	async def version_check(self):
		# split version and cahced_version into array of [api, major, minor]
		version_parts = [int(x) for x in self.version.split(".")]
		cached_version_parts = [int(x) for x in secrets.data["CACHED_VERSION"].split(".")]
		# if major/api update detected and not debugging
		if version_parts[0] != cached_version_parts[0] or version_parts[1] != cached_version_parts[1] and not debugging:
			#update cached version and build number
			secrets.data["CACHED_VERSION"] = self.version
			secrets.data["CACHED_BUILD"] = self.build_num
			
			## send new message and update stored message id
			nt = "\n\t- "
			embed = discord.Embed(title=f"Local Chat Bot v{version_parts[0]}.{version_parts[1]}.x", color=0xff6000)
			embed.set_author(name=f"Your Local Chat Bot", icon_url=self.bot.user.avatar_url)
			embed.add_field(name=f"v{self.version}b{self.build_num} Changelog", value=f"\t- {nt.join(ylcb_config.data['meta']['changelog'])}", inline=False)
			
			msg = await self.changelog_channel.send(embed=embed)
			secrets.data["CHANGELOG_MESSAGE_ID"] = msg.id
			## updates secrets
			secrets.updateFile()
		
		# if minor/build update detected and not debugging
		elif version_parts[2] != cached_version_parts[2] or self.build_num != secrets.data["CACHED_BUILD"] and not debugging:
			#update cached version and build number
			secrets.data["CACHED_BUILD"] = self.build_num
			secrets.data["CACHED_VERSION"] = self.version
			msg = await self.changelog_channel.fetch_message(secrets.data["CHANGELOG_MESSAGE_ID"])
			if msg.author != self.bot.user:
				l.log(f"Changelog message was sent by another user. Changelog message updating won't work until CHANGELOG_MESSAGE_ID in config/secrets.json is updated", lvl=l.WRN, channel=l.DISCORD)
			else:
				nt = "\n\t- "
				embed = msg.embeds[0]
				embed.add_field(name=f"v{self.version}b{self.build_num} Changelog", value=f"\t- {nt.join(ylcb_config.data['meta']['changelog'])}", inline=False)
				await msg.edit(embed=embed)
			## updates secrets
			secrets.updateFile()
	
	
	@commands.Cog.listener()
	async def on_ready(self):
		l.log("Discord bot ready...", channel=l.DISCORD)
		l.log(f"Running version: {self.version}b{self.build_num}", channel=l.DISCORD)
		
		global _guild
		global _member_role
		global _streamer_role
		global _welcome_channel
		global _changelog_channel
		global _suggestion_channel
		global _announcement_channel
		
		
		## server
		_guild =  self.bot.get_guild(ylcb_config.data["discord"]["guild_id"])
		self.guild = _guild
		
		## roles
		_member_role = self.guild.get_role(ylcb_config.data["discord"]["member_role_id"])
		self.member_role = _member_role
		_streamer_role = self.guild.get_role(ylcb_config.data["discord"]["streamer_role_id"])
		self.streamer_role = _streamer_role
		
		## channels
		_welcome_channel		= self.bot.get_channel(ylcb_config.data["discord"]["welcome_channel_id"])
		self.welcome_channel = _welcome_channel
		_changelog_channel		= self.bot.get_channel(ylcb_config.data["discord"]["changelog_channel_id"])
		self.changelog_channel = _changelog_channel
		_suggestion_channel		= self.bot.get_channel(ylcb_config.data["discord"]["suggestion_channel_id"])
		self.suggestion_channel = _suggestion_channel
		_announcement_channel	= self.bot.get_channel(ylcb_config.data["discord"]["announcement_channel_id"])
		self.announcement_channel = _announcement_channel
		
		
		await self.version_check()
		
		
		## for every extension you want to load, load it
		for extension in ylcb_config.data["extensions"]:
			l.log(f"Loading {extension}...", channel=l.DISCORD)
			loadable = True
			try: ## Try catch allows you to skip setting up a requirements value if no requirement is needed
				for requirement in Config(f"./src/ext/config/{extension}.json").data["requirements"]:
					if not self.bot.extensions.__contains__(f"ext.{requirement}") and requirement != "":
						try: self.bot.load_extension(f"ext.{requirement}")
						except Exception as e:
							l.log(f"\tCould not load requirement {requirement}", lvl=l.ERR, channel=l.DISCORD)
							l.log(f"\t{e}", lvl=l.ERR, channel=l.DISCORD)
							self.bot.remove_cog(extension)
							loadable = False
						else: l.log(f"\tLoaded requirement {requirement}", channel=l.DISCORD)
					else: l.log(f"\tRequirement {requirement} met", channel=l.DISCORD)
			except KeyError: pass
			if loadable:
				try: self.bot.load_extension(f"ext.{extension}")
				except commands.ExtensionAlreadyLoaded: l.log(f"Already loaded ext.{extension}")
				else: l.log(f"Loaded {extension}", channel=l.DISCORD)
	
	
	@commands.Cog.listener()
	async def on_member_join(self, user: discord.Member):
		await self.welcome_channel.send(f"Welcome to {self.guild.name}, {user.mention}")
		await user.add_roles(_member_role)
	
	
	@commands.Cog.listener()
	async def on_member_remove(self, user: discord.Member):
		await self.welcome_channel.send(f"We will miss you, {u.discordify(str(user))}")
	
	
	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		if message.author == self.bot.user: return
		await self.bot.wait_until_ready()
		l.log(_suggestion_channel, "_suggestion_channel")
		l.log(self.suggestion_channel, "self.suggestion_channel")
		if message.channel == _suggestion_channel:
			embed_dict = {
				"title": "Feature Request",
				"timestamp": datetime.now().isoformat(),
				"type": "rich",
				"color": 0x8000ff,
				"author": {
					"name": u.discordify(str(message.author)),
					"icon_url": str(message.author.avatar_url)
				},
				"fields": [
					{"name": "Request", "value": message.content}
				]
			}
			embed = discord.Embed(embed=discord.Embed.from_dict(embed_dict))
			if message.author.id not in ylcb_config.data["devs"]:
				await message.author.send("Your request has been sent to the developers. They will respond as soon as possible. The embed below is what they have recieved.", embed=embed)
			l.log(f"Request from {u.discordify(str(message.author))} recieved", channel=l.DISCORD)
			
			for dev in ylcb_config.data["devs"]:
				developer: discord.User = await self.bot.fetch_user(dev)
				if developer:
					try: await developer.send(embed=embed)
					except Exception as e:
						l.log(e, lvl=l.ERR, channel=l.DISCORD)
				else: l.log(f"Developer with ID {dev} does not exist!", lvl=l.ERR, channel=l.DISCORD)
	
	
	@commands.before_invoke
	async def before_invoke(self, ctx):
		l.log(ctx, channel=l.DISCORD)
	
	
	## basic commands
	
	
	@commands.command(name="version", usage=f"{prefix}version", brief="Tells you what version I'm running")
	async def version_command(self, ctx):
		"""
		Tells you what version I'm running
		"""
		await ctx.send(f"I'm running version {self.version}b{self.build_num}")
	
	
	@commands.command(name="help", usage=f"{prefix}help [command:str]", brief="This command")
	async def help_command(self, ctx, command: str = None):
		"""
		This command

		Args:
			command (`str`, optional): Command or extension name. Defaults to `None`.
		"""
		
		fields = []
		
		if not command:
			fields.append({"name": "Base", "value": "Base bot commands - ylcb-devs", "inline": True})
			for i,cog in enumerate(self.bot.cogs):
				if not i: continue
				cog: Extension = self.bot.get_cog(cog)
				fields.append({"name": cog.name, "value": cog.description, "inline": True})
		else:
			if f"ext.{command}" in self.bot.extensions:
				cog: commands.Cog = self.bot.get_cog(command)
				for cmd in cog.get_commands():
					cmd: commands.Command
					if not cmd.hidden: fields.append({"name": cmd.name, "value": cmd.brief, "inline": True})
			elif self.bot.get_command(command):
				cmd = self.bot.get_command(command)
				fields.append({"name": cmd.name, "value": cmd.help, "inline": True})
				fields.append({"name": "Usage", "value": f"`{cmd.usage}`", "inline": True})
				if cmd.aliases: fields.append({"name": "Aliases", "value": ", ".join(cmd.aliases), "inline": True})
		embed_dict = {
			"title": "Help",
			"description": "`<...>` is a required parameter.\n`[...]` is an optional parameter.\n`:` specifies a type",
			"color": 0x15F3FF,
			"fields": fields,
			"timestamp": datetime.datetime.now().isoformat()
		}
		await ctx.send(embed=discord.Embed.from_dict(embed_dict))
	
	
	## dev level commands
	
	
	@commands.command(name="list", hidden=True)
	@u.is_dev()
	async def list(self, ctx):
		await ctx.send(", ".join(self.bot.cogs))
	
	
	@commands.command(name="dev", hidden=True)
	@u.is_dev()
	async def dev(self, ctx, _user: discord.Member = None):
		"""Add a developer to the team"""
		if not _user:
			await ctx.send(f"{ctx.author.mention}, please tag a user to make them a developer.")
			return
		
		if _user.id in ylcb_config.data["devs"]:
			await ctx.send(f"{ctx.author.mention}, that user is already a developer.")
			return
		
		ylcb_config.data["devs"].append(_user.id)
		ylcb_config.updateFile()
		await ctx.send(f"{_user.mention}, {ctx.author.mention} has made you a developer!")
	@dev.error
	async def dev_error(self, ctx, error):
		if isinstance(error, commands.CheckFailure):
			await ctx.send(f"{ctx.author.mention}, this command can only be used by developers")
	
	
	@commands.command(name="stop", hidden=True)
	@u.is_dev()
	async def stop(self, ctx):
		"""Safely stop the bot"""
		try:
			db = self.bot.get_cog("database").db
			if db: db.close()
		except: pass
		await ctx.send(f"Goodbye.")
		await self.bot.close()
		l.log("Successfully logged out and closed. Exiting...", lvl=l.FLG, channel=l.DISCORD)
		exit(1)


def setup(bot):
	bot.add_cog(Bot(bot))
