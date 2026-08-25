\# RobustLoop - Fault Injection PoC



A deterministic CI tool for injecting \*semantic\* sensor faults (Freeze, Drift, Contradiction) into robotics data streams before code hits the physical robot.



\## Why?

Simulators like Gazebo add noise. But real-world robot crashes happen because of \*plausible\* but false data (e.g., frozen sensor values, timestamp delays, or two sensors contradicting each other). RobustLoop automates the testing of software robustness against these semantic faults.



\## Current PoC Features

\- Fault Injection SDK (Freeze, Drift, Delay, Offset, Dropout, Spike)

\- Multi-Sensor Contradiction Testing

\- Deterministic Safety Assertions (Crash vs. Safe-Mode evaluation)

\- Reliability Scoring across different Software Versions (CI Simulation)



\## Run it

```bash

python robustloop\_poc.py



