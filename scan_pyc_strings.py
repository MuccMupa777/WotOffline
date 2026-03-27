import sys

P = r"C:\Users\LilYas777\Downloads\World_of_Tanks_0.08.02.00.00_RU_0349_SD\res\scripts\common\arenatype.pyc"
b = open(P, "rb").read()

subs = [
	"g_cache", "gCache", "cache",
	"init", "initialize", "load", "read",
	"getArena", "getBy", "geometry", "geometryName",
	"teamBasePositions", "teamBasePosition", "basePositions",
	"minimap", "positions",
	"ResMgr", "DataSection", "openSection",
]

for s in subs:
	if s in b:
		print("HIT", s)
print("len", len(b))

