# Justfile for setting up and running the Python application

# Default target (run the application)
default:
    just run

# Install Python dependencies
install:
    # Install Python dependencies
    pip install -r requirements.txt
    # Download NLTK data
    python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

# Run the application
run:
    python3 app.py

# Clean up temporary files and folders
clean:
    # Remove temporary frame files
    rm -f temp_frame_*.jpg
    # Remove the index folder
    rm -rf index
    # Remove log files
    rm -f app.log

# Format the code using black
format:
    black .

# Lint the code using flake8
lint:
    flake8 .

# Run tests (if any)
test:
    pytest

# Set up the development environment
setup: install format lint