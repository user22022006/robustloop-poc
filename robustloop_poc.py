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

# --- SIMULIERTE ROBOTER-SOFTWARE VERSIONEN ---

def software_v1_0(sensor_a, sensor_b):
    """Version 1.0: Vertraut blind auf Sensor A."""
    return sensor_a, "RUNNING" # Ignoriert Sensor B komplett

def software_v1_1(sensor_a, sensor_b):
    """Version 1.1: Erkennt Widerspruch, bremst aber erst bei 0.5m Differenz."""
    if abs(sensor_a - sensor_b) > 0.5:
        return sensor_b, "SAFE_MODE (Late Reaction)"
    return sensor_a, "RUNNING"

def software_v2_0(sensor_a, sensor_b):
    """Version 2.0: Robuste Logik. Erkennt Widerspruch ab 0.1m."""
    if abs(sensor_a - sensor_b) > 0.1:
        return sensor_b, "SAFE_MODE (Immediate)"
    return sensor_a, "RUNNING"

def run_test_suite(software_func, version_name):
    sensor_lidar = SensorProxy("Lidar")
    sensor_safety = SensorProxy("Safety")
    sensor_lidar.set_fault(fault_type="drift", start_ms=2000, duration_ms=3000)
    
    current_ms = 0
    robot_speed = 0.2
    distance_to_obstacle = 2.0
    reaction_time_ms = 0
    crashed = False
    safe_mode_triggered = False
    
    while current_ms <= 5000:
        t_sec = current_ms / 1000.0
        distance_to_obstacle = max(0.0, 2.0 - (robot_speed * t_sec))
        
        val_a = sensor_lidar.read(distance_to_obstacle, current_ms)
        val_b = sensor_safety.read(distance_to_obstacle, current_ms)
        
        used_value, decision = software_func(val_a, val_b)
        
        if "SAFE_MODE" in decision:
            if not safe_mode_triggered:
                reaction_time_ms = current_ms - 2000 # Zeit seit Fault-Start
                safe_mode_triggered = True
            robot_speed = 0.0 # Roboter stoppt
            
        # Safety Assertion: Wenn Ground Truth 0 ist und Speed > 0 -> CRASH
        if distance_to_obstacle <= 0.05 and robot_speed > 0:
            crashed = True
            break
            
        current_ms += 50
        
    # Reliability Score berechnen (100 = Perfekt, 0 = Katastrophe)
    score = 0
    if safe_mode_triggered and not crashed:
        score = 100 - int(reaction_time_ms / 10) # Punkte abziehen für späte Reaktion
    elif crashed:
        score = 0
        
    return {
        "Version": version_name,
        "Crashed": crashed,
        "Safe Mode Triggered": safe_mode_triggered,
        "Reaction Time (ms)": reaction_time_ms,
        "Reliability Score": max(0, score)
    }

if __name__ == "__main__":
    print("="*60)
    print("ROBUSTLOOP CI - RUNNING RELIABILITY TEST SUITE")
    print("="*60)
    print("\n[Scenario] Sensor Drift on Lidar starting at t=2000ms\n")
    
    versions = [
        ("v1.0", software_v1_0),
        ("v1.1", software_v1_1),
        ("v2.0", software_v2_0)
    ]
    
    results = []
    for name, func in versions:
        print(f"[*] Testing {name}...")
        result = run_test_suite(func, name)
        results.append(result)
        
    print("\n" + "-"*60)
    print(f"{'VERSION':<10} | {'CRASH':<8} | {'SAFE MODE':<12} | {'REACT (MS)':<12} | {'SCORE':<6}")
    print("-"*60)
    
    for r in results:
        print(f"{r['Version']:<10} | {'YES' if r['Crashed'] else 'NO':<8} | {'YES' if r['Safe Mode Triggered'] else 'NO':<12} | {r['Reaction Time (ms)']:<12} | {r['Reliability Score']:<6}")
    
    print("-"*60)
    print("\n[CONCLUSION] v2.0 significantly improved system robustness.")
    print("="*60)
