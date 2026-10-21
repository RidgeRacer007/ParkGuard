import argparse, json, random
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
import joblib

def generated(n=1200):
    rng=random.Random(12); rows=[]
    centers={"normal":(70,70,50,24,52,3,0,0),"vehicle exhaust":(500,550,120,36,35,180,2,60),"firecracker smoke":(280,300,90,38,31,110,10,8),"CNG/flammable gas leak":(680,240,760,30,45,280,2,30),"EV or battery fault":(350,260,130,68,25,100,16,100),"vehicle fire":(750,700,300,95,20,400,30,130)}
    for label,c in centers.items():
        for _ in range(n//len(centers)): rows.append([*[max(0,rng.gauss(v,max(2,v*.18))) for v in c],label])
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--generate',action='store_true'); ap.add_argument('--data'); ap.add_argument('--output',default='parkguard/ai/model.joblib'); args=ap.parse_args()
    rows=generated() if args.generate or not args.data else [json.loads(x) for x in Path(args.data).read_text().splitlines() if x.strip()]
    if not args.generate and args.data: rows=[[r[k] for k in ('gas','mq135','mq4','temperature','humidity','gas_rise','temperature_rise','duration_s')]+[r['label']] for r in rows]
    X=np.array([r[:-1] for r in rows]); y=np.array([r[-1] for r in rows]); enc=LabelEncoder(); y=enc.fit_transform(y)
    a,b,c,d=train_test_split(X,y,test_size=.2,random_state=7,stratify=y); clf=RandomForestClassifier(n_estimators=160,class_weight='balanced',random_state=7).fit(a,c)
    print(classification_report(d,clf.predict(b),target_names=enc.classes_)); Path(args.output).parent.mkdir(parents=True,exist_ok=True); joblib.dump(clf,args.output)
if __name__=='__main__': main()
