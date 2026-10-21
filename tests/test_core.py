from parkguard.ai.classifier import classify
from parkguard.escalation import Escalator
def test_low_confidence_cannot_erase_danger():
 d=classify({'gas':300,'mq135':300,'mq4':300,'temperature':70,'humidity':20},[{'gas':10,'temperature':20}],{'smoke_or_flame':True});assert d['level']>=2
def test_blast_detection():
 e=Escalator();s=e.evaluate('n',{'label':'uncertain','level':0,'features':{'gas_rise':200,'temperature_rise':12}},{'smoke_or_flame':True});assert s['blast'] and s['level']==3
def test_ack_stops_ping():
 e=Escalator();e.evaluate('n',{'label':'vehicle fire','level':2,'features':{}},{});assert e.should_ping('n');assert e.acknowledge('n');assert not e.should_ping('n')
def test_registered_location():
 from parkguard.main import position
 assert position('demo-node')['source']=='registered location'
def test_neighbor_marks_spreading():
 e=Escalator();s=e.evaluate('a',{'label':'vehicle fire','level':2,'features':{}},{},neighbor_active=True);assert s['spreading'] and s['level']==3
def test_gas_rule_survives_classifier_confidence():
 assert classify({'gas':700,'mq135':100,'mq4':900,'temperature':30,'humidity':40},[{'gas':20,'temperature':20}])['level']>=2
