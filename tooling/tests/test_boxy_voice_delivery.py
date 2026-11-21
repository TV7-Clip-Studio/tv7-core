import hashlib,json,tempfile,unittest
from pathlib import Path
from boxy_voice_delivery import verify
class DeliveryTests(unittest.TestCase):
 def fixture(self,root):
  p={'id':'short','text':'Easy.','text_sha256':hashlib.sha256(b'Easy.').hexdigest()};i={'id':'native-short','passage_id':'short','role':'candidate','identity':{'id':'native','version':1},'performance':{'kind':'unresolved'},'treatment':{'kind':'dry','version':1}}
  q={'schema':'boxy-lady.audition-request.v1','request_id':'fixture','submission_owner':'fixture','retry_policy':'none','scope':'audition-only','passages':[p],'items':[i]};request=json.dumps(q).encode();(root/'request.json').write_bytes(request);sha=hashlib.sha256(request).hexdigest()
  d={'schema':'boxy-lady.audition-delivery.v1','request_id':'fixture','submission_owner':'fixture','retry_policy':'none','scope':'audition-only','request_sha256':sha,'passages':[p],'items':[{**i,'status':'blocked','listening_acceptance':None}],'artifacts':[{'path':'request.json','sha256':sha,'bytes':len(request)}],'promotion_authorized':False,'listening_acceptance':None,'status':'partial'}
  self.save(root,d);return d,sha
 def save(self,r,d):
  body=json.dumps(d).encode();(r/'delivery.json').write_bytes(body);(r/'delivery.sha256').write_text(hashlib.sha256(body).hexdigest()+'  delivery.json\n')
 def test_partial_remains_partial(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d,sha=self.fixture(r);self.assertEqual(verify(r,sha)['status'],'partial')
   d['status']='complete';self.save(r,d)
   with self.assertRaises(ValueError):verify(r,sha)
 def test_integrity_paths_and_request_binding(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d,sha=self.fixture(r)
   with self.assertRaises(ValueError):verify(r,'0'*64)
   d['artifacts'][0]['path']='../outside';self.save(r,d)
   with self.assertRaises(ValueError):verify(r,sha)
 def test_complete_audio_receipt_and_tampering(self):
  import io,wave,struct
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d,sha=self.fixture(r);d['items'][0]['status']='complete';d['status']='complete'
   b=io.BytesIO()
   with wave.open(b,'w') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(struct.pack('<h',1000)*24000)
   audio=b.getvalue();audio_sha=hashlib.sha256(audio).hexdigest();take={'voice':{'id':'native','identity_version':1},'request':{'text':'Easy.'},'speech_sha256':audio_sha,'duration':1.}
   for key,name,body in [('audio','take.wav',audio),('receipt','take.json',json.dumps(take).encode())]:
    (r/name).write_bytes(body);record={'path':name,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)};d['artifacts'].append(record);d['items'][0][key]=record
   self.save(r,d);self.assertEqual(verify(r,sha)['complete'],1)
   with self.assertRaisesRegex(ValueError,'Trusted'):verify(r,sha,'0'*64)
   (r/'take.wav').write_bytes(b'corrupt')
   with self.assertRaisesRegex(ValueError,'integrity'):verify(r,sha)
