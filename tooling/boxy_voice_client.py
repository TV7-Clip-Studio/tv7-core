"""One-owner stdio MCP voice session. No inference retries or private defaults."""
import argparse,json,os,selectors,signal,subprocess,tempfile,time
from pathlib import Path

class VoiceClient:
 def __init__(self,command,timeout=20):
  if not isinstance(command,list) or not command or not all(isinstance(x,str) and x and '\x00' not in x for x in command):raise ValueError('Expected trusted launch command')
  self.timeout=timeout;self.counter=0;self.buffer=b'';self.log=tempfile.TemporaryFile()
  try:self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,start_new_session=True)
  except BaseException:self.log.close();raise
  self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ)
  try:
   self.server=self.request('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'tv7-voice-consumer','version':'0.1.0'}})
   self.process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n');self.process.stdin.flush()
  except BaseException:self.close();raise
 def request(self,method,params):
  self.counter+=1;identifier=self.counter;payload=json.dumps({'jsonrpc':'2.0','id':identifier,'method':method,'params':params}).encode()+b'\n'
  if len(payload)>65536:raise ValueError('Request exceeds server limit')
  self.process.stdin.write(payload);self.process.stdin.flush();deadline=time.monotonic()+self.timeout
  while True:
   if b'\n' in self.buffer:
    line,self.buffer=self.buffer.split(b'\n',1);message=json.loads(line)
    if not isinstance(message,dict) or message.get('id')!=identifier:raise ValueError('Mismatched MCP response')
    if 'error' in message:raise ValueError('MCP error: '+str(message['error']))
    if 'result' not in message:raise ValueError('Missing MCP result')
    return message['result']
   remaining=deadline-time.monotonic()
   if remaining<=0 or not self.selector.select(remaining):raise TimeoutError('Voice response timed out; reconcile jobs before resubmitting')
   chunk=os.read(self.process.stdout.fileno(),65536)
   if not chunk:raise RuntimeError('Voice process disconnected')
   self.buffer+=chunk
   if len(self.buffer)>1048576:raise ValueError('Oversized MCP response')
 def call(self,name,arguments):
  result=self.request('tools/call',{'name':name,'arguments':arguments})
  if result.get('isError'):raise ValueError('Voice tool error: '+str(result.get('content')))
  texts=[x['text'] for x in result.get('content',[]) if x.get('type')=='text']
  if len(texts)!=1:raise ValueError('Expected one JSON tool result')
  return json.loads(texts[0])
 def check(self):
  names={x['name'] for x in self.request('tools/list',{}).get('tools',[])}
  if not {'list_voice_identities','synthesize_voice','convert_voice','get_voice_job','cancel_voice_job'}<=names:raise ValueError('Missing voice tools')
  return {'server':self.server['serverInfo'],'tools':sorted(names),'identities':self.call('list_voice_identities',{}),'inference_submitted':False}
 def close(self):
  if self.process.stdin and not self.process.stdin.closed:self.process.stdin.close()
  try:self.process.wait(timeout=5)
  except subprocess.TimeoutExpired:
   os.killpg(self.process.pid,signal.SIGTERM)
   try:self.process.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(self.process.pid,signal.SIGKILL);self.process.wait()
  self.selector.close()
  if self.process.stdout:self.process.stdout.close()
  self.log.close()
 def __enter__(self):return self
 def __exit__(self,*args):self.close()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);args=p.parse_args()
 with VoiceClient(json.loads(args.config.read_text())['command']) as c:print(json.dumps(c.check(),indent=2))
if __name__=='__main__':main()
