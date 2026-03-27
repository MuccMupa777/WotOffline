import os
import random

from gui.mods.offhangar.logging import LOG_DEBUG


def _veh_type_descriptor_from_compact_descr(compact_descr):
	"""
	BattleContext expects `vehicleType` to be a descriptor object (has `.type`),
	not an int compact descr.
	"""
	try:
		if not compact_descr:
			return None
		from items import vehicles
		vd = vehicles.VehicleDescr(compactDescr=compact_descr)
		td = getattr(vd, 'typeDescriptor', None)
		if td is not None:
			return td
		# Fallback: some builds expose it as `type`.
		t = getattr(vd, 'type', None)
		return t
	except Exception:
		return None


def _discover_map_pool():
	"""
	Build map pool from the game's arena_defs naming convention.
	We cannot rely on plain-text XML here (0.8.2 ships DataSection binaries),
	so we keep a resilient, filename-based fallback list.
	"""
	# Primary: hardcoded list derived from WoT 0.8.2 `res/scripts/arena_defs/*.xml`.
	names = (
		'01_karelia',
		'02_malinovka',
		'03_campania',
		'04_himmelsdorf',
		'05_prohorovka',
		'06_ensk',
		'07_lakeville',
		'08_ruinberg',
		'10_hills',
		'11_murovanka',
		'13_erlenberg',
		'14_siegfried_line',
		'15_komarin',
		'17_munchen',
		'18_cliff',
		'19_monastery',
		'22_slough',
		'23_westfeld',
		'28_desert',
		'29_el_hallouf',
		'31_airfield',
		'33_fjord',
		'34_redshire',
		'35_steppes',
		'36_fishing_bay',
		'37_caucasus',
		'38_mannerheim_line',
		'39_crimea',
		'42_north_america',
		'44_north_america',
		'45_north_america',
		'47_canada_a',
		'51_asia',
	)

	pool = []
	for nm in names:
		try:
			map_id = int(nm.split('_', 1)[0])
		except Exception:
			map_id = 0
		pool.append((map_id, nm))
	return tuple(pool)


_MAP_POOL = _discover_map_pool()


def _make_player_info(acc_id, team, nick, veh_id, veh_type_compact_descr):
	return {
		'accountDBID': acc_id,
		'name': nick,
		'team': team,
		'vehicleInvID': veh_id,
		'vehTypeCompDescr': veh_type_compact_descr,
		# Battle GUI may use this key; keep compact descr here (icons/etc).
		'vehicleType': veh_type_compact_descr,
		'isAlive': True,
	}


def _resolve_selected_compact_descr(player):
	try:
		from CurrentVehicle import g_currentVehicle
		item = getattr(g_currentVehicle, 'item', None)
		if item is not None:
			return getattr(item, 'typeCompDescr', 0) or 0
	except Exception:
		pass
	# Fallback: resolve from offline inventory compDescr map by current/selected invID.
	try:
		inv = getattr(player, 'inventory', None)
		if inv is not None and hasattr(inv, '_Inventory__cache'):
			cache = getattr(inv, '_Inventory__cache', None) or {}
			vehData = cache.get('inventory', {}).get(1, {})  # ITEM_TYPE_INDICES['vehicle'] == 1 in 0.8.x
			compDescrMap = vehData.get('compDescr', {})
			# invIDs in our offline inventory start from 1 and map to compactDescr ints.
			vid = getattr(player, 'playerVehicleID', 0) or 0
			if vid and vid in compDescrMap:
				return compDescrMap.get(vid, 0) or 0
	except Exception:
		pass
	try:
		td = getattr(player, 'vehicleTypeDescriptor', None)
		return getattr(td, 'typeCompDescr', 0) or 0
	except Exception:
		return 0


def build_offline_battle_context(player, selected_veh_inv_id):
	"""
	Build minimal pseudo-battle stack for the client:
	- map: random from 0.8.2 arena_defs pool
	- team1: player + 14 bots
	- team2: 15 bots

	Important: keys/fields here are consumed by the arena/avatar stubs injected by the mod.
	"""
	map_id, map_name = random.choice(_MAP_POOL)
	allies, enemies = [], []

	player_dbid = getattr(player, 'databaseID', 10000001) or 10000001
	player_name = getattr(player, 'name', 'offline_player') or 'offline_player'
	# Prefer compDescr by selected inv id to avoid circular playerVehicleID fallback.
	selected_compact_descr = 0
	try:
		from CurrentVehicle import g_currentVehicle
		item = getattr(g_currentVehicle, 'item', None)
		if item is not None:
			selected_compact_descr = getattr(item, 'typeCompDescr', 0) or 0
	except Exception:
		selected_compact_descr = 0
	if not selected_compact_descr:
		try:
			inv = getattr(player, 'inventory', None)
			cache = getattr(inv, '_Inventory__cache', None) or {}
			vehData = cache.get('inventory', {}).get(1, {})
			compDescrMap = vehData.get('compDescr', {})
			if selected_veh_inv_id and selected_veh_inv_id in compDescrMap:
				selected_compact_descr = compDescrMap.get(selected_veh_inv_id, 0) or 0
			# Last-resort: pick any available vehicle compact descr.
			if not selected_compact_descr and compDescrMap:
				try:
					selected_compact_descr = compDescrMap.values()[0] or 0
				except Exception:
					selected_compact_descr = 0
		except Exception:
			selected_compact_descr = 0
	if not selected_compact_descr:
		selected_compact_descr = _resolve_selected_compact_descr(player)

	# Use "vehicle id" space distinct from hangar invIDs: battle systems treat it as a vehicle entity id.
	player_vehicle_id = 1
	allies.append(_make_player_info(player_dbid, 1, player_name, player_vehicle_id, selected_compact_descr))

	for i in xrange(14):
		acc_id = 20000000 + i
		allies.append(_make_player_info(acc_id, 1, 'Bot_%d' % (i + 1), i + 2, selected_compact_descr))

	for i in xrange(15):
		acc_id = 30000000 + i
		enemies.append(_make_player_info(acc_id, 2, 'Bot_%d' % (i + 15), i + 16, selected_compact_descr))

	vehicles = {}
	for p in (allies + enemies):
		v_id = p['vehicleInvID']
		td = _veh_type_descriptor_from_compact_descr(p['vehTypeCompDescr'])
		vehicles[v_id] = {
			'accountDBID': p['accountDBID'],
			'team': p['team'],
			'name': p['name'],
			'vehTypeCompDescr': p['vehTypeCompDescr'],
			# Critical: BattleContext expects `.type` on this value.
			'vehicleType': td if td is not None else p['vehTypeCompDescr'],
			'isAlive': True,
		}

	ctx = {
		'mapID': map_id,
		'mapName': map_name,
		'playerVehicleID': player_vehicle_id,
		'selectedVehInvID': selected_veh_inv_id,
		'selectedVehTypeCompDescr': selected_compact_descr,
		'team1': allies,
		'team2': enemies,
		'vehicles': vehicles,
	}
	LOG_DEBUG('OfflineBattleStack.ready', map_name, 'mapID', map_id, 'allies', len(allies), 'enemies', len(enemies), 'vehCD', selected_compact_descr)
	return ctx

