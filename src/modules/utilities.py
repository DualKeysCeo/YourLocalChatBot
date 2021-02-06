import datetime, json, discord

from discord.ext.commands import Context
from neotermcolor import cprint
from sys import argv

class Config:
	"""Config class"""
	
	def __init__(self, path: str = "config.json"):
		"""Config()"""
		self.path = f"config/{path}"
		self.data: dict
		self.updateData()
	
	
	def updateFile(self) -> None:
		"""Updates config file with current data"""
		with open(self.path, "w+") as f:
			f.write(json.dumps(self.data))
			f.close()
	
	
	def updateData(self) -> dict:
		"""Loads contents of config file into data"""
		self.data = json.load(open(self.path))
		return self.data


class Logger:
	"""Logger class"""
	CMD = 1
	WRN = 2
	ERR = 3
	LOG = 4
	FLG = 5
	
	
	def __init__(self):
		"""Logger()"""
		ts = str(datetime.datetime.now()).replace(':', '-')
		self.log_file_path = f"logs/{ts}.log"
		if __debug__: self.log_file_path = f"logs/DEBUG {ts}.log"
		log_file = open(self.log_file_path, "a+")
		log_file.close()
	
	
	def log(self, msg, lvl = LOG):
		"""Decent logging system"""
		timestamp = str(datetime.datetime.now().isoformat(timespec='seconds')).replace('T', ' ')
		
		prefix = "LOG"
		color = "white"
		
		if type(msg) is Context:
			logString = f"[{prefix}] {timestamp}: {msg.command.name} command ran by {msg.author.display_name}#{msg.author.discriminator}"
			lvl = self.CMD
		else: logString = f"[{prefix}] {timestamp}: {msg}"
		
		if lvl == self.WRN:
			prefix = "WRN"
			color = "yellow"
		elif lvl == self.ERR:
			prefix = "ERR"
			color = "red"
		elif lvl == self.CMD:
			prefix = "CMD"
			color = "green"
		elif lvl == self.FLG:
			prefix = "FLG"
			color = "magenta"
		
		cprint(logString, color=color)
		log_file = open(self.log_file_path, "a+")
		log_file.write(logString + "\n")
		log_file.close()


class Utilities:
	"""Utilities class"""
	@staticmethod
	def admin(author: discord.Member) -> bool:
		"""Returns if user is an admin"""
		if author.guild_permissions.administrator: return True
		return False
	
	
	@staticmethod
	def streamer(user: discord.Member) -> bool:
		"""Returns if a user is a streamer"""
		for role in user.roles:
			if role.id == ylcb_config.data["discord"]["streamer_role_id"]: return True
		return False
	
	
	@staticmethod
	def dev(author: discord.Member) -> bool:
		"""Returns if user is a developer"""
		if author.id in ylcb_config.data["devs"]: return True
		return False


ylcb_config = Config("config.json")
secrets = Config("secrets.json")
utilities = Utilities()
logger = Logger()