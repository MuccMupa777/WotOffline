import os
import py_compile
import shutil
import sys

SRC = r"c:\Users\LilYas777\NoviyDesigner\scripts\client"
DST = r"c:\Users\LilYas777\NoviyDesigner\compilated\res_mods\0.8.2\scripts\client"

copied = 0
compiled = 0

for root, dirs, files in os.walk(SRC):
	rel = os.path.relpath(root, SRC)
	outdir = os.path.join(DST, rel) if rel != "." else DST
	if not os.path.isdir(outdir):
		os.makedirs(outdir)
	for fn in files:
		if not fn.lower().endswith(".py"):
			continue
		src_path = os.path.join(root, fn)
		dst_path = os.path.join(outdir, fn)
		shutil.copyfile(src_path, dst_path)
		copied += 1
		py_compile.compile(src_path, cfile=dst_path + "c", dfile=src_path, doraise=True)
		compiled += 1

print("COPIED", copied)
print("COMPILED", compiled)

