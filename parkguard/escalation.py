"""Emergency rules, hysteresis, chained recipients and acknowledgment state."""
from datetime import datetime, timezone, timedelta

class Escalator:
    def __init__(self): self.active={}; self.last_level={}
    def evaluate(self,node,decision,reading,registered_event=False,neighbor_active=False,photo_growth=False,now=None):
        now=now or datetime.now(timezone.utc); f=decision.get('features',{}); old=self.active.get(node)
        blast=f.get('temperature_rise',0)>=8 and f.get('gas_rise',0)>=100 and reading.get('smoke_or_flame',False)
        # Smoke alone can be dust or exhaust. Only a hot/fire-classified condition or an
        # explicit flame cue enters the unwarranted-fire branch.
        fire=decision.get('label') == 'vehicle fire' or bool(reading.get('flame_detected'))
        prolonged=old and (now-old['created']).total_seconds()>90 and f.get('temperature_rise',0)>0
        spreading=bool((neighbor_active and fire) or (photo_growth and fire) or (prolonged and fire))
        unwarranted=fire and not registered_event
        level=3 if blast or unwarranted or spreading else max(int(decision.get('level',0)), 2 if fire else 0)
        # Hysteresis: do not drop an active alert until three consecutive safe evaluations.
        if old and not old.get('acknowledged') and level < old['level']:
            old['safe_count']=old.get('safe_count',0)+1
            if old['safe_count']<3: level=old['level']
        if level>=2:
            if not old: old={'created':now,'level':level,'acknowledged':False,'safe_count':0,'last_ping':None}
            old.update(level=level,spreading=spreading,blast=blast,unwarranted=unwarranted,label=decision.get('label','uncertain'))
            self.active[node]=old
        elif old and (old.get('acknowledged') or old.get('safe_count',0)>=3): self.active.pop(node,None)
        self.last_level[node]=level
        return {"level":level,"emergency":level==3,"spreading":spreading,"blast":blast,"unwarranted_fire":unwarranted,"acknowledged":bool(old and old.get('acknowledged'))}
    def acknowledge(self,node):
        if node not in self.active: return False
        self.active[node]['acknowledged']=True; return True
    def should_ping(self,node,now=None):
        now=now or datetime.now(timezone.utc); item=self.active.get(node)
        if not item or item['acknowledged']: return False
        if item['last_ping'] is None or now-item['last_ping']>=timedelta(seconds=30): item['last_ping']=now; return True
        return False
    def recipient(self,node,now=None):
        item=self.active.get(node)
        if not item:return None
        elapsed=((now or datetime.now(timezone.utc))-item['created']).total_seconds()
        return 'watchman' if elapsed<60 else 'manager' if elapsed<120 else 'vehicle_owner'
