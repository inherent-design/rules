"""Native transactional lifecycle witnesses in an owned temporary root."""
from pathlib import Path
import concurrent.futures
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
import threading

profile=platform.system().lower()+"-"+platform.machine()
counter=0
def emit(feature,predicate,facts,decision,basis="0",**extra):
    global counter
    counter+=1
    print(json.dumps(dict(v=2,profile=profile,app="native-candidate",feature=feature,
        operationId=f"{feature}-{counter}",target="fixture/project",basis=basis,predicate=predicate,
        observed=facts,outcome=dict(decision=int(decision),**extra))))

def database(root):
    file=root/"state.sqlite"
    with sqlite3.connect(file) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("CREATE TABLE assets(id TEXT PRIMARY KEY, bytes BLOB);"
            "CREATE TABLE roots(owner TEXT,id TEXT,FOREIGN KEY(id) REFERENCES assets(id));"
            "CREATE TABLE project(rev TEXT); INSERT INTO project VALUES('0');")
        db.execute("INSERT INTO assets VALUES('A',?)",(b"alpha",))
    def save(expected,asset):
        with sqlite3.connect(file,timeout=3) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            actual=db.execute("SELECT rev FROM project").fetchone()[0]
            known=db.execute("SELECT 1 FROM assets WHERE id=?",(asset,)).fetchone() is not None
            if expected!=actual or not known:
                return False,actual,known
            db.execute("UPDATE project SET rev=?",(str(int(actual)+1),))
            db.execute("DELETE FROM roots WHERE owner='saved'")
            db.execute("INSERT INTO roots VALUES('saved',?)",(asset,))
            return True,actual,known
    result,actual,known=save("0","missing")
    emit("missing-assets","draft",dict(retained=known,current=actual=="0",writable=True),result)
    with concurrent.futures.ThreadPoolExecutor(2) as executor:
        # Both callers supply base zero. BEGIN IMMEDIATE serializes their reads.
        outcomes=list(executor.map(lambda _:save("0","A"),range(2)))
    assert sum(x[0] for x in outcomes)==1
    for i,(result,actual,known) in enumerate(outcomes):
        emit("competing-save-"+str(i),"draft",dict(retained=known,current=actual=="0",writable=True),result)
    with sqlite3.connect(file) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("INSERT INTO assets VALUES('B',?)",(b"beta",))
        for owner in ("undo","plan"):
            db.execute("INSERT INTO roots VALUES(?,'B')",(owner,))
        db.commit()
        for operation in ("hold-undo","hold-plan","release-all"):
            if operation=="hold-plan":db.execute("DELETE FROM roots WHERE owner='undo'")
            if operation=="release-all":db.execute("DELETE FROM roots WHERE owner='plan'")
            roots={row[0] for row in db.execute("SELECT owner FROM roots WHERE id='B'")}
            try:
                db.execute("DELETE FROM assets WHERE id='B'")
                reclaimed=True
            except sqlite3.IntegrityError:
                reclaimed=False
            emit(operation,"collect",dict(covered=True,saved="saved" in roots,undo="undo" in roots,plan="plan" in roots,active=False),reclaimed)
        assert db.execute("SELECT COUNT(*) FROM assets").fetchone()[0]==1
    # A plain file write and later metadata commit are distinct effects.
    (root/"orphan").write_bytes(b"retained-but-unsaved")
    with sqlite3.connect(file) as db:
        assert db.execute("SELECT rev FROM project").fetchone()[0]=="1"
    emit("bytes-before-metadata","save_status",dict(confirmed=False,newer_edit=False),2,orphanBytes=True)

def editor(root):
    entered,release=threading.Event(),threading.Event()
    current=saved=1
    file=root/"document"
    file.write_text("old")
    captured=current
    def write():
        entered.set()
        if not release.wait(3):raise RuntimeError("save gate expired")
        file.write_text("revision-1")
        return captured
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        job=pool.submit(write)
        try:
            assert entered.wait(2)
            current+=1
        finally:release.set()
        saved=job.result(timeout=2)
    assert file.read_text()=="revision-1" and current==2 and saved==1
    emit("edit-during-save","save_status",dict(confirmed=True,newer_edit=current!=saved),int(current!=saved))

def process(root):
    # Window close is modeled by the supervisor closing admission. Only the
    # child's receipt and actual wait establish its end. No human UI is used.
    script=("import pathlib,sys;"
            "pathlib.Path(sys.argv[1]).write_text('started');"
            "sys.stdin.buffer.read(1);pathlib.Path(sys.argv[2]).write_text('finished')")
    worker=subprocess.Popen([sys.executable,"-c",script,str(root/"entered"),str(root/"finished")],stdin=subprocess.PIPE)
    try:
        import time
        deadline=time.monotonic()+3
        while not (root/"entered").exists():
            if worker.poll() is not None or time.monotonic()>=deadline:raise RuntimeError("child did not start")
            time.sleep(.002)
        emit("close-supervisor","retire",dict(closed=True,end_confirmed=False),int(worker.poll() is not None))
        worker.stdin.write(b"x");worker.stdin.close()
        worker.wait(timeout=3)
        assert worker.returncode==0 and (root/"finished").read_text()=="finished"
        emit("child-final-receipt","retire",dict(closed=True,end_confirmed=True),int(worker.poll() is not None))
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait()

def provenance(root):
    for name in ("profile-A","profile-B"):
        (root/name).mkdir()
        (root/name/"config").write_text(name)
    requested=("profile-A","config")
    observed=("profile-B","config")
    assert requested[1]==observed[1]
    emit("same-display-different-owner","consume",dict(identity=requested==observed,compatible=True,covered=True),0)
    correct=(root/requested[0]/requested[1]).read_text()=="profile-A"
    emit("qualified-owner","consume",dict(identity=correct,compatible=True,covered=True),1)
    # Browser/native consumers can preserve drafts even when execution is unavailable.
    emit("missing-process-capability","execute",dict(capable=False,complete=True,approved=True),0)

if __name__=="__main__":
    with tempfile.TemporaryDirectory(prefix="rules-lifecycle-") as path:
        root=Path(path)
        database(root);editor(root);process(root);provenance(root)
