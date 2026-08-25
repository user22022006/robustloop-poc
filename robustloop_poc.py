import math
import json
import os
import sys # Neu: Für System-Exit-Codes

class SensorProxy:
    def __init__(self):
        self.fault_type = None
        self.fault_start_ms = 0
        self.fault_duration_ms = 0
        self.drift_accumulator = 0

    def set_fault(self, fault_type, start_ms, duration_ms):
        self.fault_type = fault_type
        self.fault_start_ms = start_ms
        self.fault_duration_ms = duration_ms
        self.drift_accumulator = 0

    def read(self, true_distance, current_ms):
        val = true_distance
        if self.fault_start_ms <= current_ms < self.fault_start_ms + self.fault_duration_ms:
            if self.fault_type == "drift":
                self.drift_accumulator += 0.05
                val = true_distance + self.drift_accumulator
        return round(val, 3)

def software_v1_0(sensor_a, sensor_b): return sensor_a, "RUNNING"
def software_v1_1(sensor_a, sensor_b):
    if abs(sensor_a - sensor_b) > 0.5: return sensor_b, "SAFE_MODE"
    return sensor_a, "RUNNING"
def software_v2_0(sensor_a, sensor_b):
    if abs(sensor_a - sensor_b) > 0.1: return sensor_b, "SAFE_MODE"
    return sensor_a, "RUNNING"

def run_test_suite(software_func, version_name):
    sensor_lidar = SensorProxy()
    sensor_safety = SensorProxy()
    sensor_lidar.set_fault(fault_type="drift", start_ms=2000, duration_ms=3000)
    
    current_ms = 0
    speed = 0.2
    pos = 0.0
    wall_pos = 2.0
    
    crashed = False
    safe_mode_triggered = False
    reaction_time = 0
    
    while current_ms <= 5000:
        true_dist = max(0.0, wall_pos - pos)
        val_a = sensor_lidar.read(true_dist, current_ms)
        val_b = sensor_safety.read(true_dist, current_ms)
        
        used_val, decision = software_func(val_a, val_b)
        
        if "SAFE_MODE" in decision:
            if not safe_mode_triggered:
                reaction_time = current_ms - 2000
                safe_mode_triggered = True
            speed = 0.0
            
        pos += speed * 0.05
        
        if pos >= wall_pos - 0.05 and speed > 0:
            crashed = True
            break
            
        current_ms += 50
        
    score = 0
    if safe_mode_triggered and not crashed:
        score = 100 - int(reaction_time / 10)
    elif crashed:
        score = 0
        
    return {"version": version_name, "score": max(0, score), "crashed": crashed, "reaction_time": reaction_time}

if __name__ == "__main__":
    print("="*50)
    print("ROBUSTLOOP CI - EXECUTING RELIABILITY TEST SUITE")
    print("="*50)
    
    versions = [("v1.0", software_v1_0), ("v1.1", software_v1_1), ("v2.0", software_v2_0)]
    all_results = []
    any_crash = False
    
    for name, func in versions:
        print(f"[*] Testing {name}...")
        result = run_test_suite(func, name)
        all_results.append(result)
        if result["crashed"]:
            any_crash = True

    # NEU: Ergebnisse als JSON-Artefakt speichern 
    with open("robustloop_results.json", "w") as f:
        json.dump({"test_suite": "Sensor_Drift_Contradiction", "results": all_results}, f, indent=4)
    
    print("\n" + "-"*50)
    print(f"{'VERSION':<10} | {'CRASH':<8} | {'SCORE':<6}")
    print("-"*50)
    for r in all_results:
        print(f"{r['version']:<10} | {'YES' if r['crashed'] else 'NO':<8} | {r['score']:<6}")
    print("-"*50)
    
    #   Exit 1 bei Crash -> GitHub Action schlägt fehl!
    if any_crash:
        print("\n❌ ROBUSTLOOP CI STATUS: FAILED")
        print("   -> At least one software version would crash in production.")
        sys.exit(1)
    else:
        print("\n✅ ROBUSTLOOP CI STATUS: PASSED")
        print("   -> All versions handle the sensor fault safely.")
        sys.exit(0)
