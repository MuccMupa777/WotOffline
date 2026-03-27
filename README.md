🚀 Major Refactor: Offline Architecture Overhaul
🔧 Core Architecture
Replaced monolithic request handling (requests.pyc) with a modular command processing pipeline:
Introduced CommandRouter for centralized command dispatch
Added command_handlers for explicit command logic separation
Decoupled transport layer (FakeServer) from business logic
Implemented structured request lifecycle:
Unified RequestResult handling
Normalized response flow via onCmdResponse / onCmdResponseExt
⚔️ Offline Battle System (New)
🆕 Added full offline battle bootstrap system
Introduced offline_battle.py:
Handles enqueue → arena → avatar transition
Simulates server-side matchmaking flow
Added offline_battle_stack.py:
Builds battle context:
teams
vehicles
arena metadata
Supports real VehicleTypeDescriptor fallback
Implemented:
onEnqueued
onArenaCreated
battle entry orchestration
🧠 Battle Context & Arena Simulation
Added dynamic arena type resolution:
_resolve_real_arena_type()
fallback to safe stub if unavailable
Implemented _OfflineArenaStub:
Prevents crashes on missing arena data
Provides safe defaults for:
minimap
events
vehicle access
Introduced _OfflineVehicleStub for safe avatar fallback
🔌 Transport & Protocol Layer
Reworked FakeServer:
Integrated with CommandRouter
Added full support for:
doCmdInt*
doCmdIntArr
doCmdIntArrStrArr
Added routing abstraction:
Command resolution via numeric ID + name
Collision-safe handling of legacy AccountCommands
🧩 Command Handling Improvements
Replaced implicit request map (BASE_REQUESTS) with explicit handlers:
handle_enqueue_random
handle_prebattle
handle_sync*
Added collision-safe handler:
handle_stats_or_enqueue_collision
Resolves overlapping command IDs in legacy builds
Introduced fallback handler (handle_unknown)
Prevents client crashes on unimplemented commands
🛡️ Session & Restrictions Bypass
Added session_guards.py:
Disabled:
captcha
parental control
session limits
Forced battle access:
isAccountAllowedToBattle → True
canJoinBattle → True
🧠 PlayerAccount Hooking (Major)
Overrode core PlayerAccount behavior:
__init__ → inject offline state
__getattribute__ → dynamic overrides:
vehicleTypeDescriptor
playerVehicleID
arena
server/cell/base
Implemented fake server binding:
baseSelf.fakeServer = FakeServer()
Added offline identity:
nickname
server settings
offline flags
🔁 Matchmaking Interception
🆕 Multi-layer enqueue interception
Hooked:
PlayerAccount.__doCmd
enqueueRandom
alternative enqueue methods (auto-detected)
Ensures:
battle trigger works across different client builds
🎮 Avatar & World Stability Layer
Added _install_offline_avatar_guards():
stabilizes onEnterWorld
protects against missing vehicle/entity state
Implemented:
safe vehicle attachment
fallback for missing model errors
Patched:
onLeaveWorld
getVehicleAttached
🎮 Input System Stabilization
Patched:
AccountInputHandler
AvatarInputHandler
Added safeguards against:
missing typeDescriptor
missing reload markers
🌍 World & Entity Control
Overrode BigWorld.clearEntitiesAndSpaces:
prevents world reset in offline mode
Controlled teardown behavior:
prevents unintended session destruction
🏪 Hangar & Economy
Implemented full offline shop:
custom pricing
unlimited resources
free XP conversion
Overrode:
Shop.__onSyncComplete
Added:
offline inventory generation
full tech tree unlock support
⏱️ Time & Session Emulation
Overrode:
server time
session tracking
weekly playtime
Ensures:
UI consistency
no session lockouts
🔌 Connection Layer
Overrode BigWorld.connect:
bypass real server
spawn local Account entity
Modified login flow:
auto-connect to offline server
🧰 Dev & Tooling
Added:
build_mod.py (auto compile & deploy)
inspect_arenatype.py (reverse tools)
scan_pyc_strings.py (binary inspection)
Added CameraNode polyfill:
ensures mod loader compatibility
⚠️ Breaking Changes
Removed legacy requests.pyc architecture
Replaced implicit command handling with explicit routing
Introduced multiple hook layers (Account, Avatar, BigWorld)
Battle flow is no longer passive — now actively simulated
🧠 Summary
This update transforms the project from:
❌ Simple offline hangar mod
into:
✅ Fully modular offline runtime with battle simulation capabilities
Credits: https://github.com/SigmaTel71/mod_offhangar_legacy by SigmaTel71 and https://github.com/IzeBerg
