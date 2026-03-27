import cPickle
import functools
import random
import time
import zlib

import AccountCommands
import BigWorld
import game
from debug_utils import LOG_CURRENT_EXCEPTION

from gui.mods.offhangar._constants import REQUEST_CALLBACK_TIME
from gui.mods.offhangar.command_router import RequestResult
from gui.mods.offhangar.data import (
	getOfflineInventory,
	getOfflineStats,
	getOfflineQuestsProgress
)
from gui.mods.offhangar.logging import LOG_DEBUG
from gui.mods.offhangar.offline_battle import (
	schedule_random_battle_flow_after_enqueue,
	start_offline_random_from_hangar,
)
from gui.mods.offhangar.session_guards import normalize_offline_stats


def _resolve_cmd(name, fallback):
	return getattr(AccountCommands, name, fallback)


_ACCOUNT_CMD_INDEX = {}

# Core sync/shop/stat commands.
CMD_REQ_SERVER_STATS = _resolve_cmd('CMD_REQ_SERVER_STATS', 100)
CMD_COMPLETE_TUTORIAL = _resolve_cmd('CMD_COMPLETE_TUTORIAL', 101)
CMD_SYNC_DATA = _resolve_cmd('CMD_SYNC_DATA', 102)
CMD_SYNC_SHOP = _resolve_cmd('CMD_SYNC_SHOP', 103)
CMD_SYNC_DOSSIERS = _resolve_cmd('CMD_SYNC_DOSSIERS', 104)
CMD_SET_LANGUAGE = _resolve_cmd('CMD_SET_LANGUAGE', 105)

# Battle pipeline (0.8.x may miss some symbolic names, so keep numeric fallback).
CMD_ENQUEUE_RANDOM = _resolve_cmd('CMD_ENQUEUE_RANDOM', 202)
CMD_PREBATTLE_ACTION = _resolve_cmd('CMD_PREBATTLE_ACTION', 203)
CMD_ARENA_LIST = _resolve_cmd('CMD_ARENA_LIST', 204)
CMD_QUEUE_INFO = _resolve_cmd('CMD_QUEUE_INFO', 205)


def _pack_stream(requestID, data):
	data = zlib.compress(cPickle.dumps(data))
	desc = cPickle.dumps((len(data), zlib.crc32(data)))
	return functools.partial(game.onStreamComplete, requestID, desc, data)


def _success(data=None):
	return RequestResult(AccountCommands.RES_SUCCESS, '', data)


def _stream():
	return RequestResult(AccountCommands.RES_STREAM, '', None)


def handle_server_stats(fake_server, requestID, cmd, args):
	player = BigWorld.player()
	tnow = time.time()
	key = (requestID, cmd)
	lastKey = getattr(player, '_offhangar_stats_last_key', None)
	lastT = getattr(player, '_offhangar_stats_last_time', 0.0)
	dedupe = (
		getattr(player, 'isOffline', False)
		and key == lastKey
		and (tnow - lastT) < 0.3
	)
	if dedupe:
		LOG_DEBUG('Offline.stats dedupe skip receiveServerStats', requestID, cmd)
	else:
		try:
			BigWorld.player().receiveServerStats({
				'clusterCCU': 155000 * (1 - random.uniform(0.0, 0.15)),
				'regionCCU': 815000 * (1 - random.uniform(0.0, 0.15))
			})
		except Exception:
			LOG_CURRENT_EXCEPTION()
	player._offhangar_stats_last_key = key
	player._offhangar_stats_last_time = tnow

	# 0.8.2 hangar may spam CMD_REQ_SERVER_STATS (501) with zeros while waiting for matchmaker;
	# real ENQUEUE_RANDOM (700) never reaches FakeServer. Break the stall after a short burst.
	int1 = args[0] if args else 0
	int2 = args[1] if len(args) > 1 else 0
	int3 = args[2] if len(args) > 2 else 0
	if getattr(player, 'isOffline', False) and int1 == 0 and int2 == 0 and int3 == 0:
		streak = getattr(player, '_offhangar_stats501_streak', 0) + 1
		player._offhangar_stats501_streak = streak
		if streak >= 2:
			player._offhangar_stats501_streak = 0
			LOG_DEBUG('Offline.heuristic501Burst', streak, requestID, cmd)
			start_offline_random_from_hangar(player, 0)
	else:
		if player is not None:
			player._offhangar_stats501_streak = 0
	return _success()


def handle_complete_tutorial(fake_server, requestID, cmd, args):
	return _success({})


def handle_sync_data(fake_server, requestID, cmd, args):
	revision = args[0] if args else 0
	data = {'rev': revision + 2, 'prevRev': revision}
	data.update(getOfflineInventory())
	data.update(getOfflineStats())
	data.update(getOfflineQuestsProgress())
	normalize_offline_stats(data.get('stats', {}))
	return _success(data)


def handle_sync_shop(fake_server, requestID, cmd, args):
	revision = args[0] if args else 0
	data = {'rev': revision + 2, 'prevRev': revision}
	BigWorld.callback(REQUEST_CALLBACK_TIME, _pack_stream(requestID, data))
	return _stream()


def handle_sync_dossiers(fake_server, requestID, cmd, args):
	revision = args[0] if args else 0
	BigWorld.callback(REQUEST_CALLBACK_TIME, _pack_stream(requestID, (revision + 2, [])))
	return _stream()


def handle_set_language(fake_server, requestID, cmd, args):
	language = args[0] if args else 'ru'
	BigWorld.callback(REQUEST_CALLBACK_TIME, _pack_stream(requestID, language))
	return _stream()


def handle_enqueue_random(fake_server, requestID, cmd, args):
	cmdName = _ACCOUNT_CMD_INDEX.get(cmd, 'UNKNOWN_ENQUEUE')
	LOG_DEBUG('BattleStub.enqueue', requestID, cmdName, cmd, args)
	schedule_random_battle_flow_after_enqueue(cmd, cmdName, args)
	return _success()


def handle_stats_or_enqueue_collision(fake_server, requestID, cmd, args):
	"""
	0.8.x can reuse the same numeric id for unrelated CMD_* names in AccountCommands index
	(last name wins). Random queue uses vehInvID in int1; REQ_SERVER_STATS uses zeros.
	"""
	int1 = args[0] if args else 0
	int2 = args[1] if len(args) > 1 else 0
	int3 = args[2] if len(args) > 2 else 0
	if int1 == 0 and int2 == 0 and int3 == 0:
		return handle_server_stats(fake_server, requestID, cmd, args)
	cmdName = _ACCOUNT_CMD_INDEX.get(cmd, 'UNKNOWN_ENQUEUE')
	LOG_DEBUG('BattleStub.enqueueSameIdAsStats', requestID, cmdName, cmd, args)
	schedule_random_battle_flow_after_enqueue(cmd, cmdName, args)
	return _success()


def handle_prebattle(fake_server, requestID, cmd, args):
	LOG_DEBUG('BattleStub.prebattleOrQueue', requestID, cmd, args)
	return _success()


def handle_unknown(fake_server, requestID, cmd, args):
	# Fallback strategy for offline mode: do not break flow on unknown commands.
	LOG_DEBUG('CommandRouter.unknown', requestID, cmd, args)
	return _success()


def configure_router(router):
	global _ACCOUNT_CMD_INDEX
	_ACCOUNT_CMD_INDEX = {}
	for name in dir(AccountCommands):
		if not name.startswith('CMD_'):
			continue
		value = getattr(AccountCommands, name, None)
		if isinstance(value, int):
			_ACCOUNT_CMD_INDEX[value] = name

	enqueueDebug = []
	for name in dir(AccountCommands):
		if not name.startswith('CMD_'):
			continue
		if 'ENQUEUE' not in name:
			continue
		val = getattr(AccountCommands, name, None)
		if isinstance(val, int):
			enqueueDebug.append((name, val))
	LOG_DEBUG('AccountCommands.CMD_ENQUEUE_*', enqueueDebug)

	cmd501Names = sorted(
		n for n in dir(AccountCommands)
		if n.startswith('CMD_') and getattr(AccountCommands, n, None) == 501
	)
	LOG_DEBUG('AccountCommands.cmdId_501', cmd501Names)

	if CMD_ENQUEUE_RANDOM == CMD_REQ_SERVER_STATS:
		router.register(CMD_REQ_SERVER_STATS, handle_stats_or_enqueue_collision)
	else:
		router.register(CMD_REQ_SERVER_STATS, handle_server_stats)
		router.register(CMD_ENQUEUE_RANDOM, handle_enqueue_random)

	router.register(CMD_COMPLETE_TUTORIAL, handle_complete_tutorial)
	router.register(CMD_SYNC_DATA, handle_sync_data)
	router.register(CMD_SYNC_SHOP, handle_sync_shop)
	router.register(CMD_SYNC_DOSSIERS, handle_sync_dossiers)
	router.register(CMD_SET_LANGUAGE, handle_set_language)

	# Battle flow + possible follow-up commands.
	router.register(CMD_PREBATTLE_ACTION, handle_prebattle)
	router.register(CMD_ARENA_LIST, handle_prebattle)
	router.register(CMD_QUEUE_INFO, handle_prebattle)

	router.set_fallback(handle_unknown)
