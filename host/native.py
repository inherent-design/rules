"""Bounded POSIX traces. Every effect stays in a private fixture or loopback connection."""
import base64
import concurrent.futures
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading

def emit(surface, case, facts, decision, **evidence):
    print(json.dumps(dict(v=1, surface=surface, case=case, observed=facts,
                          outcome=dict(decision=decision, **evidence))))

def files(root):
    live, staged = root / "live", root / "stage"
    live.write_bytes(b"A")
    staged.write_bytes(b"B")
    with live.open("rb") as old:
        os.replace(staged, live)
        for case, early, data in [("earlier-open", True, old.read()), ("later-open", False, live.read_bytes())]:
            emit("file", case, dict(opened_before=early, replaced=True), [b"A", b"B"].index(data))
    # The same bytes were approved and checked. A second writer interposes.
    approved = live.read_bytes()
    assert live.read_bytes() == approved
    live.write_bytes(b"C")
    staged.write_bytes(b"D")
    os.replace(staged, live)
    assert live.read_bytes() == b"D"  # Plain rename has no expected-old-content argument.
    live.unlink()
    try:
        os.replace(staged, live)
    except FileNotFoundError:
        assert not live.exists()
    else:
        raise AssertionError("missing stage erroneously published")

def streams():
    script = Path(__file__).resolve().parents[1] / "scripts/host-streams"
    for mode in ["pipe","tty"]:
        code = 'import os,sys; print(sum(os.isatty(i)<<i for i in range(3))); print("diag",file=sys.stderr)'
        r = json.loads(subprocess.check_output([script, "--stdin", mode, "--", sys.executable, "-c", code]))
        assert r["outcome"] == dict(exit_code=0,signal=None,timed_out=False,capture_complete=True)
        assert base64.b64decode(r["observed"]["stderr_b64"]).splitlines() == [b"diag"]
        facts = r["observed"]["isatty"]
        emit("streams", mode, dict(input=facts["stdin"], output=facts["stdout"], diagnostic=facts["stderr"]),
             int(base64.b64decode(r["observed"]["stdout_b64"])))
    r = json.loads(subprocess.check_output([script, "--stdin", "pipe", "--timeout", ".15", "--",
                                           sys.executable, "-c", "import time;time.sleep(10)"]))
    assert r["outcome"]["timed_out"] and r["outcome"]["signal"] == signal.SIGKILL

def process_effects(root):
    # Same command status. Project and incidental log are independent scopes.
    project, log = root / "project", root / "log"
    for write_project in [False, True]:
        for path in [project,log]:
            path.write_bytes(b"before")
        code = ('import sys;from pathlib import Path;Path(sys.argv[1]).write_bytes(b"logged");'
                'sys.argv[3]=="yes" and Path(sys.argv[2]).write_bytes(b"updated");sys.exit(1)')
        result = subprocess.run([sys.executable,"-c",code,log,project,"yes" if write_project else "no"])
        assert result.returncode == 1
        for scope, path in [("project",project),("log",log)]:
            contents = path.read_bytes()
            expected_change = scope == "log" or write_project
            emit("effect", f"failed-{scope}-{write_project}", dict(exit_ok=False,comparable=True,
                 differs=contents != b"before"), 2 if expected_change else 1)

def scheduling():
    entered, go = threading.Event(), threading.Event()
    def worker():
        entered.set()
        if not go.wait(5):
            raise RuntimeError("fixture gate expired")
        return "applied"
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        job = pool.submit(worker)
        try:
            assert entered.wait(2)
            assert not job.cancel()
            try:
                job.result(timeout=.005)
            except concurrent.futures.TimeoutError:
                emit("work", "cancel-request-and-timeout", dict(requested_stop=True, witnessed_end=False),
                     int(job.done()))
            else:
                raise AssertionError("blocked worker returned")
        finally:
            go.set()
        assert job.result(timeout=2) == "applied"
        emit("work", "later-result", dict(requested_stop=True, witnessed_end=True), int(job.done()))

def transport():
    # No shared state is available to the client except its decoded wire data.
    # The server ledger is inspected separately as the test oracle.
    for case, applied, wire in [
        ("commit", True, b"1 7 COMMIT\n"), ("deny", False, b"1 7 DENY\n"),
        ("lost-after", True, b""), ("lost-before", False, b""),
        ("wrong-id", True, b"1 8 COMMIT\n"), ("truncated", True, b"1 7 COM"),
        ("new-version", True, b"2 7 COMMIT\n"),
    ]:
        entries = []
        with socket.socket() as listener:
            listener.bind(("127.0.0.1",0))
            listener.listen(1)
            with socket.create_connection(listener.getsockname(), timeout=2) as client:
                server,_ = listener.accept()
                with server:
                    client.sendall(b"7\n")
                    with server.makefile("rb") as reader:
                        assert reader.readline(32) == b"7\n"
                    if applied:
                        entries.append(7)
                    server.sendall(wire)
                with client.makefile("rb") as reader:
                    raw = reader.readline(32)
        fields = raw.split()
        matched = len(fields) == 3 and fields[1] == b"7"
        complete = (raw.endswith(b"\n") and len(fields) == 3 and fields[0] == b"1"
                    and fields[2] in (b"COMMIT",b"DENY"))
        # The client's complete vocabulary; malformed/unknown rows cannot grant success.
        decision = {b"1 7 COMMIT\n":2,b"1 7 DENY\n":1}.get(raw,0)
        emit("receipt", case, dict(id_matches=matched, complete=complete,
             committed=fields[-1:] == [b"COMMIT"]), decision, server_applied=7 in entries)

def shared_handle(root):
    # A lock held by an open file description survives closing one duplicate.
    with (root / "resource").open("wb") as pool:
        fcntl.flock(pool, fcntl.LOCK_EX)
        with os.fdopen(os.dup(pool.fileno()), "wb") as published:
            pool.close()
            with (root / "resource").open("rb") as next_owner:
                for last_owner in [False, True]:
                    if last_owner:
                        published.close()
                    try:
                        fcntl.flock(next_owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired = True
                    except BlockingIOError:
                        acquired = False
                    emit("reuse", "dup-final-" + str(last_owner), dict(retired=True,
                         sole_pool_owner=last_owner, no_more_uses=True), int(acquired))

def approval():
    # One serialized effect statement combines principal, target, and current basis.
    with sqlite3.connect(":memory:") as db:
        db.executescript("CREATE TABLE grants(actor PRIMARY KEY, active); INSERT INTO grants VALUES('reviewer',1);"
                         "CREATE TABLE files(target PRIMARY KEY, rev, value); INSERT INTO files VALUES('pack',1,'A');")
        for case, actor, target, rev, active in [
            ("wrong-actor","listener","pack",1,1), ("wrong-target","reviewer","other",1,1),
            ("revoked","reviewer","pack",1,0), ("approved","reviewer","pack",1,1),
            ("old-basis","reviewer","pack",1,1),
        ]:
            db.execute("UPDATE grants SET active=?", (active,))
            current = db.execute("SELECT rev FROM files").fetchone()[0]
            result = db.execute("UPDATE files SET value='B',rev=rev+1 WHERE target=? AND rev=? "
                                "AND EXISTS(SELECT 1 FROM grants WHERE actor=? AND active=1)",(target,rev,actor))
            emit("apply_review",case,dict(actor_allowed=actor=="reviewer" and bool(active),
                 target_matches=target=="pack",basis_current=current==rev),result.rowcount)
        assert db.execute("SELECT rev,value FROM files").fetchone() == (2,"B")

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as path:
        files(Path(path))
        process_effects(Path(path))
        shared_handle(Path(path))
    streams()
    scheduling()
    transport()
    approval()
