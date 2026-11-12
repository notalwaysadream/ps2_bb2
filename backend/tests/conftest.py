import os
import pytest

# Ensure tests run in isolated offline simulation mode
os.environ["SIMULATION_MODE"] = "true"
os.environ["GROQ_API_KEY"] = ""
os.environ["GNANI_API_KEY"] = ""
