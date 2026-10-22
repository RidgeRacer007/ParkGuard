import os, json, time, hashlib, uuid, base64, asyncio, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict, deque
from typing import Any
from fastapi import FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .ai.classifier import classify, image_check, RollingBaseline
from .escalation import Escalator

# ── OpenTelemetry tracing (gracefully disabled if SDK not installed) ──────────
_otel_enabled = False
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    _otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if _otel_endpoint:
        _provider = TracerProvider(
            resource=Resource.create({SERVICE_NAME: "parkguard-api"})
        )
        _provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=_otel_endpoint))
        )
        trace.set_tracer_provider(_provider)
        _otel_enabled = True
        logging.getLogger("parkguard").info("OpenTelemetry tracing enabled → %s", _otel_endpoint)
    else:
        logging.getLogger("parkguard").info(
            "OpenTelemetry tracing disabled (set OTEL_EXPORTER_OTLP_ENDPOINT to enable)"
        )
except ImportError:
    pass  # SDK not installed — tracing silently skipped

ROOT=Path(__file__).resolve().parent.parent
NODES=json.loads((ROOT/'config/nodes.json').read_text())
KEYS=json.loads(os.getenv('PARKGUARD_DEVICE_KEYS','{"demo-node":"demo-key-change-me","bay-a":"replace-me"}'))
RATE=int(os.getenv('API_RATE_LIMIT','120')); events=[]; readings=defaultdict(lambda:deque(maxlen=200)); statuses={}; photos={}; rate_buckets=defaultdict(deque); escalator=Escalator(); hash_tail='0'*64
baselines=RollingBaseline()
model=None
try:
    import joblib
    model_path=os.getenv('PARKGUARD_MODEL_PATH',str(ROOT/'parkguard/ai/model.joblib'))
    if Path(model_path).exists(): model=joblib.load(model_path)
except Exception: model=None
app=FastAPI(title='ParkGuard API',version='1.0.0'); app.mount('/static',StaticFiles(directory=ROOT/'web'),name='static'); app.mount('/assets',StaticFiles(directory=ROOT/'web/assets'),name='assets')

# Instrument FastAPI with OpenTelemetry if the SDK is available
if _otel_enabled:
    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        pass

@app.get('/style.css')
def style():
    from fastapi.responses import FileResponse
    return FileResponse(ROOT/'web/style.css')
@app.get('/app.js')
def script():
    from fastapi.responses import FileResponse
    return FileResponse(ROOT/'web/app.js')
mongo_collection=None; object_store=None

@app.on_event('startup')
def connect_optional_services():
    global mongo_collection, object_store
    try:
        from pymongo import MongoClient
        client=MongoClient(os.getenv('MONGO_URI',''),serverSelectionTimeoutMS=700)
        client.admin.command('ping'); mongo_collection=client[os.getenv('MONGO_DB','parkguard')]['events']
    except Exception: mongo_collection=None
    try:
        from minio import Minio
        endpoint=os.getenv('MINIO_ENDPOINT','');
        if endpoint:
            object_store=Minio(endpoint,access_key=os.getenv('MINIO_ACCESS_KEY','parkguard'),secret_key=os.getenv('MINIO_SECRET_KEY','change-me'),secure=os.getenv('MINIO_SECURE','false').lower()=='true')
            bucket=os.getenv('MINIO_BUCKET','parkguard-photos')
            if not object_store.bucket_exists(bucket): object_store.make_bucket(bucket)
    except Exception: object_store=None

@app.on_event('startup')
async def start_alert_repeater():
    app.state.alert_task=asyncio.create_task(alert_repeater())

@app.on_event('shutdown')
async def stop_alert_repeater():
    task=getattr(app.state,'alert_task',None)
    if task: task.cancel()

async def alert_repeater():
    while True:
        for node,item in list(statuses.items()):
            if node in escalator.active: await notify_telegram(node,item)
        await asyncio.sleep(1)

class Reading(BaseModel):
    node_id:str=Field(min_length=1,max_length=64); timestamp:float|None=None
    mq135:float=Field(ge=0,le=4095); mq4:float=Field(ge=0,le=4095)
    temperature:float=Field(ge=-40,le=125); humidity:float=Field(ge=0,le=100)
    duration_s:float=Field(default=0,ge=0,le=86400); event_window:bool=False; sensor_alarm:bool=False; smoke_or_flame:bool=False
    wifi_aps:list[str]=Field(default_factory=list,max_length=30)

def position(node):
    cfg=NODES.get(node)
    if not cfg: raise HTTPException(404,'Node has no registered location')
    return {**cfg,'source':'registered location'}

def recent_neighbor(node):
    now=datetime.now(timezone.utc)
    for other in NODES.get(node,{}).get('neighbors',[]):
        active=escalator.active.get(other)
        if active and now-active['created']<=timedelta(minutes=5): return True
    return False

async def auth(node, key, request):
    if node not in KEYS or key!=KEYS[node]: raise HTTPException(401,'Invalid device credentials')
    now=time.monotonic(); bucket=rate_buckets[request.client.host if request.client else 'unknown']
    while bucket and now-bucket[0]>60: bucket.popleft()
    if len(bucket)>=RATE: raise HTTPException(429,'Rate limit exceeded')
    bucket.append(now)

async def notify_telegram(node,item):
    token=os.getenv('TELEGRAM_BOT_TOKEN',''); base=os.getenv('PUBLIC_BASE_URL','http://localhost:8000')
    if not token or not escalator.should_ping(node): return
    role=escalator.recipient(node); chat=os.getenv({'watchman':'TELEGRAM_CHAT_ID','manager':'TELEGRAM_MANAGER_CHAT_ID','vehicle_owner':'TELEGRAM_OWNER_CHAT_ID'}.get(role,'TELEGRAM_CHAT_ID'),'') or os.getenv('TELEGRAM_CHAT_ID','')
    if not chat:return
    p=item['position']; d=item['decision']; e=item['escalation']; lat=p['latitude'];lon=p['longitude']
    text=(f"🚨 ParkGuard Level {e['level']}: {d['label']} ({d['confidence']:.0%})\n{p['building']} · {p['floor']} · {p['bay']}\nPosition source: {p['source']}\n"
          f"Google Maps: https://maps.google.com/?q={lat},{lon}\nDirections: https://www.google.com/maps/dir/?api=1&destination={lat},{lon}\nWaze: https://waze.com/ul?ll={lat},{lon}&navigate=yes\nCall 101 now: tel:101\n"
          f"Forward to fire brigade: ParkGuard emergency at {p['building']}, {p['floor']}, bay {p['bay']}; {d['label']}; position source {p['source']}. Call 101.")
    url=f'https://api.telegram.org/bot{token}/sendMessage'
    keyboard={'inline_keyboard':[[{'text':'Acknowledge','callback_data':'ack:'+node},{'text':'I am at the scene','callback_data':'scene:'+node}]]}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url,json={'chat_id':chat,'text':text,'reply_markup':keyboard,'disable_web_page_preview':True})
            await client.post(f'https://api.telegram.org/bot{token}/sendLocation',json={'chat_id':chat,'latitude':lat,'longitude':lon})
            if item.get('photo') and e['level']>=2:
                fp=ROOT/'data'/item['photo'].lstrip('/')
                if fp.exists():
                    with fp.open('rb') as f: await client.post(f'https://api.telegram.org/bot{token}/sendPhoto',data={'chat_id':chat,'caption':text[:900]},files={'photo':('incident.jpg',f,'image/jpeg')})
    except Exception: pass

class SMSProvider:
    """Provider boundary for a future SMS vendor; deliberately sends nothing."""
    async def send(self, recipient:str, message:str):
        return {'sent':False,'provider':'stub','recipient_configured':bool(recipient)}

def incident(node, decision, escalation, extra=None):
    global hash_tail
    doc={'id':str(uuid.uuid4()),'node_id':node,'time':datetime.now(timezone.utc).isoformat(),'decision':decision,'escalation':escalation,'position':position(node),'photo':photos.get(node),'prev_hash':hash_tail,'extra':extra or {}}
    canonical=json.dumps(doc,sort_keys=True,separators=(',',':')); doc['hash']=hashlib.sha256((hash_tail+canonical).encode()).hexdigest(); hash_tail=doc['hash']; events.append(doc)
    if mongo_collection is not None:
        try: mongo_collection.insert_one({**doc,'_id':doc['id']})
        except Exception: pass
    return doc

@app.get('/',response_class=HTMLResponse)
def home(): return (ROOT/'web/index.html').read_text(encoding='utf-8')
@app.get('/api/health')
def health(): return {'ok':True,'service':'parkguard','nodes':len(NODES)}
@app.get('/api/nodes')
def list_nodes(): return [{'node_id':n,'config':position(n),'status':statuses.get(n,{})} for n in NODES]
@app.get('/api/status')
def status(): return {'nodes':statuses,'incidents':events[-100:]}
@app.get('/api/incidents')
def get_incidents(): return list(reversed(events[-100:]))
@app.get('/api/location/{node}')
def get_location(node): return position(node)
@app.post('/api/readings')
async def post_reading(payload:Reading, request:Request, x_device_key:str=Header(default='')):
    await auth(payload.node_id,x_device_key,request)
    if payload.node_id not in NODES: raise HTTPException(404,'Register node location first')
    row=payload.model_dump(); hist=list(readings[payload.node_id])
    if hist:
        previous=hist[-1]['reading']; old={**previous,'gas':(previous['mq135']+previous['mq4'])/2}
    else: old={'gas':(row['mq135']+row['mq4'])/2,'temperature':row['temperature'],'humidity':row['humidity']}
    avg_gas=(row['mq135']+row['mq4'])/2; prior=baselines.get(payload.node_id)
    decision=classify({'gas':avg_gas,**row},[old],{'smoke_or_flame':row['smoke_or_flame']},model=model)
    if row['sensor_alarm'] and decision['level']<2: decision['level']=2
    decision['features']['baseline_gas']=prior['gas'];decision['features']['baseline_temperature']=prior['temperature']
    decision['features']['gas_anomaly']=avg_gas>max(prior['gas']*2,prior['gas']+180)
    baselines.add(payload.node_id,avg_gas,row['temperature'])
    # sensor trend rules are authoritative; image flag may be supplied by a camera model.
    state=escalator.evaluate(payload.node_id,decision,row,registered_event=row['event_window'],neighbor_active=recent_neighbor(payload.node_id))
    item={'node_id':payload.node_id,'reading':row,'decision':decision,'escalation':state,'position':position(payload.node_id),'online':True,'time':datetime.now(timezone.utc).isoformat(),'photo':photos.get(payload.node_id)}
    readings[payload.node_id].append(item); statuses[payload.node_id]=item
    if mongo_collection is not None:
        try: mongo_collection.insert_one({'_id':str(uuid.uuid4()),'kind':'reading',**item})
        except Exception: pass
    if state['level']>=2:
        previous=next((x for x in reversed(events) if x['node_id']==payload.node_id),None)
        too_soon=previous and previous['escalation']['level']==state['level'] and (datetime.now(timezone.utc)-datetime.fromisoformat(previous['time'])).total_seconds()<30
        if not too_soon: incident(payload.node_id,decision,state)
        await notify_telegram(payload.node_id,item)
    if os.getenv('WIFI_POSITIONING','false').lower()=='true' and payload.wifi_aps:
        item['wifi_positioning']=await approximate_wifi_position(payload.wifi_aps)
    return item

async def approximate_wifi_position(aps):
    """Experimental best-effort lookup; never used to replace registered coordinates."""
    if os.getenv('WIFI_POSITIONING','false').lower()!='true':return {'available':False,'source':'approximate (Wi-Fi)','reason':'disabled'}
    # BeaconDB is an experimental MLS-compatible lookup; coverage/availability varies.
    try:
        import httpx
        wifi=[{'macAddress':str(mac)} for mac in aps[:10]]
        async with httpx.AsyncClient(timeout=4) as client:
            r=await client.post('https://api.beacondb.net/v1/geolocate',json={'wifiAccessPoints':wifi},headers={'User-Agent':'ParkGuard/1.0 prototype'})
            if r.status_code==200:
                x=r.json()['location'];return {'available':True,'latitude':x['lat'],'longitude':x['lng'],'accuracy_m':r.json().get('accuracy'),'source':'approximate (Wi-Fi)','experimental':True}
    except Exception: pass
    return {'available':False,'source':'approximate (Wi-Fi)','experimental':True}
@app.post('/api/photos/{node}')
async def upload_photo(node:str,request:Request,x_device_key:str=Header(default='')):
    global object_store, hash_tail
    await auth(node,x_device_key,request)
    ctype=request.headers.get('content-type','')
    if ctype.startswith('image/jpeg') or ctype.startswith('image/png'): data=await request.body()
    elif ctype.startswith('multipart/form-data'):
        form=await request.form(); file=form.get('file')
        if file is None or not hasattr(file,'read'): raise HTTPException(400,'Multipart field "file" required')
        data=await file.read(8_000_001)
    else: raise HTTPException(415,'JPEG or PNG required')
    if len(data)>8_000_000: raise HTTPException(413,'Photo too large')
    path=ROOT/'data/photos'; path.mkdir(parents=True,exist_ok=True); name=f'{uuid.uuid4()}.jpg'; (path/name).write_bytes(data)
    if object_store is None and os.getenv('MINIO_ENDPOINT',''):
        try:
            from minio import Minio
            object_store=Minio(os.getenv('MINIO_ENDPOINT'),access_key=os.getenv('MINIO_ACCESS_KEY','parkguard'),secret_key=os.getenv('MINIO_SECRET_KEY','change-me'),secure=os.getenv('MINIO_SECURE','false').lower()=='true')
            bucket=os.getenv('MINIO_BUCKET','parkguard-photos')
            if not object_store.bucket_exists(bucket):object_store.make_bucket(bucket)
        except Exception:object_store=None
    if object_store is not None:
        try:
            from io import BytesIO
            from minio import Minio
            object_store.put_object(os.getenv('MINIO_BUCKET','parkguard-photos'),name,BytesIO(data),len(data),content_type='image/jpeg')
        except Exception: pass
    previous_path=ROOT/'data'/photos[node].lstrip('/') if node in photos else None
    previous_bytes=previous_path.read_bytes() if previous_path and previous_path.exists() else None
    photos[node]=f'/photos/{name}'; image=image_check(data,previous_bytes)
    if node in statuses: statuses[node]['photo']=photos[node]
    for event in reversed(events):
        if event['node_id']==node and not event.get('photo'):
            event['photo']=photos[node]
            break
    # Rebuild the in-memory SHA-256 chain after attaching the late camera frame.
    tail='0'*64
    for event in events:
        event['prev_hash']=tail; old_hash=event.pop('hash',None)
        canonical=json.dumps(event,sort_keys=True,separators=(',',':'))
        event['hash']=hashlib.sha256((tail+canonical).encode()).hexdigest();tail=event['hash']
    hash_tail=tail
    latest=statuses.get(node)
    if latest and (image['smoke_or_flame'] or image['growing']):
        row=latest['reading']; hist=list(readings[node]); history=hist[-2]['reading'] if len(hist)>1 else row
        old={'gas':(history['mq135']+history['mq4'])/2,'temperature':history['temperature'],'humidity':history['humidity']}
        d=classify({'gas':(row['mq135']+row['mq4'])/2,**row},[old],image,model=model)
        state=escalator.evaluate(node,d,{**row,'smoke_or_flame':image['smoke_or_flame']},registered_event=row.get('event_window',False),neighbor_active=recent_neighbor(node),photo_growth=image['growing'])
        latest.update(decision=d,escalation=state);statuses[node]=latest
        if state['level']>=2:
            incident(node,d,state,{'image_check':image});await notify_telegram(node,latest)
    if latest and latest['escalation']['level']>=2 and os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                fp=ROOT/'data'/photos[node].lstrip('/')
                with fp.open('rb') as f: await client.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendPhoto",data={'chat_id':os.getenv('TELEGRAM_CHAT_ID'),'caption':f"ParkGuard {latest['decision']['label']} · {latest['position']['building']} {latest['position']['floor']} {latest['position']['bay']} · position source: {latest['position']['source']}"},files={'photo':('incident.jpg',f,'image/jpeg')})
        except Exception:pass
    return {'url':photos[node],'image_check':image}
@app.get('/photos/{name}')
def photo(name:str):
    p=ROOT/'data/photos'/Path(name).name
    if not p.exists():raise HTTPException(404,'Photo not found')
    from fastapi.responses import FileResponse
    return FileResponse(p)
@app.post('/api/ack/{node}')
def acknowledge(node:str,body:dict|None=None):
    if node not in NODES: raise HTTPException(404,'Unknown node')
    return {'acknowledged':escalator.acknowledge(node),'node_id':node,'who':(body or {}).get('who','watchman')}
@app.post('/api/telegram/webhook')
def telegram_webhook(body:dict):
    query=body.get('callback_query',{}); data=query.get('data','')
    if ':' not in data:return {'ok':True}
    action,node=data.split(':',1)
    if action in ('ack','scene'): escalator.acknowledge(node)
    return {'ok':True,'acknowledged':node in escalator.active and escalator.active[node]['acknowledged']}
@app.post('/api/phone-location')
def phone_location(body:dict):
    lat=float(body.get('latitude',0)); lon=float(body.get('longitude',0))
    if not (-90<=lat<=90 and -180<=lon<=180):raise HTTPException(422,'Invalid coordinates')
    return {'node_id':'phone-gps','position':{'latitude':lat,'longitude':lon,'source':'phone GPS'},'label':'Phone GPS tracker'}
@app.get('/metrics',response_class=PlainTextResponse)
def metrics():
    lines=['# HELP parkguard_nodes_known Configured nodes','# TYPE parkguard_nodes_known gauge',f'parkguard_nodes_known {len(NODES)}','# HELP parkguard_incidents_total Stored incidents','# TYPE parkguard_incidents_total gauge',f'parkguard_incidents_total {len(events)}']
    for n,s in statuses.items(): lines += [f'parkguard_level{{node="{n}"}} {s["escalation"]["level"]}']
    return '\n'.join(lines)+'\n'
@app.post('/api/demo/{scenario}')
def demo(scenario:str):
    scenarios={'normal':(80,60,24,48,False),'exhaust':(550,120,36,35,False),'firecracker_smoke':(300,90,38,31,True),'cng_leak':(250,800,30,45,False),'ev_fault':(270,140,68,25,False),'vehicle_fire':(750,300,75,20,True),'explosion':(850,600,95,19,True),'unwarranted_fire':(700,300,70,22,True)}
    if scenario=='spreading_fire':
        return [demo('vehicle_fire') if n=='demo-node' else _fake(n,800,350,80,20,True) for n in ('demo-node','bay-a')]
    if scenario=='network_outage':return {'queued':True,'message':'Simulator queues readings and prioritizes emergency events, then replays them after reconnect.'}
    if scenario not in scenarios:raise HTTPException(404,'Unknown scenario')
    g,m,t,h,sm=scenarios[scenario]; return _fake('demo-node',g,m,t,h,sm)
def _fake(node,g,m,t,h,sm):
    row={'node_id':node,'mq135':g,'mq4':m,'temperature':t,'humidity':h,'gas':(g+m)/2,'smoke_or_flame':sm,'event_window':False,'sensor_alarm':False}
    d=classify(row,[{'gas':50,'temperature':24}],{'smoke_or_flame':sm}); s=escalator.evaluate(node,d,row,neighbor_active=recent_neighbor(node))
    item={'node_id':node,'reading':row,'decision':d,'escalation':s,'position':position(node),'online':True,'time':datetime.now(timezone.utc).isoformat()}; statuses[node]=item
    if s['level']>=2:
        incident(node,d,s)
    return item
