#!/usr/bin/env python3
"""
Test IBM Quantum connection and list backends.
Run: IBM_QUANTUM_TOKEN="your-token" python scripts/test_ibm_connection.py
"""
import os
import sys

token = os.environ.get("IBM_QUANTUM_TOKEN")
if not token:
    print("Error: Set IBM_QUANTUM_TOKEN first")
    print('Example: IBM_QUANTUM_TOKEN="your-token" python scripts/test_ibm_connection.py')
    sys.exit(1)

try:
    from qiskit_ibm_runtime import QiskitRuntimeService
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
    backends = list(service.backends())
    print("Connected. Available backends:", [b.name for b in backends[:8]])
    # Check if ibm_miami exists
    miami = service.backend("ibm_miami") if any(b.name == "ibm_miami" for b in backends) else None
    if miami:
        print("ibm_miami: OK")
    else:
        print("ibm_miami: not found in list")
except Exception as e:
    print("Error:", e)
    sys.exit(1)
