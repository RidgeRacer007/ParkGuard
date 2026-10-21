"""Conservative trend classifier. Rules determine danger; ML never lowers it."""
from collections import defaultdict, deque
from math import exp

LABELS = ("normal", "vehicle exhaust", "firecracker smoke", "CNG/flammable gas leak", "EV or battery fault", "vehicle fire")

class RollingBaseline:
    def __init__(self, size=120): self.values = defaultdict(lambda: deque(maxlen=size))
    def add(self, node, gas, temp): self.values[node].append((float(gas), float(temp)))
    def get(self, node):
        rows = self.values[node]
        if not rows: return {"gas": 0.0, "temperature": 20.0}
        return {"gas": sum(x[0] for x in rows)/len(rows), "temperature": sum(x[1] for x in rows)/len(rows)}

def classify(reading, history=(), image=None, model=None):
    gas = float(reading.get("gas", 0)); co2 = float(reading.get("mq135", gas)); mq4 = float(reading.get("mq4", gas))
    temp = float(reading.get("temperature", 20)); humidity = float(reading.get("humidity", 50))
    old = history[0] if history else reading
    rise = gas - float(old.get("gas", gas)); temp_rise = temp - float(old.get("temperature", temp))
    humidity_change = humidity - float(old.get("humidity", humidity))
    duration = float(reading.get("duration_s", 0)); smoke = bool((image or {}).get("smoke_or_flame"))
    if smoke and temp_rise >= 8 and rise >= 100: label, confidence = "vehicle fire", .97
    elif smoke and temp >= 55: label, confidence = "vehicle fire", .91
    elif temp >= 48 and temp_rise >= 4: label, confidence = "EV or battery fault", .82
    elif mq4 >= 700 or (rise >= 180 and mq4 >= 400): label, confidence = "CNG/flammable gas leak", .88
    elif smoke and (duration < 20 or humidity_change <= -6): label, confidence = "firecracker smoke", .68
    elif co2 >= 450 or gas >= 350: label, confidence = "vehicle exhaust", .76
    else: label, confidence = "normal", .9
    if model:
        try:
            pred = model.predict_proba([[gas, co2, mq4, temp, humidity, rise, temp_rise, duration]])[0]
            classes = list(model.classes_); ml_label = str(classes[int(pred.argmax())]); ml_conf = float(pred.max())
            if ml_conf >= .72 and label == "normal": label, confidence = ml_label, ml_conf
        except Exception: pass
    if confidence < .60: label = "uncertain"
    # Danger cues are independent and cannot be erased by uncertain/low-confidence labels.
    if smoke and temp_rise >= 8 and rise >= 100: level = 3
    elif label in ("CNG/flammable gas leak", "EV or battery fault", "vehicle fire"): level = 2
    elif label in ("vehicle exhaust", "firecracker smoke"): level = 1
    else: level = 0
    return {"label": label, "confidence": round(confidence, 3), "level": level, "features": {"gas_rise": rise, "temperature_rise": temp_rise, "duration_s": duration, "humidity": humidity, "humidity_change": humidity_change}}

def image_check(jpeg_bytes, previous=None):
    """Replace with a real smoke/flame model. Current safe stub uses coarse warm-color score."""
    try:
        from PIL import Image
        from io import BytesIO
        def score(blob):
            im=Image.open(BytesIO(blob)).convert("RGB").resize((64,64)); px=list(im.getdata())
            return sum(1 for r,g,b in px if r>180 and g>70 and g<190 and b<100)/len(px)
        warm=score(jpeg_bytes); prior=score(previous) if previous else 0.0; growing=warm-prior>.04
        return {"smoke_or_flame": warm > .08, "growing":growing,"confidence": round(min(.6,warm*2),3), "method":"colour heuristic stub"}
    except Exception: return {"smoke_or_flame": False, "confidence": 0.0, "method":"unavailable heuristic"}
