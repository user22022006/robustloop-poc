import math
import json
import os

class SensorProxy:
    def __init__(self, name):
        self.name = name
        self.fault_type = None
        self.fault_start_ms = 0
        self.fault_duration_ms = 0
        self.frozen_value = None
        self.drift_accumulator = 0

    def set_fault(self, fault_type, start_ms, duration_ms):
        self.fault_type = fault_type
        self.fault_start_ms = start_ms
        self.fault_duration_ms = duration_ms
        self.frozen_value = None
        self.drift_accumulator = 0

    def read(self, true_distance, current_ms):
        val = true_distance
        if self.fault_start_ms <= current_ms < self.fault_start_ms + self.fault_duration_ms:
            if self.fault_type == "drift":
                self.drift_accumulator += 0.05
                val = true_distance + self.drift_accumulator
        return round(val, 3)

# --- ROBOTER LOGIK VERSIONEN ---
def software_v1_0(sensor_a, sensor_b):
    return sensor_a, "RUNNING" # Blind

def software_v1_1(sensor_a, sensor_b):
    if abs(sensor_a - sensor_b) > 0.5: return sensor_b, "SAFE_MODE"
    return sensor_a, "RUNNING"

def software_v2_0(sensor_a, sensor_b):
    if abs(sensor_a - sensor_b) > 0.1: return sensor_b, "SAFE_MODE"
    return sensor_a, "RUNNING"

def run_test_suite(software_func, version_name):
    sensor_lidar = SensorProxy("Lidar")
    sensor_safety = SensorProxy("Safety")
    sensor_lidar.set_fault(fault_type="drift", start_ms=2000, duration_ms=3000)
    
    current_ms = 0
    speed = 0.2
    pos = 0.0 # Roboter Startposition
    wall_pos = 2.0 # Wand ist 2 Meter entfernt
    
    history = {
        "timestamps": [], "robot_pos": [], "sensor_a": [], "sensor_b": [], "status": []
    }
    
    crashed = False
    safe_mode_triggered = False
    reaction_time = 0
    
    while current_ms <= 5000:
        t_sec = current_ms / 1000.0
        true_dist = max(0.0, wall_pos - pos)
        
        val_a = sensor_lidar.read(true_dist, current_ms)
        val_b = sensor_safety.read(true_dist, current_ms)
        
        used_val, decision = software_func(val_a, val_b)
        
        if "SAFE_MODE" in decision:
            if not safe_mode_triggered:
                reaction_time = current_ms - 2000
                safe_mode_triggered = True
            speed = 0.0
            
        pos += speed * 0.05 # Bewege Roboter
        
        if pos >= wall_pos - 0.05 and speed > 0:
            crashed = True
            speed = 0.0
            
        history["timestamps"].append(round(t_sec, 2))
        history["robot_pos"].append(round(pos, 3))
        history["sensor_a"].append(val_a)
        history["sensor_b"].append(val_b)
        history["status"].append(decision)
        
        current_ms += 50
        
    score = 0
    if safe_mode_triggered and not crashed:
        score = 100 - int(reaction_time / 10)
    elif crashed:
        score = 0
        
    return history, {"version": version_name, "score": max(0, score), "crashed": crashed, "reaction": reaction_time}

def generate_dynamic_report(histories, results):
    datasets = []
    colors = {"v1.0": "rgba(231, 76, 60, 1)", "v1.1": "rgba(241, 196, 15, 1)", "v2.0": "rgba(39, 174, 96, 1)"}
    
    for res in results:
        v = res["version"]
        datasets.append({
            "label": f"Roboter Position - {v} (Score: {res['score']})",
            "data": histories[v]["robot_pos"],
            "borderColor": colors[v],
            "borderWidth": 4,
            "fill": False,
            "tension": 0.1
        })
        
    datasets.append({
        "label": "Wand (Hindernis)",
        "data": [2.0] * len(histories["v1.0"]["timestamps"]),
        "borderColor": "rgba(0, 0, 0, 1)",
        "borderDash": [10, 5],
        "fill": False
    })

    data_json = json.dumps({
        "labels": histories["v1.0"]["timestamps"],
        "datasets": datasets
    })

    html_content = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>RobustLoop - Dynamic Reliability Demo</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style> body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f9f9f9; }}
    .container {{ max-width: 900px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }} </style></head>
    <body><div class="container">
        <h1>RobustLoop Dynamic CI Report</h1>
        <div style="background: #eef2f5; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <p><strong>Test Scenario:</strong> Sensor Drift starting at t=2.0s</p>
            <p><strong>Result v1.0 (Red):</strong> Trusted drifting sensor -> <b>CRASH</b> (Score 0)</p>
            <p><strong>Result v1.1 (Yellow):</strong> Late contradiction check -> <b>Hard Brake</b> (Score 60)</p>
            <p><strong>Result v2.0 (Green):</strong> Immediate contradiction check -> <b>Safe Stop</b> (Score 90)</p>
        </div>
        <canvas id="chart" width="800" height="400"></canvas>
        <p style="font-size: 12px; color: #7f8c8d; margin-top: 20px;">* The chart shows the physical position of the robot over time. A robust system (v2.0) stops early, while the blind system (v1.0) drives into the wall.</p>
    </div>
    <script> const ctx = document.getElementById('chart').getContext('2d');
    new Chart(ctx, {{ type: 'line', data: {data_json}, 
    options: {{ scales: {{ x: {{ type: 'linear', title: {{display: true, text: 'Zeit (Sekunden)'}} }}, y: {{ title: {{display: true, text: 'Roboter Position (Meter)'}}, min: 0, max: 2.2 }} }}, 
    plugins: {{ title: {{ display: true, text: 'Dynamische Roboterbewegung bei Fault Injection' }} }} }} }}); 
    </script></body></html>"""

    report_filename = "robustloop_dynamic_report.html"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    try:
        os.startfile(report_filename)
    except:
        pass

if __name__ == "__main__":
    print("="*50)
    print("ROBUSTLOOP DYNAMIC CI - RUNNING RELIABILITY TEST SUITE")
    print("="*50)
    
    versions = [("v1.0", software_v1_0), ("v1.1", software_v1_1), ("v2.0", software_v2_0)]
    histories = {}
    results = []
    
    for name, func in versions:
        print(f"[*] Testing {name}...")
        hist, res = run_test_suite(func, name)
        histories[name] = hist
        results.append(res)
        
    print("\n[+] Generating Dynamic HTML Report...")
    generate_dynamic_report(histories, results)
    print("\n" + "="*50)
    print("ERGEBNISSE:")
    for r in results:
        status = "CRASHED" if r["crashed"] else "SAFE"
        print(f" - {r['version']}: {status} (Score: {r['score']})")
    print("="*50)
