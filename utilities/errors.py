
from discord.ext.commands.errors import CommandError

class NotServerOwner(CommandError):
	pass

class VoiceNotConnected(CommandError):
	pass

class SO_VoiceNotConnected(VoiceNotConnected):
	pass

class NSO_VoiceNotConnected(VoiceNotConnected):
	pass

class TagError(CommandError):
	pass

class NoTags(TagError):
	pass

class NoTag(TagError):
	pass