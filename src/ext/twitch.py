import discord, requests, sqlite3
import requests
import modules.utilities as utils

from discord.ext.commands	import Context
from discord.ext			import commands, tasks
from modules.utilities		import utilities as u,secrets,ylcb_config
from ext					import *
import datetime


class twitch(Extension):
	"""Twitch Extension - ylcb-devs"""
	def __init__(self, bot: commands.Bot):
		"""Twitch(bot)"""
		super().__init__(
			bot,
			"ext.twitch",
			requirements=	{"database"},
			config=			utils.Config(f"exts/twitch.json")
		)
		self.db = bot.get_cog("database").db
		self.printer.start()
	
	
	def cog_unload(self):
		self.printer.cancel()
	
	
	""" TODO 
		generalize database entry code
		with the entry of extensions and the attempt to let anyone make extensions the database is no longer just for streamers
	"""
	@commands.command(name="streamer")
	async def streamer(self, ctx: Context, _user: discord.Member = None, _username: str = None) -> None:
		"""Adds twitch username to the database"""
		u.log(ctx)
		if not u.admin(ctx.author):
			await ctx.send(f"{ctx.author.mention}, only admins can use this command.")
			return
		if not _user:
			await ctx.send(f"{ctx.author.mention}, please tag a user to make them a streamer.")
			return
		if not _username:
			await ctx.send(f"{ctx.author.mention}, please specify the user\'s Twitch username.")
			return
		if u.streamer(_user):
			await ctx.send(f"{ctx.author.mention}, that user is already a streamer.")
			return
		
		guild = await self.bot.fetch_guild(ylcb_config.data["discord"]["guild_id"])
		await _user.add_roles(guild.get_role(ylcb_config.data["discord"]["streamer_role_id"]))
		##ANCHOR layout of the database
		self.db.execute(
			"INSERT INTO Users VALUES (:username,:id,:d_id,:json,:bal,:items)", 
			{
				"username": _username,
				"id": None,
				"d_id": _user.id,
				"json":"{}",
				"bal": 100,
				"items": "{}"
			}
		)
		self.db.commit()
		# "twitch_username": _username,	#str
		# "message_id": None,			#int
		# "discord_id": _user.id,		#int
		# "response": {},				#json
		# "balance": 100,				#int
		await ctx.send(f"{_user.mention}, {ctx.author.mention} has made you a streamer!")
	
	
	@commands.command()
	async def raid(self, ctx, twitchChannel = None):
		"""Gives specified use a shoutout"""
		u.log(ctx)
		if not u.admin(ctx.author):
			await ctx.send(f"{ctx.author.mention}, only admins can use this command.")
			return
		if not twitchChannel:
			await ctx.send(f"{ctx.author.mention}, please specify a channel name.")
			return
		
		await ctx.send(f"@everyone we're raiding https://twitch.tv/{twitchChannel}")

	
	
	##ANCHOR check if streamer is live
	async def check(self, streamerChannel: discord.TextChannel) -> bool:
		for streamer in self.db.cursor().execute("SELECT * FROM Users").fetchall(): #ANCHOR db entry
			username = streamer[0]
			message_id = streamer[1]
			discord_id = streamer[2]
			response = streamer[3]
			
			headers = {
				"User-Agent": "Your user agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36 OPR/63.0.3368.51 (Edition beta)",
				"Client-ID": secrets.data["twitch_client_id"],
				"Authorization": f"Bearer {secrets.data['twitch_access_token']}"
			}
			
			u.log(f"\tChecking if {username} is live...")
			
			r = requests.get(f"https://api.twitch.tv/helix/streams?user_login={username}", headers=headers)
			try: streamData = r.json()["data"][0]
			except: streamData = r.json()["data"]
			r.close()
			
			
			if streamData:
				r = requests.get(f"https://api.twitch.tv/helix/users?id={streamData['user_id']}", headers=headers)
				try: userData = r.json()["data"][0]
				except: userData = r.json()["data"]
				r.close()
				
				r = requests.get(f"https://api.twitch.tv/helix/games?id={streamData['game_id']}", headers=headers)
				try: gameData = r.json()["data"][0]
				except: gameData = r.json()["data"]
				r.close()
				
				user: discord.User  = await self.bot.fetch_user(int(streamer[2]))
				embed_dict = {
					"title": streamData["title"],
					"url": f"https://twitch.tv/{username}",
					"type": "rich",
					"timestamp": datetime.datetime.now().isoformat(),
					"color": 0x8000ff,
					"fields": [
						{"name": "Game", "value": gameData["name"], "inline": True},
						{"name": "Viewers", "value": streamData["viewer_count"], "inline": True}
					],
					"author": {
						"name": user.name,
						"icon_url": str(user.avatar_url)
					},
					"thumbnail": {
						"url": streamData["box_art_url"].format(width=390, height=519),
						"width": 390,
						"height": 519
					},
					"image": {
						"url": streamData["thumbnail_url"].format(width=1280, height=720),
						"width": 1280,
						"height": 720
					}
				}
				embed = discord.Embed.from_dict(embed_dict)
				
				if not message_id:
					u.log(f"\t\t{username} is now live, announcing stream...")
					if not __debug__:msg = await streamerChannel.send(f"@everyone {user.mention} is live!", embed=embed)
					else			:msg = await streamerChannel.send(f"{user.mention} is live!", embed=embed)
					self.db.execute("UPDATE Users SET message_id=:id WHERE twitch_username=:username", {"id":msg.id,"username":username})
					self.db.commit()
				elif response != streamData:
					msg = await streamerChannel.fetch_message(streamer[1])
					u.log(f"\t\tUpdating {username}\'s live message...")
					if not __debug__:msg = await msg.edit(content=f"@everyone {user.mention} is live!", embed=embed)
					else			:msg = await msg.edit(content=f"{user.mention} is live!", embed=embed)
					self.db.execute("UPDATE Users SET response=:json WHERE twitch_username=:username", {"json":json.dumps(streamData),"username":username})
					self.db.commit()
			elif streamer[1]:
				u.log(f"\t\t{username} is no longer live, deleting message...")
				msg = await streamerChannel.fetch_message(streamer[1])
				await msg.delete()
				self.db.execute("UPDATE Users SET message_id=:id,response=:json WHERE twitch_username=:username", {"id":None,"json":"{}","username":username})
				self.db.commit()
		return True
	
	
	@tasks.loop(seconds=60)
	async def printer(self):
		u.log("Checking twitch...")
		if await self.check(self.bot.get_channel(utils.ylcb_config.data["discord"]["announcement_channel_id"])):
			u.log("Check Successful")
	
	
	@printer.before_loop
	async def before_printer(self):
		await self.bot.wait_until_ready()


def setup(bot):
	bot.add_cog(twitch(bot))
