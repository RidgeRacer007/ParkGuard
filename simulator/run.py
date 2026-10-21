import argparse, json, time, urllib.request, io, os
try:
 from PIL import Image, ImageDraw
except ImportError: Image=None
SCENARIOS={'normal':[(80,60,24,48,False)],'exhaust':[(200,100,28,44,False),(480,130,34,38,False),(620,150,38,33,False)],'firecracker_smoke':[(150,70,28,46,False),(280,90,34,33,True)],'cng_leak':[(180,400,25,48,False),(250,850,31,44,False)],'ev_fault':[(180,130,28,42,False),(280,150,52,32,False),(380,180,70,25,False)],'vehicle_fire':[(350,180,44,33,True),(650,270,76,22,True)],'explosion':[(200,100,24,45,False),(850,620,92,19,True)],'unwarranted_fire':[(750,300,85,20,True)],'spreading_fire':[(700,300,78,20,True),(780,350,84,18,True)],'network_outage':[(700,300,78,20,True),(780,350,84,18,True)]}
def jpg(smoke):
 if Image is None:return None
 im=Image.new('RGB',(320,180),(30,35,40));d=ImageDraw.Draw(im)
 if smoke:
  for i in range(7):d.ellipse((80+i*12,30+i*4,180+i*11,120+i*4),fill=(100+i*10,90+i*8,80))
 else:d.rectangle((0,135,320,180),fill=(65,65,65))
 out=io.BytesIO();im.save(out,'JPEG');return out.getvalue()
def send(url,data,key):
 req=urllib.request.Request(url+'/api/readings',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Device-Key':key},method='POST')
 with urllib.request.urlopen(req,timeout=3) as r:return json.load(r)
def device_key(node):
 raw=os.getenv('PARKGUARD_DEVICE_KEYS','')
 if not raw:
  try: raw=next(x.split('=',1)[1] for x in open('.env',encoding='utf-8') if x.startswith('PARKGUARD_DEVICE_KEYS='))
  except (OSError,StopIteration): raw=''
 try:return json.loads(raw).get(node,'demo-key-change-me') if raw else 'demo-key-change-me'
 except json.JSONDecodeError:return 'demo-key-change-me'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scenario',choices=SCENARIOS,default='vehicle_fire');ap.add_argument('--api',default='http://localhost:8000');ap.add_argument('--node',default='demo-node');ap.add_argument('--delay',type=float,default=.8);a=ap.parse_args();queue=[]
 for i,(g,m,t,h,sm) in enumerate(SCENARIOS[a.scenario]):
  node='bay-a' if a.scenario=='spreading_fire' and i else a.node
  row={'node_id':node,'mq135':g,'mq4':m,'temperature':t,'humidity':h,'duration_s':i*3,'event_window':False,'sensor_alarm':False,'smoke_or_flame':sm}
  if a.scenario=='network_outage':queue.append(row);print('outage: buffered',node);continue
  try:
   key=device_key(node);print(json.dumps(send(a.api,row,key),indent=2));img=jpg(sm)
   if img:
    b='parkguard-boundary';body=b'--'+b.encode()+b'\r\nContent-Disposition: form-data; name="file"; filename="sample.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'+img+b'\r\n--'+b.encode()+b'--\r\n';req=urllib.request.Request(a.api+'/api/photos/'+node,data=body,headers={'Content-Type':'multipart/form-data; boundary='+b,'X-Device-Key':key},method='POST');urllib.request.urlopen(req,timeout=4).read()
  except Exception as e:print('send failed; buffered for retry:',e);queue.append(row)
  time.sleep(a.delay)
 if queue:
  print('reconnecting; emergency events first');queue.sort(key=lambda x:not x['smoke_or_flame'])
  for row in queue:
   try:print('resent',row['node_id'],send(a.api,row,device_key(row['node_id'])).get('escalation'))
   except Exception as e:print('retry still unavailable:',e)
if __name__=='__main__':main()
