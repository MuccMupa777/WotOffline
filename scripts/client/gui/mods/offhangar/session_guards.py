from GameSessionController import _GameSessionController

from gui.mods.offhangar.logging import LOG_DEBUG
from gui.mods.offhangar.utils import override


FORCE_ALLOW_BATTLE_ENTRY = True


def normalize_offline_stats(stats):
	"""Disable anti-offline restrictions in account stats payload."""
	if not isinstance(stats, dict):
		return
	stats['battlesTillCaptcha'] = 0
	stats['captchaTriesLeft'] = 0
	stats['restrictions'] = {}


def _always_false(baseFunc, baseSelf, *args, **kwargs):
	return False


def _always_true(baseFunc, baseSelf, *args, **kwargs):
	return True


def install_game_session_guards():
	"""
	Patch GameSessionController restrictions that can block battle entry.
	Only patch existing methods to stay compatible with different 0.8.x builds.
	"""
	patches_false = (
		'needCaptcha',
		'isCaptchaRequired',
		'isParentalControlActive',
		'hasParentalControl',
		'hasActiveSessionLimit'
	)
	for method_name in patches_false:
		if hasattr(_GameSessionController, method_name):
			override(_GameSessionController, method_name)(_always_false)
			LOG_DEBUG('SessionGuard.disable', method_name)

	if FORCE_ALLOW_BATTLE_ENTRY:
		for method_name in ('isAccountAllowedToBattle', 'canJoinBattle'):
			if hasattr(_GameSessionController, method_name):
				override(_GameSessionController, method_name)(_always_true)
				LOG_DEBUG('SessionGuard.forceAllowBattle', method_name)
