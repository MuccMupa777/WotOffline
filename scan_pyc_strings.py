import sys

P = r"C:\Users\User\Downloads\World_of_Tanks"
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

