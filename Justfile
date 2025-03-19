# Set shell mode
set shell := ["bash", "-c"]

# Define virtual environment name
venv := ".venv_test"

# Use Python 3.11 explicitly
PYTHON := `command -v python3.11 || command -v python3 || command -v python`

# Create virtual environment and install dependencies
setup:
    uv venv --python=python3.11 .venv_test   # ✅ Ensure Python 3.11 is used
    source .venv_test/bin/activate && uv pip install -r requirements.txt  # Activate and install dependencies
    source .venv_test/bin/activate && bentoml build 

# Run the application
run:
    source .venv_test/bin/activate
    python3 app.py

# Clean up virtual environment
clean:
    rm -rf {{venv}}

# Display help message
help:
    @echo "Available recipes:"
    @echo "  setup - Create virtual environment and install dependencies"
    @echo "  run   - Run the application"
    @echo "  clean - Remove virtual environment"
