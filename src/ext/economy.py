import datetime

import discord
import modules.utilities as utils
from discord.ext import commands
from modules.utilities import logger as l
from modules.utilities import prefix
from modules.utilities import utilities as u

from ext import Extension

class economy(Extension):
	"""Economy Extension - ylcb-devs"""
	def __init__(self, bot: commands.Bot):
		"""Economy(bot)"""
		super().__init__(bot, "ext.economy")
		self.db = bot.get_cog("database").db
	
	
	def get_balance_from_d_id(self, discord_id: int)									-> float:
		"""Returns the given user's balance"""
		return self.db.cursor().execute("SELECT balance FROM Users WHERE discord_id=:d_id", {"d_id": discord_id}).fetchone()[0]
	def set_balance_from_d_id(self, discord_id: int, bal: int)							-> float:
		"""Returns and sets a given users balance to bal"""
		self.db.execute("UPDATE Users SET balance=:bal WHERE discord_id=:d_id", {"bal": round(bal, 2), "d_id": discord_id})
		self.db.commit()
		return round(bal, 2)
	def can_pay_amount(self, sender: discord.Member, amount: int)						-> bool	:
		"""Returns if balance can be paid"""
		snd_bal = self.get_balance_from_d_id(sender.id)
		return snd_bal > amount
	def get_transaction_history_from_id(self, discord_id: int)							-> list	:
		return self.db.cursor().execute("SELECT transaction_history FROM Users WHERE discord_id=:d_id", {"d_id": discord_id}).fecthone()[0]
	def set_transaction_history_from_id(self, discord_id: int, value: dict) 			-> dict	:
		self.db.execute("UPDATE Users SET transaction_history=:th WHERE discord_id=:d_id", {"th": value, "d_id": discord_id})
		self.db.commit()
		return value
	def clear_transaction_history_from_id(self, discord_id: int)						-> dict	:
		return self.set_transaction_history(discord_id, [])
	def push_transaction_history_from_id(self, discord_id: int, place:str, amount:int)	-> dict	:
		thCur: dict = self.get_transaction_history_from_id(discord_id)
		if len(thCur) >= 3:
			for x in range(len(thCur) - 2):
				thCur.pop()
		thCur.insert(0,{"place": place, "amount": amount})
		return thCur
	
	@commands.command(name="balance", aliases=["bal"], usage=f"{prefix}balance [user:user]")
	async def balance(self,ctx, user: discord.Member = None):
		"""Returns your or another users balance"""
		if not user: user = ctx.author
		points = self.get_balance_from_d_id(user.id)
		embed_dict = {
			"title":"Bank",
			"type": "rich",
			"timestamp": datetime.datetime.now().isoformat(),
			"color": 0x00ff00,
			"fields": [
				{"name": "Balance", "value": "$"+str(points)}
			],
			"author": {
				"name": user.display_name,
				"icon_url": str(user.avatar_url)
			}
		}
		th = self.get_transaction_history_from_id(user.id)
		values: list = []
		for entry in th:
			if th["amount"] > 0 : emoji = "🟩"
			else: emoji = "🟥"
			if len(th["place"]) > 20: 
				th["place"] = th["place"][:20]
				th["place"][19] = "…"
			value = f"{emoji}\t{th['place'].ljust(20)}\t{th['amount']}"
			values.append(value)
		embed_dict["fields"].push({"name": "Transaction History", "value": "\n".join(values)})
		embed = discord.Embed.from_dict(embed_dict)
		await ctx.send(embed=embed)
	
	
	@commands.command(name="pay", usage=f"{prefix}pay <reciever:user> [amount:float=50] [message:str]")
	async def pay(self,ctx, reciever: discord.Member, amount: float = 50, *, message: str = None):
		"""Pay another user"""
		if reciever == ctx.author:
			await ctx.send(f"{ctx.author.mention}, you cannot send money to yourself")
			return
		amount = round(amount, 2)
		if self.can_pay_amount(ctx.author, amount):
			l.log(f"Check: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Reciever:{reciever.display_name}#{reciever.discriminator} | Status: AWAITING APPROVAL", channel=l.DISCORD)
			self.set_balance_from_d_id(ctx.author.id, self.get_balance_from_d_id(ctx.author.id)-amount)
			embed_dict = {
				"title":"Check [AWAITING APPROVAL]",
				"type": "rich",
				"timestamp": datetime.datetime.now().isoformat(),
				"color": 0xff8800,
				"fields": [
					{"name": "Pay To:", "value": reciever.display_name+"#"+reciever.discriminator, "inline":True},
					{"name": "Balance:", "value": "$"+str(amount), "inline":True},
					{"name": "From:", "value": ctx.author.display_name+"#"+ctx.author.discriminator, "inline":True},
				]
			}
			if message: embed_dict["fields"].append({"name": "Message:", "value": message})
			
			embed = discord.Embed.from_dict(embed_dict)
			msg: dicsord.Message = await ctx.send(f"Are you sure you want to pay this user ${amount}",embed=embed)
			await msg.add_reaction("✅")
			await msg.add_reaction("❎")
			def check(payload: discord.RawReactionActionEvent): return payload.user_id == ctx.author.id and str(payload.emoji) in ["✅", "❎"] and payload.message_id == msg.id
			payload = await self.bot.wait_for("raw_reaction_add", check=check)
			
			if str(payload.emoji) == "✅":
				embed_dict["title"] = "Check [PENDING]"
				l.log(f"Check: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Reciever:{reciever.display_name}#{reciever.discriminator} | Status: APPROVED,PENDING", channel=l.DISCORD)
			elif str(payload.emoji) == "❎":
				await msg.delete()
				await ctx.message.delete()
				self.set_balance_from_d_id(ctx.author.id, self.get_balance_from_d_id(ctx.author.id)+amount)
				l.log(f"Check: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Reciever:{reciever.display_name}#{reciever.discriminator} | Status: CANCELED", channel=l.DISCORD)
			
			embed = discord.Embed.from_dict(embed_dict)
			await msg.edit(content=reciever.mention,embed=embed)
			def check(payload: discord.RawReactionActionEvent): return payload.member == reciever and str(payload.emoji) in ["✅", "❎"] and payload.message_id == msg.id
			payload = await self.bot.wait_for("raw_reaction_add", check=check)
			
			if str(payload.emoji) == "✅":
				embed_dict["title"] = "Check [ACCEPTED]"
				embed_dict["color"] = 0x00ff00
				try:
					self.set_balance_from_d_id(reciever.id, self.get_balance_from_d_id(reciever.id)-amount)
					self.push_transaction_history_from_id(ctx.author.id, "Transfer", -1*amount)
				except Exception as e: l.log(e, l.ERR, l.DISCORD)
				else:self.set_balance_from_d_id(ctx.author.id, self.get_balance_from_d_id(ctx.author.id)+amount)
				self.set_balance_from_d_id(reciever.id, self.get_balance_from_d_id(reciever.id)+amount)
				self.push_transaction_history_from_id(reciever.id, "Transfer", amount)
				l.log(f"Check: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Reciever:{reciever.display_name}#{reciever.discriminator} | Status: ACCEPTED,PAID", channel=l.DISCORD)
			elif str(payload.emoji) == "❎":
				embed_dict["title"] = "Check [DECLINED]"
				embed_dict["color"] = 0xff0000
				l.log(f"Check: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Reciever:{reciever.display_name}#{reciever.discriminator} | Status: DECLINED,REFUNDED", channel=l.DISCORD)
				self.set_balance_from_d_id(ctx.author.id, self.get_balance_from_d_id(ctx.author.id)+amount)
			embed_dict["timestamp"] = datetime.datetime.now().isoformat()
			await msg.edit(content=None, embed=discord.Embed.from_dict(embed_dict))
			try: await msg.clear_reactions()
			except Exception as e: l.log(e, l.WRN, l.DISCORD)
		else:
			l.log(f"Check: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Reciever:{reciever.display_name}#{reciever.discriminator} | Status: BANK DECLINED", channel=l.DISCORD)
			await ctx.send(f"{ctx.author.mention}, you only have ${self.get_balance_from_d_id(ctx.author.id)}")
	
	
	@commands.command(name="request", aliases=["req"], usage=f"{prefix}request <sender:user> [amount:float=50] [message:str]")
	async def request(self,ctx,sender: discord.Member, amount: float = 50, *, message: str = None):
		"""Request money from another user"""
		if sender == ctx.author:
			await ctx.send(f"{ctx.author.mention}, you cannot request money from yourself")
			return
		if self.can_pay_amount(sender, amount):
			l.log(f"Money Request: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Payer:{sender.display_name}#{sender.discriminator} | Status: APPROVED,PENDING", channel=l.DISCORD)
			embed_dict = {
				"title":"Money Request [PENDING]",
				"type": "rich",
				"timestamp": datetime.datetime.now().isoformat(),
				"color": 0xff8800,
				"fields": [
					{"name": "Pay To:", "value": ctx.author.display_name+"#"+ctx.author.discriminator, "inline":True},
					{"name": "Balance:", "value": "$"+str(amount), "inline":True},
					{"name": "From:", "value": sender.display_name+"#"+sender.discriminator, "inline":True},
				]
			}
			if message: embed_dict["fields"].append({"name": "Message:", "value": message})
			
			embed = discord.Embed.from_dict(embed_dict)
			msg: dicsord.Message = await ctx.send(sender.mention,embed=embed)
			await msg.add_reaction("✅")
			await msg.add_reaction("❎")
			def check(payload: discord.RawReactionActionEvent): return payload.member == sender and str(payload.emoji) in ["✅", "❎"] and payload.message_id == msg.id
			payload = await self.bot.wait_for("raw_reaction_add", check=check)
			
			if str(payload.emoji) == "✅":
				embed_dict["title"] = "Money Request [ACCEPTED]"
				embed_dict["color"] = 0x00ff00
				try:
					self.set_balance_from_d_id(sender.id, self.get_balance_from_d_id(sender.id)-amount)
					self.push_transaction_history_from_id(sender.id, "Transfer", amount*-1)
				except Exception as e: l.log(e, l.ERR, l.DISCORD)
				else: self.set_balance_from_d_id(ctx.author.id, self.get_balance_from_d_id(ctx.author.id)+amount)
				self.push_transaction_history_from_id(ctx.author.id, "Transfer", amount)
				l.log(f"Money Request: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Payer:{sender.display_name}#{sender.discriminator} | Status: ACCEPTED,PAID", channel=l.DISCORD)
			elif str(payload.emoji) == "❎":
				embed_dict["title"] = "Money Request [DECLINED]"
				embed_dict["color"] = 0xff0000
				l.log(f"Money Request: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Payer:{sender.display_name}#{sender.discriminator} | Status: DECLINED,REFUNDED", channel=l.DISCORD)
				self.set_balance_from_d_id(sender.id, self.get_balance_from_d_id(sender.id)+amount)
			embed_dict["timestamp"] = datetime.datetime.now().isoformat()
			await msg.edit(content=None, embed=discord.Embed.from_dict(embed_dict))
			try: await msg.clear_reactions()
			except Exception as e: l.log(e, l.WRN, l.DISCORD)
		else:
			l.log(f"Money Request: {ctx.author.display_name}#{ctx.author.discriminator} | Amount:${amount} | Payer:{sender.display_name}#{sender.discriminator} | Status: DECLINED", channel=l.DISCORD)
			await ctx.send(f"{ctx.author.mention}, that user has insufficient funds!")
	
	
	@commands.command(name="go_broke", aliases=["0"], usage=f"{prefix}go_broke")
	async def go_broke(self, ctx):
		try:
			self.set_balance_from_d_id(ctx.author.id, 0)
			self.clear_transaction_history_from_id(ctx.author.id)
		except Exception as e: l.log(e, l.ERR, l.DISCORD)
		else: await ctx.send(f"{ctx.author.mention}, congrats you're broke...")
	
	
	#ANCHOR admin commands
	
	@commands.command(name="set_balance", hidden=True)
	@u.is_admin()
	async def set_balance(self, ctx, user: discord.Member, amount: float = 0):
		"""Set the given user's balance to amount"""
		try:
			self.set_balance_from_d_id(user.id, amount)
			self.clear_transaction_history_from_id(user.id)
			self.push_transaction_history_from_id(user.id, "Admin Set Amount", amount)
		except Exception as e: l.log(e, l.ERR, l.DISCORD)
		else: await ctx.send(f"{ctx.author.mention}, {user.mention}'s balance is now ${amount}")
	@set_balance.error
	async def set_balance_error(self, ctx, error):
		if isinstance(error, commands.CheckFailure):
			await ctx.send(f"{ctx.author.mention}, this command can only be used by admins")
	
	
	@commands.command(name="add_balance", hidden=True)
	@u.is_admin()
	async def add_balance(self, ctx, user: discord.Member, amount: float):
		"""Add an amount to the given user's balance"""
		try: 
			self.set_balance_from_d_id(user.id, self.get_balance_from_d_id(user.id) + amount)
			self.push_transaction_history_from_id(ctx.author.id, "Admin Added Amount", amount)
		except Exception as e: l.log(e, l.ERR, l.DISCORD)
		else: await ctx.send(f"{ctx.author.mention}, {user.mention}'s balance is now ${self.get_balance_from_d_id(user.id)}")
	@add_balance.error
	async def add_balance_error(self, ctx, error):
		if isinstance(error, commands.CheckFailure):
			await ctx.send(f"{ctx.author.mention}, this command can only be used by admins")
	
	
	@commands.command(name="sub_balance", hidden=True)
	@u.is_admin()
	async def sub_balance(self, ctx, user: discord.Member, amount: float):
		"""Subtract an amount from the given user's balance"""
		try:
			self.set_balance_from_d_id(user.id, self.get_balance_from_d_id(user.id) - amount)
			self.push_transaction_history_from_id(ctx.author.id, "Admin Removed Amount", amount*-1)
		except Exception as e: l.log(e, l.ERR, l.DISCORD)
		else: await ctx.send(f"{ctx.author.mention}, {user.mention}'s balance is now ${self.get_balance_from_d_id(user.id)}")
	@sub_balance.error
	async def sub_balance_error(self, ctx, error):
		if isinstance(error, commands.CheckFailure):
			await ctx.send(f"{ctx.author.mention}, this command can only be used by admins")

def setup(bot):
	bot.add_cog(economy(bot))
