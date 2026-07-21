"""Copy cjscript source files into Crawlab container workspace."""
import io
import os
import subprocess
import tarfile
import pathlib

SRC = pathlib.Path(__file__).resolve().parent
DST = "/root/crawlab_workspace/6a5ed03a41129010b7d17dc0/"
CONTAINER = "cjscript-master-1"

buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w") as tar:
    for item in SRC.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(SRC)
        parts = rel.parts
        # Skip hidden files/dirs and non-essential files
        if any(p.startswith(".") for p in parts):
            continue
        if "_deploy" in str(rel) or rel.name == ".gitignore":
            continue
        if rel.match("__pycache__/*") or rel.match("*.pyc"):
            continue
        tarinfo = tar.gettarinfo(str(item), str(rel))
        with open(item, "rb") as f:
            buf.write(tarinfo.tobuf())
            buf.write(f.read())

buf.seek(0)

proc = subprocess.Popen(
    ["docker", "exec", "-i", CONTAINER, "tar", "xf", "-", "-C", DST],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
out, err = proc.communicate(buf.read())
if proc.returncode == 0:
    print("Deploy OK")
else:
    print("Deploy FAILED:", err.decode())
    print("stdout:", out.decode())
