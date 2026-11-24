"""Private archive fixtures exercise bounded reads and descriptor-relative confinement."""
import errno
import io
import json
import os
from pathlib import Path
import platform
import tempfile
import zipfile

def emit(case,identity,covered,decision,**extra):
    print(json.dumps(dict(v=2,profile=platform.system().lower()+"-"+platform.machine(),
        app="archive-candidate",feature="bounded-archive",operationId=case,
        target="fixture/extraction-root",basis="0",predicate="consume",
        observed=dict(identity=identity,compatible=True,covered=covered),
        outcome=dict(decision=int(decision),**extra))))

def bounded(stream,limit):
    parts=[];remaining=limit+1
    while remaining:
        chunk=stream.read(min(1024,remaining))
        if not chunk:break
        parts.append(chunk);remaining-=len(chunk)
    result=b"".join(parts)
    if len(result)>limit:raise ValueError("entry exceeds admitted bytes")
    return result

def relative_file(root,name):
    # This deliberately narrow POSIX adapter supports one path component.
    # Nested paths require opening each parent directory under the same rule.
    if name in ("",".","..") or "/" in name or "\\" in name or "\0" in name:
        raise ValueError("unsupported portable path")
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=root)
    return os.fdopen(fd,"wb")

with tempfile.TemporaryDirectory(prefix="rules-archive-") as path:
    root=Path(path);out=root/"output";out.mkdir()
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,"w",compression=zipfile.ZIP_DEFLATED) as writer:
        writer.writestr("good",b"verified")
        writer.writestr("../escape",b"outside")
        writer.writestr("large",b"A"*4096)
    dirfd=os.open(out,os.O_RDONLY|os.O_DIRECTORY)
    try:
        with zipfile.ZipFile(io.BytesIO(raw.getvalue())) as archive:
            for name in ("good","../escape","large"):
                safe=name=="good" or name=="large"
                fits=name!="large"
                try:
                    with archive.open(name) as entry:
                        data=bounded(entry,32)
                    with relative_file(dirfd,name) as target:
                        target.write(data)
                    applied=True
                except ValueError:
                    applied=False
                emit(name,safe,fits,applied)
        assert (out/"good").read_bytes()==b"verified"
        assert not (root/"escape").exists() and not (out/"large").exists()
        # An approved lexical name can still refer through a native symlink.
        outside=root/"sentinel";outside.write_bytes(b"keep")
        (out/"alias").symlink_to(outside)
        try:
            with relative_file(dirfd,"alias") as target:target.write(b"overwrite")
            raise AssertionError("alias unexpectedly opened")
        except OSError as error:
            if error.errno not in (errno.EEXIST,errno.ELOOP):raise
        assert outside.read_bytes()==b"keep"
        emit("native-alias",False,True,False,protectedBytes=outside.read_text())
    finally:os.close(dirfd)
