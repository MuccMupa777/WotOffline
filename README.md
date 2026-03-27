# 🛠️ WotOffline — Offline Runtime for World of Tanks 0.8.2

WotOffline is an experimental offline runtime for World of Tanks 0.8.2.

The project replaces client-server interaction with a fully local emulation layer, enabling:
- offline hangar functionality
- fake account environment
- partial battle simulation infrastructure

---

## 🚀 Features

### 🏠 Offline Hangar
- Full account emulation (credits, gold, XP)
- Offline shop and inventory generation
- All vehicles available
- No server dependency

### ⚙️ Server Emulation
- FakeServer replacing Wargaming backend
- Command routing via `CommandRouter`
- Full support for `AccountCommands`

### ⚔️ Battle Infrastructure (Work in Progress)
- Enqueue interception
- Offline battle bootstrap
- Arena context generation
- Avatar and entity stabilization

> ⚠️ Full battle gameplay is NOT implemented yet.  
> The current goal is infrastructure and runtime simulation.

---

## 🧠 Architecture Overview

The project is structured as a layered offline runtime:

```
Client (WoT)
   ↓
FakeServer (transport layer)
   ↓
CommandRouter (protocol layer)
   ↓
Command Handlers (logic layer)
   ↓
Offline Battle System (runtime layer)
```

### Key Modules

- `server.py` — transport layer (FakeServer)
- `command_router.py` — command dispatch
- `command_handlers.py` — command logic
- `offline_battle.py` — battle orchestration
- `offline_battle_stack.py` — battle context builder
- `mod_offhangar.py` — hooks and integration layer

---

## 📦 Installation

1. Copy compiled scripts into:
```
res_mods/0.8.2/scripts/client/gui/mods/
```

2. Launch the game.

3. The client will automatically connect to the offline server.

---

## ⚠️ Important Notes

- This project modifies core client behavior.
- It relies on reverse engineering of the BigWorld engine.
- Stability may vary depending on client build.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.

You are free to:
- Use the software
- Modify the source code
- Distribute copies

Under the following conditions:
- You must disclose source code
- You must keep the same license (GPLv3)
- You must include copyright notices

See the `LICENSE` file for full details.

---

## 📚 Credits

This project is based on prior work:

- **SigmaTel71 / DrWeb7_1**  
  https://github.com/SigmaTel71/mod_offhangar_legacy

- **IzeBerg**  
  Original implementation of the offhangar concept (ported from newer WoT versions)

This repository extends and refactors their work into a modular offline runtime system.

---

## ⚠️ Disclaimer

This project is **not affiliated with Wargaming.net**.

All trademarks and game assets belong to their respective owners.

This software is provided **"as is"**, without warranty of any kind.

Use at your own risk.

---

## 🎯 Project Status

🟡 Active development

Current focus:
- battle runtime infrastructure
- stable arena initialization
- avatar lifecycle handling

Future goals:
- full offline battle simulation
- entity update loop
- AI or scripted battle behavior

---

## 🧪 Purpose

This project is intended for:
- research
- reverse engineering
- educational purposes

---

## 💬 Contributing

Contributions, experiments and ideas are welcome.

---

## 🧠 Summary

WorOffline transforms World of Tanks from:

❌ Online-only client  

into  

✅ Modular offline runtime with server emulation and battle simulation foundations
