import sys

GAME_SCRIPTS = r"C:\Users\LilYas777\Downloads\World_of_Tanks_0.08.02.00.00_RU_0349_SD\res\scripts"
sys.path.insert(0, GAME_SCRIPTS)

print("sys.path[0] =", sys.path[0])

try:
	import common.arenatype as m
	print("import common.arenatype: OK")
except Exception as e:
	print("import common.arenatype: FAIL", e)
	raise

print("module =", m)
print("has g_cache =", hasattr(m, "g_cache"))
print("cache value =", getattr(m, "g_cache", None))
print("init-like attrs =", [a for a in dir(m) if "init" in a.lower() or "cache" in a.lower()][:100])

