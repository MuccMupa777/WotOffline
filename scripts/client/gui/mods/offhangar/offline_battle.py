"""
Offline battle bootstrap for FakeServer.

Real servers answer enqueue with BW callbacks (onEnqueued / onArenaCreated). With only
FakeServer.doCmd* responses the client can exit or hang, so we replay the minimal chain.
Compatible checks keep this safe across 0.8.x builds that differ slightly.
"""

import time

from debug_utils import LOG_CURRENT_EXCEPTION

import BigWorld

from gui.mods.offhangar.logging import LOG_DEBUG
from gui.mods.offhangar.offline_battle_stack import build_offline_battle_context

_BATTLE_BOOT_DEBOUNCE_SEC = 1.5


def _resolve_real_arena_type(map_id, map_name, gameplay_name):
	"""
	Try to resolve a real ArenaType object from the client's cache.
	This provides minimap + other per-map metadata needed by battle GUI.
	"""
	try:
		try:
			import ArenaType as ArenaTypeModule
		except ImportError:
			# 0.8.2 ships it as `common/arenatype.pyc`
			try:
				from common import arenatype as ArenaTypeModule
			except ImportError:
				import arenatype as ArenaTypeModule
		cache = getattr(ArenaTypeModule, 'g_cache', None)
		# Lazy init on some builds: cache can start as None.
		for init_name in ('init', '_init', 'initialize'):
			init_fn = getattr(ArenaTypeModule, init_name, None)
			if callable(init_fn):
				try:
					init_fn()
					cache = getattr(ArenaTypeModule, 'g_cache', None)
				except Exception:
					LOG_CURRENT_EXCEPTION()
			if cache is not None:
				break

		if cache is None:
			LOG_DEBUG('OfflineBattle.arenaType.cacheMissing', map_name, 'module', getattr(ArenaTypeModule, '__name__', '?'))
			return None

		# Some builds provide module-level getters instead of direct cache access.
		for fn_name in ('getArenaType', 'getByGeometryName', 'getByName', 'getArenaTypeByName'):
			fn = getattr(ArenaTypeModule, fn_name, None)
			if callable(fn):
				for key in (map_name, map_id):
					try:
						at = fn(key)
						if at is not None:
							try:
								at.geometryName = map_name
								at.gameplayName = gameplay_name
							except Exception:
								pass
							return at
					except Exception:
						continue

		def _try_get(key):
			for getter in (
				lambda: cache.get(key),
				lambda: cache[key],
				lambda: cache.getArenaType(key) if hasattr(cache, 'getArenaType') else None,
				lambda: cache.getByID(key) if hasattr(cache, 'getByID') else None,
				lambda: cache.getById(key) if hasattr(cache, 'getById') else None,
			):
				try:
					at = getter()
					if at is not None:
						return at
				except Exception:
					continue
			return None

		# g_cache can be a mapping-like object; try the common access patterns.
		at = _try_get(map_name)
		if at is None and map_id:
			at = _try_get(map_id)
		# If stack provided short name like "himmelsdorf", try to match "04_himmelsdorf".
		if at is None and map_name and '_' not in map_name:
			try:
				keys = cache.keys() if hasattr(cache, 'keys') else []
				for k in keys:
					try:
						if isinstance(k, basestring) and (k == map_name or k.endswith('_' + map_name)):
							at = _try_get(k)
							if at is not None:
								map_name = k
								break
					except Exception:
						continue
			except Exception:
				LOG_CURRENT_EXCEPTION()
		if at is not None:
			try:
				at.geometryName = map_name
				at.gameplayName = gameplay_name
			except Exception:
				pass
			return at

		# 0.8.2: g_cache can be a dict keyed by arenaTypeID (int), with geometryName stored on values.
		try:
			if isinstance(cache, dict):
				for k, v in cache.iteritems():
					try:
						geom = getattr(v, 'geometryName', None) or ''
						if not isinstance(geom, basestring):
							continue
						if geom == map_name or geom.endswith('_' + map_name) or map_name.endswith('_' + geom):
							try:
								v.gameplayName = gameplay_name
							except Exception:
								pass
							return v
					except Exception:
						continue
		except Exception:
			LOG_CURRENT_EXCEPTION()

		# Diagnostics: log cache shape so we can implement the correct lookup for 0.8.2.
		try:
			cache_type = type(cache).__name__
			attrs = [a for a in dir(cache) if 'get' in a.lower() or 'arena' in a.lower() or 'type' in a.lower()]
			if isinstance(cache, dict):
				keys = cache.keys()
				key_types = {}
				for kk in keys[:50]:
					kt = type(kk).__name__
					key_types[kt] = key_types.get(kt, 0) + 1
				# also sample a few geometry names to confirm value shape
				sample_geom = []
				for vv in cache.values()[:10]:
					try:
						g = getattr(vv, 'geometryName', None)
						if g:
							sample_geom.append(g)
					except Exception:
						continue
				LOG_DEBUG(
					'OfflineBattle.arenaType.cacheNoHit',
					map_name, 'mapID', map_id,
					'cacheType', cache_type,
					'keyTypes', key_types,
					'sampleGeom', sample_geom[:5],
					'attrs', attrs[:20]
				)
			else:
				LOG_DEBUG('OfflineBattle.arenaType.cacheNoHit', map_name, 'mapID', map_id, 'cacheType', cache_type, 'attrs', attrs[:25])
		except Exception:
			LOG_CURRENT_EXCEPTION()
	except Exception:
		LOG_CURRENT_EXCEPTION()
	return None


def _queue_type_randoms():
	try:
		from constants import QUEUE_TYPE
		return QUEUE_TYPE.RANDOMS
	except Exception:
		# Very old builds: keep a sane default; onEnqueued may still accept an int.
		return 1


def _resolve_vehicle_inv_id(player, int1):
	if int1:
		return int1
	try:
		from CurrentVehicle import g_currentVehicle
		if g_currentVehicle is not None:
			item = getattr(g_currentVehicle, 'item', None)
			if item is not None:
				vid = getattr(item, 'invID', None)
				if vid:
					return vid
	except ImportError:
		pass
	except Exception:
		LOG_CURRENT_EXCEPTION()
	inv = getattr(player, 'inventory', None)
	if inv is None:
		return 0
	for methodName in (
		'getCurrVehicleInvID',
		'getCurrentVehInvID',
		'getVehicleInvID',
		'getCurrentInvID',
	):
		fn = getattr(inv, methodName, None)
		if callable(fn):
			try:
				v = fn()
				if v:
					return v
			except Exception:
				LOG_CURRENT_EXCEPTION()
	for methodName in ('getCurrentVehicle', 'getCurrVehicle'):
		fn = getattr(inv, methodName, None)
		if callable(fn):
			try:
				veh = fn()
				if veh is not None:
					vid = getattr(veh, 'invID', None)
					if vid:
						return vid
			except Exception:
				LOG_CURRENT_EXCEPTION()
	return 0


def _enable_offline_battle_transition(player):
	# Hangar hardening hooks in mod_offhangar must relax while loading an arena.
	player._offhangar_allow_world_clear = True
	# Allow become-non-player only after avatar spawn attempt.
	player._offline_allow_become_non_player = False


def _try_spawn_battle_avatar_stub(player, cmdName):
	"""
	Best-effort avatar bootstrap: if Account switches to non-player but no battle avatar
	is created by the engine, client falls into fini(). We try to create avatar entity.
	"""
	if player is None or not getattr(player, 'isOffline', False):
		return
	space_id = BigWorld.createSpace()
	for avatar_name in ('Avatar',):
		try:
			LOG_DEBUG('OfflineBattle.spawnAvatar.try', cmdName, avatar_name, 'space', space_id)
			player._offline_allow_become_non_player = True
			BigWorld.createEntity(avatar_name, space_id, 0, (0, 0, 0), (0, 0, 0), {})
			LOG_DEBUG('OfflineBattle.spawnAvatar.ok', avatar_name)
			return
		except Exception:
			LOG_CURRENT_EXCEPTION()
	player._offline_allow_become_non_player = False
	LOG_DEBUG('OfflineBattle.spawnAvatar.fail', cmdName)


def _step_on_enqueued(player, vehInvID, cmdName):
	try:
		_enable_offline_battle_transition(player)
		ctx = build_offline_battle_context(player, vehInvID)
		player._offhangar_battle_ctx = ctx
		player._offhangar_player_vehicle_id = ctx.get('playerVehicleID', vehInvID)
		player._offhangar_team = 1
		arena = getattr(player, '_offhangar_arena', None)
		if arena is not None:
			arena.vehicles = ctx.get('vehicles', {})
			arena.guiType = 0
			arena.bonusType = 0
			arena.extraData = {'mapName': ctx.get('mapName'), 'mapID': ctx.get('mapID')}
			map_name = ctx.get('mapName', '') or ''
			map_id = ctx.get('mapID', 0) or 0
			gameplay = 'ctf'
			real_arena_type = _resolve_real_arena_type(map_id, map_name, gameplay)
			if real_arena_type is not None:
				arena.arenaType = real_arena_type
				LOG_DEBUG('OfflineBattle.arenaType.real', map_name, 'minimap', hasattr(real_arena_type, 'minimap'))
			elif getattr(arena, 'arenaType', None) is not None:
				# Fallback: keep stub, but ensure required attrs exist.
				arena.arenaType.geometryName = map_name
				arena.arenaType.gameplayName = gameplay
				if not hasattr(arena.arenaType, 'minimap'):
					arena.arenaType.minimap = None
				LOG_DEBUG('OfflineBattle.arenaType.stub', map_name)
		queueType = _queue_type_randoms()
		LOG_DEBUG('OfflineBattle.onEnqueued', cmdName, 'queueType', queueType, 'vehInvID', vehInvID)
		onEnqueued = getattr(player, 'onEnqueued', None)
		if callable(onEnqueued):
			onEnqueued(queueType)
		if hasattr(player, 'isInRandomQueue'):
			player.isInRandomQueue = True
	except Exception:
		LOG_CURRENT_EXCEPTION()


def _step_on_arena_created(player, cmdName):
	try:
		if player is None:
			return
		if getattr(player, '_offhangar_arena_created_once', False):
			LOG_DEBUG('OfflineBattle.onArenaCreated skip duplicate', cmdName)
			return
		player._offhangar_arena_created_once = True
		LOG_DEBUG('OfflineBattle.onArenaCreated', cmdName)
		onArenaCreated = getattr(player, 'onArenaCreated', None)
		if callable(onArenaCreated):
			onArenaCreated()
		BigWorld.callback(0.05, lambda: _try_spawn_battle_avatar_stub(BigWorld.player(), cmdName))
	except Exception:
		LOG_CURRENT_EXCEPTION()


def _schedule_arena_created_resilient(cmdName, account_ref):
	# Race-safe firing: in some runs client tears down right after onEnqueued.
	# Fire immediately and then retry a couple of frames.
	def _fire():
		player = BigWorld.player() or account_ref
		_step_on_arena_created(player, cmdName)

	BigWorld.callback(0.0, _fire)
	BigWorld.callback(0.03, _fire)
	BigWorld.callback(0.10, _fire)


def schedule_random_battle_flow_after_enqueue(cmd, cmdName, args):
	"""
	Call after RES_SUCCESS was delivered for an enqueue-like command.
	args: tuple from doCmdInt3 (int1, int2, int3) or similar.
	"""
	player = BigWorld.player()
	if player is not None:
		now = time.time()
		if now - getattr(player, '_offhangar_sched_debounce', 0) < 1.0:
			LOG_DEBUG('OfflineBattle.schedule debounce', cmdName, cmd, args)
			return
		player._offhangar_sched_debounce = now

	int1 = args[0] if args else 0
	# Never treat server-stats traffic as battle (same numeric cmd id can alias in AccountCommands index).
	if cmdName and ('SERVER_STATS' in cmdName or 'REQ_SERVER_STATS' in cmdName):
		if int1 == 0 and (len(args) < 2 or args[1] == 0) and (len(args) < 3 or args[2] == 0):
			LOG_DEBUG('OfflineBattle.skip stats-shaped packet', cmdName, cmd, args)
			return

	def _run():
		player = BigWorld.player()
		if player is None or not getattr(player, 'isOffline', False):
			return
		player._offhangar_arena_created_once = False
		vehInvID = int1
		if vehInvID == 0 and cmdName and 'ENQUEUE' in cmdName:
			vehInvID = _resolve_vehicle_inv_id(player, 0)
		if not vehInvID:
			LOG_DEBUG('OfflineBattle.skip no vehInvID', cmdName, cmd, args)
			return
		_step_on_enqueued(player, vehInvID, cmdName)
		_schedule_arena_created_resilient(cmdName, player)

	# Run after the current frame so onCmdResponse callbacks finish first.
	BigWorld.callback(0.05, _run)


def start_offline_random_from_hangar(player, vehInvID):
	"""
	0.8.x hangar may spam other doCmd ids before/instead of CMD_ENQUEUE_RANDOM (700).
	When the client calls PlayerAccount.enqueueRandom, short-circuit here so we still
	fire the same BW-side chain as a real matchmaker ack.
	"""
	if player is None or not getattr(player, 'isOffline', False):
		return
	now = time.time()
	last = getattr(player, '_offhangar_battle_last_boot', 0.0)
	if now - last < _BATTLE_BOOT_DEBOUNCE_SEC:
		LOG_DEBUG('OfflineBattle.hook debounce skip', vehInvID)
		return
	player._offhangar_battle_last_boot = now

	cmdName = 'offline.enqueueRandom'

	def _run():
		p = BigWorld.player()
		if p is None or not getattr(p, 'isOffline', False):
			return
		p._offhangar_arena_created_once = False
		vid = vehInvID or _resolve_vehicle_inv_id(p, 0)
		if not vid:
			LOG_DEBUG('OfflineBattle.hook skip no vehInvID', vehInvID)
			return
		LOG_DEBUG('OfflineBattle.hook start', cmdName, 'vehInvID', vid)
		_step_on_enqueued(p, vid, cmdName)
		_schedule_arena_created_resilient(cmdName, p)

	BigWorld.callback(0.05, _run)
