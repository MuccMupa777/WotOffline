# 🚀 Major Refactor: Offline Architecture Overhaul

## 🔧 Core Architecture
- Replaced monolithic request handling (`requests.pyc`)
- Introduced modular pipeline:
  - `CommandRouter` — centralized dispatch
  - `command_handlers` — separated logic
  - `FakeServer` — transport only
- Unified request lifecycle (`RequestResult`)
- Normalized responses (`onCmdResponse / onCmdResponseExt`)

---

## ⚔️ Offline Battle System (New)
- Added `offline_battle.py`
  - Handles: enqueue → arena → avatar
- Added `offline_battle_stack.py`
  - Builds battle context:
    - teams
    - vehicles
    - arena metadata
- Implemented:
  - `onEnqueued`
  - `onArenaCreated`

---

## 🧠 Battle Context & Arena Simulation
- Added `_resolve_real_arena_type()`
- Implemented `_OfflineArenaStub`
  - prevents crashes
  - provides safe defaults
- Added `_OfflineVehicleStub`

---

## 🔌 Transport & Protocol
- Reworked `FakeServer`
- Integrated with `CommandRouter`
- Added support for:
  - `doCmdInt*`
  - array-based commands
- Added collision-safe command handling

---

## 🧩 Command Handling
- Replaced `BASE_REQUESTS` with explicit handlers
- Added:
  - `handle_enqueue_random`
  - `handle_prebattle`
  - `handle_sync*`
- Added collision handler:
  - `handle_stats_or_enqueue_collision`
- Added fallback:
  - `handle_unknown`

---

## 🛡️ Session & Restrictions Bypass
- Disabled:
  - captcha
  - parental control
  - session limits
- Forced:
  - `isAccountAllowedToBattle = True`
  - `canJoinBattle = True`

---

## 🧠 PlayerAccount Hooking
- Overrode:
  - `__init__`
  - `__getattribute__`
- Injected:
  - fake server
  - offline identity
  - dynamic vehicle & arena handling

---

## 🔁 Matchmaking Interception
- Hooked:
  - `__doCmd`
  - `enqueueRandom`
  - alternative enqueue methods
- Ensures compatibility across client builds

---

## 🎮 Avatar & World Stability
- Added avatar guards:
  - `onEnterWorld`
  - `onLeaveWorld`
- Safe vehicle fallback
- Crash protection for missing data

---

## 🎮 Input System Stabilization
- Patched:
  - `AccountInputHandler`
  - `AvatarInputHandler`
- Fixed missing:
  - `typeDescriptor`
  - reload markers

---

## 🌍 World Control
- Overrode:
  - `BigWorld.clearEntitiesAndSpaces`
- Prevents unwanted world reset

---

## 🏪 Hangar & Economy
- Implemented offline shop
- Overrode `Shop.__onSyncComplete`
- Added:
  - inventory generation
  - full unlock support

---

## ⏱️ Time & Session Emulation
- Overrode:
  - server time
  - session logic
- Fixed UI consistency

---

## 🔌 Connection Layer
- Overrode `BigWorld.connect`
- Auto-login to offline server
- Local Account entity creation

---

## 🧰 Dev Tools
- Added:
  - `build_mod.py`
  - `inspect_arenatype.py`
  - `scan_pyc_strings.py`
- Added `CameraNode` loader polyfill

---

## ⚠️ Breaking Changes
- Removed `requests.pyc`
- Replaced request handling system
- Introduced full hook-based architecture
- Battle flow now actively simulated

---

## 🧠 Summary
This update transforms the project from:

❌ Simple offline hangar mod  
➡️  
✅ Modular offline runtime with battle simulation
