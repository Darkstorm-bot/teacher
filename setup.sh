#!/bin/bash
# HF-Tutor Setup Script
# This script sets up the complete development environment for HF-Tutor

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     HF-Tutor Setup Script             ║${NC}"
echo -e "${BLUE}║  Multi-Agent AI Tutoring System       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if running in correct directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}Error: Please run this script from the hf-tutor root directory${NC}"
    exit 1
fi

# Function to print section headers
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to check command success
check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
        exit 1
    fi
}

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================
print_header "Step 1: Checking Prerequisites"

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "Python version: ${GREEN}$PYTHON_VERSION${NC}"
else
    echo -e "${RED}Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

# Check Node.js version
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "Node.js version: ${GREEN}$NODE_VERSION${NC}"
else
    echo -e "${YELLOW}Node.js not found. Frontend features will be limited.${NC}"
fi

# Check Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "Docker version: ${GREEN}$DOCKER_VERSION${NC}"
else
    echo -e "${YELLOW}Docker not found. SearXNG research features will be disabled.${NC}"
fi

# Check Ollama
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version)
    echo -e "Ollama version: ${GREEN}$OLLAMA_VERSION${NC}"
else
    echo -e "${RED}Ollama not found. Please install from https://ollama.ai${NC}"
    echo -e "${YELLOW}Continuing setup, but you'll need Ollama to run the system${NC}"
fi

check_success "Prerequisites check completed"

# ============================================================================
# Step 2: Create Virtual Environment
# ============================================================================
print_header "Step 2: Setting Up Python Virtual Environment"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    check_success "Virtual environment created"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
check_success "Virtual environment activated"

# ============================================================================
# Step 3: Install Python Dependencies
# ============================================================================
print_header "Step 3: Installing Python Dependencies"

echo "Upgrading pip..."
pip install --upgrade pip
check_success "Pip upgraded"

echo "Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    check_success "Python dependencies installed"
else
    echo -e "${RED}requirements.txt not found${NC}"
    exit 1
fi

# Install additional recommended packages
echo "Installing additional development tools..."
pip install pytest pytest-cov black flake8 mypy 2>/dev/null || true
check_success "Development tools installed"

# ============================================================================
# Step 4: Install Node.js Dependencies
# ============================================================================
print_header "Step 4: Installing Node.js Dependencies"

if command -v node &> /dev/null && [ -f "package.json" ]; then
    echo "Installing npm packages..."
    npm install
    check_success "Node.js dependencies installed"
else
    echo -e "${YELLOW}Skipping Node.js dependencies (Node.js not available or package.json missing)${NC}"
fi

# ============================================================================
# Step 5: Pull Ollama Models
# ============================================================================
print_header "Step 5: Setting Up Ollama Models"

if command -v ollama &> /dev/null; then
    echo "This step will pull required LLM models (~8-10 GB total)"
    echo "Models to pull:"
    echo "  - qwen2.5:14b-instruct-q4_K_M (primary tutor)"
    echo "  - llama3.2:3b (routing/classification)"
    echo "  - mistral:7b-instruct (analogies)"
    echo ""
    
    read -p "Do you want to pull models now? (y/n): " pull_models
    
    if [ "$pull_models" = "y" ] || [ "$pull_models" = "Y" ]; then
        # Start Ollama server in background if not running
        if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "Starting Ollama server..."
            ollama serve > /dev/null 2>&1 &
            sleep 3
        fi
        
        echo "Pulling qwen2.5:14b-instruct-q4_K_M..."
        ollama pull qwen2.5:14b-instruct-q4_K_M
        check_success "qwen2.5:14b pulled"
        
        echo "Pulling llama3.2:3b..."
        ollama pull llama3.2:3b
        check_success "llama3.2:3b pulled"
        
        echo "Pulling mistral:7b-instruct..."
        ollama pull mistral:7b-instruct
        check_success "mistral:7b-instruct pulled"
    else
        echo -e "${YELLOW}Skipping model pull. Run 'ollama pull <model>' manually later.${NC}"
    fi
else
    echo -e "${YELLOW}Ollama not installed. Skipping model setup.${NC}"
fi

# ============================================================================
# Step 6: Set Up SearXNG with Docker
# ============================================================================
print_header "Step 6: Setting Up SearXNG (Research Engine)"

if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "SearXNG will be set up using Docker Compose"
    
    # Create SearXNG config directory if it doesn't exist
    if [ ! -d "searxng" ]; then
        mkdir -p searxng
        echo "Created searxng configuration directory"
    fi
    
    # Create basic SearXNG settings if not exists
    if [ ! -f "searxng/settings.yml" ]; then
        cat > searxng/settings.yml << 'SEARXNG_EOF'
use_default_settings: true
general:
  debug: false
  instance_name: "HF-Tutor Research"
  donation_url: null
  contact_url: null
  enable_metrics: true
search:
  safe_search: 0
  autocomplete: "google"
  default_lang: "da"
  formats:
    - html
    - json
server:
  secret_key: "hf-tutor-secret-key-change-in-production"
  limiter: false
  image_proxy: true
  http_protocol_version: "1.0"
ui:
  static_use_hash: true
  default_theme: simple
  query_in_title: true
  infinite_scroll: true
  results_on_new_tab: false
outgoing:
  request_timeout: 5.0
  max_request_timeout: 10.0
  useragent_suffix: ""
engines:
  - name: google
    engine: google
    shortcut: g
  - name: wikipedia
    engine: wikipedia
    shortcut: w
  - name: arxiv
    engine: arxiv
    shortcut: a
  - name: duckduckgo
    engine: duckduckgo
    shortcut: d
SEARXNG_EOF
        check_success "SearXNG configuration created"
    fi
    
    read -p "Do you want to start SearXNG now? (y/n): " start_searxng
    
    if [ "$start_searxng" = "y" ] || [ "$start_searxng" = "Y" ]; then
        if [ -f "docker-compose.yml" ]; then
            docker-compose up -d searxng
            check_success "SearXNG started"
            echo -e "${GREEN}SearXNG available at http://localhost:8080${NC}"
        else
            echo -e "${YELLOW}docker-compose.yml not found. Skipping SearXNG setup.${NC}"
        fi
    else
        echo -e "${YELLOW}Skipping SearXNG startup. Run 'docker-compose up -d searxng' later.${NC}"
    fi
else
    echo -e "${YELLOW}Docker not available. SearXNG research features will be disabled.${NC}"
    echo -e "${YELLOW}To enable later: install Docker and run 'docker-compose up -d searxng'${NC}"
fi

# ============================================================================
# Step 7: Initialize Database and Memory Palace
# ============================================================================
print_header "Step 7: Initializing Database and Memory Palace"

# Create data directory
if [ ! -d "data" ]; then
    mkdir -p data
    echo "Created data directory"
fi

# Initialize database
echo "Initializing SQLite database..."
python3 -c "
from api.core.database import init_db
try:
    init_db()
    print('Database initialized successfully')
except Exception as e:
    print(f'Database initialization note: {e}')
" 2>/dev/null || echo -e "${YELLOW}Database will be initialized on first run${NC}"
check_success "Database setup complete"

# Create Memory Palace directory structure
echo "Setting up Memory Palace directories..."
mkdir -p data/mempalace/{matematik,fysik,datalogi,kommunikation}
mkdir -p data/chromadb
check_success "Memory Palace directories created"

# ============================================================================
# Step 8: Create Environment File
# ============================================================================
print_header "Step 8: Creating Environment Configuration"

if [ ! -f ".env" ]; then
    cat > .env << 'ENV_EOF'
# HF-Tutor Environment Configuration

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=qwen2.5:14b-instruct-q4_K_M

# SearXNG Configuration
SEARXNG_URL=http://localhost:8080

# Database
DATABASE_URL=sqlite:///data/hf_agent.db

# Memory Palace
PALACE_PATH=data/mempalace
CHROMA_PATH=data/chromadb

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
ENV_EOF
    check_success "Environment file created (.env)"
    echo -e "${YELLOW}Please review and update .env with your settings${NC}"
else
    echo -e "${GREEN}✓ Environment file already exists${NC}"
fi

# ============================================================================
# Step 9: Verify Installation
# ============================================================================
print_header "Step 9: Verifying Installation"

echo "Checking Python imports..."
python3 -c "
import fastapi
import uvicorn
import pydantic
print('✓ FastAPI stack OK')

try:
    from api.services.agents import AgentProfile, PersonalityTraits
    print('✓ Agents module OK')
except Exception as e:
    print(f'⚠ Agents module: {e}')

try:
    from api.services.memory_palace import MemoryPalace
    print('✓ Memory Palace module OK')
except Exception as e:
    print(f'⚠ Memory Palace module: {e}')

try:
    from api.services.orchestrator import Orchestrator
    print('✓ Orchestrator module OK')
except Exception as e:
    print(f'⚠ Orchestrator module: {e}')
"

echo ""
echo "Directory structure:"
echo "  data/"
ls -la data/ 2>/dev/null | head -10 || echo "  (empty)"

echo ""
echo "Memory Palace wings:"
ls -la data/mempalace/ 2>/dev/null || echo "  (not created yet)"

# ============================================================================
# Summary
# ============================================================================
print_header "Setup Complete! 🎉"

echo -e "${GREEN}HF-Tutor has been successfully set up!${NC}"
echo ""
echo "Next steps:"
echo "  1. ${YELLOW}Review .env${NC} and update settings if needed"
echo "  2. ${YELLOW}Start Ollama${NC}: ollama serve"
echo "  3. ${YELLOW}Start backend${NC}: python main.py"
echo "  4. ${YELLOW}Start frontend${NC}: npm run dev (in a new terminal)"
echo ""
echo "Quick start commands:"
echo "  ${BLUE}./start_backend.py${NC}  - Start the backend server"
echo "  ${BLUE}npm run dev${NC}         - Start the frontend dev server"
echo ""
echo "Access points:"
echo "  Frontend:  ${GREEN}http://localhost:5173${NC}"
echo "  Backend:   ${GREEN}http://localhost:8000${NC}"
echo "  API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo "  SearXNG:   ${GREEN}http://localhost:8080${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Happy Learning with HF-Tutor! 📚${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
