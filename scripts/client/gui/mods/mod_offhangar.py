import os
import signal

import Account
import AccountCommands
import Avatar as AvatarModule
import AvatarInputHandler as AvatarInputHandlerModule
import BigWorld
import account_shared

from ConnectionManager import connectionManager
from GameSessionController import _GameSessionController
from account_helpers.Shop import Shop
from debug_utils import LOG_CURRENT_EXCEPTION, LOG_ERROR
from gui.Scaleform.Login import Login
from gui.Scaleform.gui_items.Vehicle import Vehicle
from helpers.time_utils import _TimeCorrector, _g_instance
from nations import INDICES
from predefined_hosts import g_preDefinedHosts

from gui.mods.offhangar.logging import *
from gui.mods.offhangar.utils import *
from gui.mods.offhangar._constants import *
from gui.mods.offhangar.server import *
from gui.mods.offhangar.data import getOfflineShopItems
from gui.mods.offhangar.session_guards import install_game_session_guards
from gui.mods.offhangar.offline_battle import start_offline_random_from_hangar

Account.LOG_DEBUG = LOG_DEBUG
Account.LOG_NOTE = LOG_NOTE
Account.LOG_ERROR = LOG_ERROR

g_preDefinedHosts._hosts.append(g_preDefinedHosts._makeHostItem(OFFLINE_SERVER_ADDRESS, OFFLINE_SERVER_ADDRESS, OFFLINE_SERVER_ADDRESS))


class _OfflineArenaStub(object):
	class _VehicleTypeStub(object):
		def __init__(self):
			self.type = self
			self.tags = set()
			self.turretRotatorSpeed = 0.0
			self.circularVisionRadius = 0

		def __getattr__(self, name):
			return 0

	class _ArenaTypeStub(object):
		def __init__(self):
			self.weatherPresets = []
			self.geometryName = ''
			self.gameplayName = ''
			# Battle UI (Minimap) expects `arenaType.minimap` to exist.
			self.minimap = None

	class _EventStub(object):
		def __iadd__(self, other):
			return self

		def __isub__(self, other):
			return self

		def __call__(self, *args, **kwargs):
			return

	def __init__(self):
		self.vehicles = {}
		self.arenaType = self._ArenaTypeStub()
		self.guiType = 0
		self.bonusType = 0
		self.extraData = {}
		self._event_stubs = {}

	def __getattr__(self, name):
		# Defensive fallback: battle subsystems read many optional arena attrs.
		if name.startswith('on'):
			if name not in self._event_stubs:
				self._event_stubs[name] = self._EventStub()
			return self._event_stubs[name]
		return 0


class _OfflineVehicleStub(object):
	class _TypeDescriptorStub(object):
		def __init__(self):
			self.type = _OfflineArenaStub._VehicleTypeStub()

		def __getattr__(self, name):
			return 0

	def __init__(self):
		self.typeDescriptor = self._TypeDescriptorStub()
		self.id = 0


class _OfflineEvent(object):
	def __iadd__(self, other):
		return self

	def __isub__(self, other):
		return self

	def __call__(self, *args, **kwargs):
		return


def _ensure_postmortem_event(obj):
	if obj is None:
		return
	try:
		cur = getattr(obj, 'onPostmortemVehicleChanged', None)
		if cur is None or callable(cur):
			obj.onPostmortemVehicleChanged = _OfflineEvent()
	except Exception:
		LOG_CURRENT_EXCEPTION()


# Force killing game process
def fini():
	os.kill(os.getpid(), signal.SIGTERM)

@override(Shop, '__onSyncComplete')
def Shop__onSyncComplete(baseFunc, baseSelf, syncID, data):
	data = {
		'berthsPrices': (16, 16, [300]),
		'freeXPConversion': (25, 1),
		'dropSkillsCost': {
			0: {'xpReuseFraction': 0.5, 'gold': 0, 'credits': 0},
			1: {'xpReuseFraction': 0.75, 'gold': 0, 'credits': 20000},
			2: {'xpReuseFraction': 1.0, 'gold': 200, 'credits': 0}
		},
		'refSystem': {
			'maxNumberOfReferrals': 50,
			'posByXPinTeam': 10,
			'maxReferralXPPool': 350000,
			'periods': [(24, 3.0), (168, 2.0), (876000, 1.5)]
		},
		'playerEmblemCost': {
			0: (15, True),
			30: (6000, False),
			7: (1500, False)
		},
		'premiumCost': {
			1: 250,
			3: 650,
			7: 1250,
			30: 2500,
			180: 13500,
			360: 24000
		},
		'winXPFactorMode': 0,
		'sellPriceModif': 0.5,
		'passportChangeCost': 50,
		'exchangeRateForShellsAndEqs': 400,
		'exchangeRate': 400,
		'tankmanCost': ({
			'isPremium': False,
			'baseRoleLoss': 0.20000000298023224,
			'gold': 0,
			'credits': 0,
			'classChangeRoleLoss': 0.20000000298023224,
			'roleLevel': 50
		},
		{
			'isPremium': False,
			'baseRoleLoss': 0.10000000149011612,
			'gold': 0,
			'credits': 20000,
			'classChangeRoleLoss': 0.10000000149011612,
			'roleLevel': 75
		},
		{
			'isPremium': True,
			'baseRoleLoss': 0.0,
			'gold': 200,
			'credits': 0,
			'classChangeRoleLoss': 0.0,
			'roleLevel': 100
		}),
		'paidRemovalCost': 10,
		'dailyXPFactor': 2,
		'changeRoleCost': 500,
		'items': getOfflineShopItems(),
		'customization': dict((nation, {'camouflages': {}}) for nation in INDICES.values()),
		'isEnabledBuyingGoldShellsForCredits': True,
		'slotsPrices': (9, [300]),
		'freeXPToTManXPRate': 10,
		'sellPriceFactor': 0.5,
		'isEnabledBuyingGoldEqsForCredits': True,
		'playerInscriptionCost': {
			0: (15, True),
			7: (1500, False),
			30: (6000, False),
			'nations': {}
		}
	}

	baseFunc(baseSelf, syncID, data)

@override(_TimeCorrector, 'serverRegionalTime')
def TimeCorrector_serverRegionalTime(baseFunc, baseSelf):
	regionalSecondsOffset = 0
	try:
		serverRegionalSettings = OFFLINE_SERVER_SETTINGS['regional_settings']
		regionalSecondsOffset = serverRegionalSettings['starting_time_of_a_new_day']
	except Exception:
		LOG_CURRENT_EXCEPTION()
	return _g_instance.serverUTCTime + regionalSecondsOffset

@override(_GameSessionController, 'isSessionStartedThisDay')
def GameSessionController_isSessionStartedThisDay(baseFunc, baseSelf):
	serverRegionalSettings = OFFLINE_SERVER_SETTINGS['regional_settings']
	return int(_g_instance.serverRegionalTime) / 86400 == int(baseSelf._GameSessionController__sessionStartedAt + serverRegionalSettings['starting_time_of_a_new_day']) / 86400

@override(_GameSessionController, '_getWeeklyPlayHours')
def GameSessionController_getWeeklyPlayHours(baseFunc, baseSelf):
	serverRegionalSettings = OFFLINE_SERVER_SETTINGS['regional_settings']
	weekDaysCount = account_shared.currentWeekPlayDaysCount(_g_instance.serverUTCTime, serverRegionalSettings['starting_time_of_a_new_day'], serverRegionalSettings['starting_day_of_a_new_weak'])
	return baseSelf._getDailyPlayHours() + sum(baseSelf._GameSessionController__stats.dailyPlayHours[1:weekDaysCount])

@override(Vehicle, 'canSell')
def Vehicle_canSell(baseFunc, baseSelf):
	return BigWorld.player().isOffline or baseFunc(baseSelf)

@override(Login, 'populateUI')
def Login_populateUI(baseFunc, baseSelf, proxy):
	baseFunc(baseSelf, proxy)
	connectionManager.connect(OFFLINE_SERVER_ADDRESS, OFFLINE_LOGIN, OFFLINE_PWD, False, False, False)

@override(Account.PlayerAccount, '__init__')
def Account_init(baseFunc, baseSelf):
	baseSelf.isOffline = not baseSelf.name
	if baseSelf.isOffline:
		baseSelf.fakeServer = FakeServer()
		baseSelf.name = OFFLINE_NICKNAME
		baseSelf.serverSettings = OFFLINE_SERVER_SETTINGS
		baseSelf._offhangar_arena = _OfflineArenaStub()
		baseSelf._offhangar_vehicle_stub = _OfflineVehicleStub()
		baseSelf._offhangar_allow_world_clear = False
		baseSelf._offline_allow_become_non_player = False
		baseSelf._offhangar_stats501_streak = 0

	baseFunc(baseSelf)

	if baseSelf.isOffline:
		BigWorld.player(baseSelf)

@override(Account.PlayerAccount, '__getattribute__')
def Account_getattribute(baseFunc, baseSelf, name):
	if name == 'team' and baseSelf.isOffline:
		return getattr(baseSelf, '_offhangar_team', 1)
	if name == 'vehicleTypeDescriptor' and baseSelf.isOffline:
		ctx = getattr(baseSelf, '_offhangar_battle_ctx', None) or {}
		if ctx.get('selectedVehTypeCompDescr'):
			try:
				from items import vehicles
				vd = vehicles.VehicleDescr(compactDescr=ctx.get('selectedVehTypeCompDescr'))
				td = getattr(vd, 'typeDescriptor', None)
				if td is not None:
					return td
			except Exception:
				LOG_CURRENT_EXCEPTION()
			vehStub = getattr(baseSelf, '_offhangar_vehicle_stub', None)
			if vehStub is None:
				vehStub = _OfflineVehicleStub()
				baseSelf._offhangar_vehicle_stub = vehStub
			td = getattr(vehStub, 'typeDescriptor', None)
			if td is None:
				vehStub.typeDescriptor = _OfflineVehicleStub._TypeDescriptorStub()
				td = vehStub.typeDescriptor
			td.typeCompDescr = ctx.get('selectedVehTypeCompDescr')
			return td
		try:
			from CurrentVehicle import g_currentVehicle
			item = getattr(g_currentVehicle, 'item', None)
			if item is not None:
				td = getattr(item, 'typeDescriptor', None)
				if td is not None:
					return td
		except Exception:
			LOG_CURRENT_EXCEPTION()
		vehStub = getattr(baseSelf, '_offhangar_vehicle_stub', None)
		if vehStub is None:
			vehStub = _OfflineVehicleStub()
			baseSelf._offhangar_vehicle_stub = vehStub
		td = getattr(vehStub, 'typeDescriptor', None)
		if td is None:
			vehStub.typeDescriptor = _OfflineVehicleStub._TypeDescriptorStub()
			td = vehStub.typeDescriptor
		return td
	if name == 'playerVehicleID' and baseSelf.isOffline:
		if getattr(baseSelf, '_offhangar_player_vehicle_id', 0):
			return baseSelf._offhangar_player_vehicle_id
		try:
			from CurrentVehicle import g_currentVehicle
			item = getattr(g_currentVehicle, 'item', None)
			if item is not None:
				return getattr(item, 'invID', 0)
		except Exception:
			LOG_CURRENT_EXCEPTION()
		return 0
	if name == 'arena' and baseSelf.isOffline:
		return getattr(baseSelf, '_offhangar_arena', None)
	if name in ('cell', 'base', 'server') and baseSelf.isOffline:
		name = 'fakeServer'
	
	return baseFunc(baseSelf, name)

@override(Account.PlayerAccount, 'onBecomePlayer')
def Account_onBecomePlayer(baseFunc, baseSelf):
	baseFunc(baseSelf)
	_ensure_postmortem_event(getattr(baseSelf, 'inputHandler', None))
	if baseSelf.isOffline:
		baseSelf.showGUI(OFFLINE_GUI_CTX)

@override(Account.PlayerAccount, 'onBecomeNonPlayer')
def Account_onBecomeNonPlayer(baseFunc, baseSelf):
	# Hangar-only stub: skip teardown. Allow when offline battle flow explicitly enables it.
	if baseSelf.isOffline and not getattr(baseSelf, '_offline_allow_become_non_player', False):
		LOG_DEBUG('OfflineStub.skip onBecomeNonPlayer')
		return
	baseFunc(baseSelf)

@override(BigWorld, 'clearEntitiesAndSpaces')
def BigWorld_clearEntitiesAndSpaces(baseFunc, *args):
	player = BigWorld.player()
	if getattr(player, 'isOffline', False) and not getattr(player, '_offhangar_allow_world_clear', False):
		return
	baseFunc(*args)

@override(BigWorld, 'connect')
def BigWorld_connect(baseFunc, server, loginParams, progressFn):
	if server == OFFLINE_SERVER_ADDRESS:
		LOG_DEBUG('BigWorld.connect')
		progressFn(1, "LOGGED_ON", {})
		BigWorld.createEntity('Account', BigWorld.createSpace(), 0, (0, 0, 0), (0, 0, 0), {})
	else:
		baseFunc(server, loginParams, progressFn)


def _offline_enqueue_random_cmd_id():
	return getattr(AccountCommands, 'CMD_ENQUEUE_RANDOM', 700)


def _install_offline_account__do_cmd_hook():
	"""
	Newer clients call base.doCmdInt3(NO_RESPONSE, ENQUEUE_RANDOM, ...) and skip __doCmd.
	0.8.x often routes matchmaker through _PlayerAccount__doCmd — intercept CMD_ENQUEUE_RANDOM there.
	"""
	if '_PlayerAccount__doCmd' not in dir(Account.PlayerAccount):
		LOG_DEBUG('Offline.__doCmd missing on PlayerAccount')
		return
	try:
		@override(Account.PlayerAccount, '__doCmd')
		def PlayerAccount___doCmd(baseFunc, baseSelf, doCmdMethod, cmd, callback, *args):
			if not getattr(baseSelf, 'isOffline', False):
				return baseFunc(baseSelf, doCmdMethod, cmd, callback, *args)
			if doCmdMethod != 'doCmdInt3' or cmd != _offline_enqueue_random_cmd_id():
				return baseFunc(baseSelf, doCmdMethod, cmd, callback, *args)
			getRid = getattr(baseSelf, '_PlayerAccount__getRequestID', None)
			if not callable(getRid):
				LOG_DEBUG('Offline.__doCmd ENQUEUE_RANDOM skip no __getRequestID')
				return baseFunc(baseSelf, doCmdMethod, cmd, callback, *args)
			rid = getRid()
			if rid is None:
				return baseFunc(baseSelf, doCmdMethod, cmd, callback, *args)
			respMap = getattr(baseSelf, '_PlayerAccount__onCmdResponse', None)
			if callback is not None and respMap is not None:
				respMap[rid] = callback
			vehInvID = args[0] if args else 0

			def _ack_and_boot():
				try:
					baseSelf.onCmdResponse(rid, AccountCommands.RES_SUCCESS, '')
				except Exception:
					LOG_CURRENT_EXCEPTION()
				start_offline_random_from_hangar(baseSelf, vehInvID)

			LOG_DEBUG('Offline.__doCmd ENQUEUE_RANDOM', rid, vehInvID)
			BigWorld.callback(0.0, _ack_and_boot)
			return rid
	except Exception:
		LOG_CURRENT_EXCEPTION()


def _install_offline_enqueue_public_hooks():
	# Direct API (when present): newer builds; 0.8.2 may omit or name differently.
	if hasattr(Account.PlayerAccount, 'enqueueRandom'):
		@override(Account.PlayerAccount, 'enqueueRandom')
		def PlayerAccount_enqueueRandom(baseFunc, baseSelf, *args, **kwargs):
			if getattr(baseSelf, 'isOffline', False):
				vehInvID = args[0] if args else 0
				LOG_DEBUG('Offline.enqueueRandom intercepted', vehInvID)
				start_offline_random_from_hangar(baseSelf, vehInvID)
				return
			return baseFunc(baseSelf, *args, **kwargs)
	else:
		LOG_DEBUG('Offline.enqueueRandom missing')

	candidates = []
	for name in dir(Account.PlayerAccount):
		if not isinstance(name, basestring):
			continue
		low = name.lower()
		if 'tutorial' in low or 'bootcamp' in low or 'sandbox' in low:
			continue
		if 'enqueue' in low and 'random' in low and name != 'enqueueRandom':
			candidates.append(name)
	if candidates:
		LOG_DEBUG('Offline.enqueueExtraCandidates', candidates)
	for methodName in candidates:
		try:
			def _bind(nm):
				@override(Account.PlayerAccount, nm)
				def _enqueueAlt(baseFunc, baseSelf, *args, **kwargs):
					if getattr(baseSelf, 'isOffline', False):
						LOG_DEBUG('Offline.intercepted', nm, args)
						start_offline_random_from_hangar(baseSelf, args[0] if args else 0)
						return
					return baseFunc(baseSelf, *args, **kwargs)
			_bind(methodName)
		except Exception:
			LOG_CURRENT_EXCEPTION()


def _install_offline_battle_transport_hooks():
	_install_offline_account__do_cmd_hook()
	_install_offline_enqueue_public_hooks()


def _install_offline_avatar_guards():
	def _ensure_offline_avatar_state(baseSelf):
		# Emulate minimal subset of fields that normal server bootstrap sets.
		defaults = {
			'_PlayerAvatar__stepsTillInit': 1,
			'_PlayerAvatar__isSpaceInitialized': False,
			'_PlayerAvatar__setOwnVehicleMatrixTimerID': 0,
			'playerVehicleID': 0,
		}
		for key, value in defaults.iteritems():
			if not hasattr(baseSelf, key):
				setattr(baseSelf, key, value)
		if not hasattr(baseSelf, 'arena'):
			baseSelf.arena = _OfflineArenaStub()
		if not hasattr(baseSelf, '_offhangar_vehicle_stub'):
			baseSelf._offhangar_vehicle_stub = _OfflineVehicleStub()
		vehStub = baseSelf._offhangar_vehicle_stub
		# 'vehicle' can be read-only on PlayerAvatar in 0.8.2, use private attrs only.
		for attrName in ('_Avatar__vehicleAttached', '_PlayerAvatar__vehicleAttached', '_Avatar__vehicle'):
			if not hasattr(baseSelf, attrName) or getattr(baseSelf, attrName) is None:
				try:
					setattr(baseSelf, attrName, vehStub)
				except TypeError:
					# Read-only slots on some builds.
					pass
				except Exception:
					LOG_CURRENT_EXCEPTION()

	seen = set()
	for className in ('Avatar', 'PlayerAvatar'):
		avatarCls = getattr(AvatarModule, className, None)
		if avatarCls is None or not hasattr(avatarCls, 'onEnterWorld'):
			continue
		# Some builds alias PlayerAvatar to Avatar; avoid double-wrapping same class.
		if id(avatarCls) in seen:
			continue
		seen.add(id(avatarCls))

		@override(avatarCls, 'onEnterWorld')
		def _avatar_onEnterWorld(baseFunc, baseSelf, _className=className, *args, **kwargs):
			_ensure_offline_avatar_state(baseSelf)
			try:
				if args:
					return baseFunc(baseSelf, *args, **kwargs)
				# 0.8.2 can call onEnterWorld without prereqs in edge transitions.
				return baseFunc(baseSelf, [])
			except KeyError as ex:
				if 'fake_model.model' in str(ex):
					LOG_DEBUG('OfflineAvatar.ignore missing model', _className, ex)
					return
				raise

		if hasattr(avatarCls, 'onLeaveWorld'):
			@override(avatarCls, 'onLeaveWorld')
			def _avatar_onLeaveWorld(baseFunc, baseSelf, _className=className, *args, **kwargs):
				_ensure_offline_avatar_state(baseSelf)
				try:
					return baseFunc(baseSelf, *args, **kwargs)
				except AttributeError as ex:
					msg = str(ex)
					if 'playerVehicleID' in msg or '_PlayerAvatar__stepsTillInit' in msg or '_PlayerAvatar__setOwnVehicleMatrixTimerID' in msg:
						LOG_DEBUG('OfflineAvatar.ignore leave attr', _className, ex)
						return
					raise
				except ValueError as ex:
					msg = str(ex)
					if 'py_cancelCallback' in msg:
						LOG_DEBUG('OfflineAvatar.ignore leave callback', _className, ex)
						return
					raise

		if hasattr(avatarCls, 'getVehicleAttached'):
			@override(avatarCls, 'getVehicleAttached')
			def _avatar_getVehicleAttached(baseFunc, baseSelf, *args, **kwargs):
				try:
					veh = baseFunc(baseSelf, *args, **kwargs)
					if veh is not None:
						return veh
				except Exception:
					LOG_CURRENT_EXCEPTION()
				_ensure_offline_avatar_state(baseSelf)
				return getattr(baseSelf, '_offhangar_vehicle_stub')


def _install_offline_input_guards():
	accIhCls = getattr(Account, 'AccountInputHandler', None)
	if accIhCls is not None and hasattr(accIhCls, '__init__'):
		@override(accIhCls, '__init__')
		def _accIh_init(baseFunc, baseSelf, *args, **kwargs):
			baseFunc(baseSelf, *args, **kwargs)
			_ensure_postmortem_event(baseSelf)
		LOG_DEBUG('OfflineInput.patched AccountInputHandler.__init__')

	aihCls = getattr(AvatarInputHandlerModule, 'AvatarInputHandler', None)
	if aihCls is None or not hasattr(aihCls, 'start'):
		return

	@override(aihCls, 'start')
	def _aih_start(baseFunc, baseSelf, *args, **kwargs):
		try:
			return baseFunc(baseSelf, *args, **kwargs)
		except AttributeError as ex:
			if 'typeDescriptor' in str(ex):
				LOG_DEBUG('OfflineInput.ignore missing typeDescriptor', ex)
				return
			raise

	if hasattr(aihCls, 'setReloading'):
		@override(aihCls, 'setReloading')
		def _aih_setReloading(baseFunc, baseSelf, *args, **kwargs):
			try:
				return baseFunc(baseSelf, *args, **kwargs)
			except AttributeError as ex:
				msg = str(ex)
				if '_FlashGunMarker__reload' in msg:
					LOG_DEBUG('OfflineInput.ignore missing flash reload marker', ex)
					return
				raise

	# Battle UI in old clients expects this callback on account input handler.
	if hasattr(aihCls, '__init__'):
		@override(aihCls, '__init__')
		def _aih_init(baseFunc, baseSelf, *args, **kwargs):
			baseFunc(baseSelf, *args, **kwargs)
			_ensure_postmortem_event(baseSelf)
		LOG_DEBUG('OfflineInput.patched AvatarInputHandler.__init__')


install_game_session_guards()
_install_offline_battle_transport_hooks()
_install_offline_avatar_guards()
_install_offline_input_guards()