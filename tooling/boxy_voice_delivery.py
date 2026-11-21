"""Consumer-side integrity verification; never equates delivery with listening approval."""
import hashlib,json,wave
from pathlib import Path

def verify(directory,expected_request_sha256,expected_delivery_sha256=None):
 root=Path(directory).resolve(strict=True)
 def read(name):
  if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe delivery path')
  p=(root/name).resolve(strict=True)
  if not p.is_relative_to(root) or not p.is_file():raise ValueError('Delivery artifact escapes root')
  return p.read_bytes()
 def digest(body):return hashlib.sha256(body).hexdigest()
 body=read('delivery.json');d=json.loads(body)
 if expected_delivery_sha256 is not None and digest(body)!=expected_delivery_sha256:raise ValueError('Trusted delivery checksum mismatch')
 if read('delivery.sha256').decode()!=digest(body)+'  delivery.json\n':raise ValueError('Delivery checksum mismatch')
 request=read('request.json');q=json.loads(request)
 if digest(request)!=expected_request_sha256 or d['request_sha256']!=expected_request_sha256:raise ValueError('Request identity mismatch')
 if d['schema']!='boxy-lady.audition-delivery.v1' or q['schema']!='boxy-lady.audition-request.v1':raise ValueError('Unsupported voice contract')
 if d.get('submission_owner')!=q.get('submission_owner') or d.get('retry_policy')!='none' or q.get('retry_policy')!='none' or d.get('scope')!='audition-only' or q.get('scope')!='audition-only':raise ValueError('Invalid submission ownership or scope')
 if d['promotion_authorized'] is not False or d['listening_acceptance'] is not None:raise ValueError('Audition cannot claim promotion/acceptance')
 if d['request_id']!=q['request_id'] or d['passages']!=q['passages']:raise ValueError('Request metadata mismatch')
 artifacts={}
 for artifact in d['artifacts']:
  if artifact['path'] in artifacts:raise ValueError('Duplicate artifact')
  value=read(artifact['path'])
  if digest(value)!=artifact['sha256'] or len(value)!=artifact['bytes']:raise ValueError('Artifact integrity failed')
  artifacts[artifact['path']]=artifact
 passages={p['id']:p for p in q['passages']}
 for p in passages.values():
  if digest(p['text'].encode())!=p['text_sha256']:raise ValueError('Passage text changed')
 if [x['id'] for x in d['items']]!=[x['id'] for x in q['items']]:raise ValueError('Delivery item set changed')
 for row,item in zip(d['items'],q['items']):
  if any(row[k]!=item[k] for k in ('passage_id','role','identity','performance','treatment')):raise ValueError('Item metadata changed')
  if row['status'] not in ('complete','failed','blocked') or row['listening_acceptance'] is not None:raise ValueError('Invalid item status')
  if row['status']!='complete':continue
  for field in ('audio','receipt'):
   if artifacts.get(row[field]['path'])!=row[field]:raise ValueError('Missing item artifact')
  take=json.loads(read(row['receipt']['path']));p=passages[row['passage_id']]
  if take['request']['text']!=p['text'] or take['speech_sha256']!=row['audio']['sha256']:raise ValueError('Audio/caption receipt mismatch')
  voice=take['voice']
  if voice['id']!=item['identity']['id'] or voice.get('identity_version',voice.get('version'))!=item['identity']['version']:raise ValueError('Voice identity changed')
  import io
  with wave.open(io.BytesIO(read(row['audio']['path']))) as w:
   if w.getnchannels()!=1 or w.getsampwidth()!=2 or not 16000<=w.getframerate()<=48000:raise ValueError('Unsupported delivered PCM')
   if abs(w.getnframes()/w.getframerate()-take['duration'])>.001:raise ValueError('Duration mismatch')
 complete=sum(r['status']=='complete' for r in d['items']);expected='complete' if complete==len(d['items']) else 'partial'
 if d['status']!=expected:raise ValueError('Partial delivery mislabelled')
 return {'request_id':d['request_id'],'status':d['status'],'complete':complete,'items':len(d['items']),'listening_acceptance':None,'promotion_authorized':False}

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--delivery-sha256',required=True);a=p.parse_args()
 print(json.dumps(verify(a.directory,a.request_sha256,a.delivery_sha256),indent=2))
