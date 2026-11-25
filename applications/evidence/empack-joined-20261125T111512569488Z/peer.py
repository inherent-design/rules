"""Owned native NDJSON peer with bounded input, output, and actual retirement."""
import json,os,select,signal,subprocess,time
class Peer:
 def __init__(self,program):
  self.process=subprocess.Popen([str(program)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);self.buffer=b'';self.frames=[];self.closed=None
 def call(self,request):
  packet=json.dumps(dict(schema=1,**request),ensure_ascii=False,separators=(',',':')).encode();assert len(packet)<=65536;self.process.stdin.write(packet+b'\n');self.process.stdin.flush();deadline=time.monotonic()+10
  while b'\n'not in self.buffer:
   remaining=deadline-time.monotonic();assert remaining>0,'Native protocol timeout'
   ready,_,_=select.select([self.process.stdout],[],[],remaining);assert ready,'Native protocol timeout'
   b=os.read(self.process.stdout.fileno(),65536);assert b,'Native protocol EOF';self.buffer+=b;assert len(self.buffer)<=65537
  raw,self.buffer=self.buffer.split(b'\n',1);value=json.loads(raw);self.frames.append(dict(request=packet.hex(),response=raw.hex()));return value
 def close(self):
  if self.closed is not None:return self.closed
  self.process.stdin.close()
  try:self.process.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=5)
  stderr=self.process.stderr.read();tail=self.process.stdout.read();assert not tail and not self.buffer
  try:os.killpg(self.process.pid,0)
  except ProcessLookupError:absent=True
  else:absent=False
  self.closed=dict(pid=self.process.pid,exitCode=self.process.returncode,groupAbsent=absent,stderr=stderr.hex());return self.closed
