import json, os, shutil, subprocess, sys, tempfile
PROJECT = os.path.abspath("..")
GAME_FILES = ["engine.py","context.py","locations.py","characters.py","story.py","dialogue.py","deaths.py","main.py","noah.py","music.py"]
tmp = tempfile.mkdtemp(dir=".")
for name in GAME_FILES:
    shutil.copy2(os.path.join(PROJECT, name), os.path.join(tmp, name))
save = {"version":2,"location":"nook","sanity":80,"trust":0,"fear":0,"flags":{},"inventory":[],"visited":["lunuen","nook"],"seen":["lunuen","nook"],"journal":[],"deaths":0,"day":1,"night":False,"connor_line":0,"mika_line":0}
with open(os.path.join(tmp,"save.json"),"w") as f: json.dump(save,f)
patch = os.path.join(tmp,"_patch"); os.makedirs(patch,exist_ok=True)
open(os.path.join(patch,"sitecustomize.py"),"w").write("import time\ntime.sleep=lambda *a,**k:None\n")
env=dict(os.environ); env["PYTHONPATH"]=patch
# stdin: pause, how-to-play pause, then talk noah, leave, q
r=subprocess.run([sys.executable,"main.py","--continue"],cwd=tmp,input="\n\ntalk noah\nleave\nq\n",capture_output=True,text=True,timeout=60,env=env)
print("rc=",r.returncode)
print(r.stdout)
if r.stderr: print("STDERR:",r.stderr[:2000])
