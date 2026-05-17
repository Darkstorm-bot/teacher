#!/usr/bin/env bash
# HF-Tutor Setup Script
# This script sets up the complete development environment for HF-Tutor

set -Eeuo pipefail
IFS=$'\n\t'

# Ensure we're running under bash (arrays and locals require bash). If not,
# re-exec the script with the system `bash` so the rest of the script parses
# correctly instead of producing "syntax error near unexpected token `)`".
if [ -z "${BASH_VERSION:-}" ]; then
    if command -v bash >/dev/null 2>&1; then
        exec bash "$0" "$@"
    else
        echo "This script requires bash. Please run it with bash." >&2
        exit 1
    fi
fi

trap 'echo -e "${RED}Error on line ${LINENO}: ${BASH_COMMAND}${NC}" >&2' ERR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

AUTO_YES=false
CHECK_ONLY=false
START_SERVICES=true
PYTHON_CMD=()
NODE_CMD=()
NPM_CMD=()
DOCKER_COMPOSE_CMD=()
DOCKER_PATH=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Runtime defaults (can be overridden via environment)
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
SEARXNG_URL="${SEARXNG_URL:-http://localhost:8080}"
LMSTUDIO_HOST="${LMSTUDIO_HOST:-http://127.0.01:1234/v1/}"
SEARXNG_DETECTED_URL=""
LMSTUDIO_DETECTED_URL=""

cd "$SCRIPT_DIR"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--yes|--auto-yes)
            AUTO_YES=true
            ;;
        --check-only|--dry-run)
            CHECK_ONLY=true
            ;;
        --no-start)
            START_SERVICES=false
            ;;
        --help|-h)
            cat <<'USAGE'
Usage: bash setup.sh [options]

Options:
  -y, --yes, --auto-yes   Assume yes for setup prompts
  --check-only            Validate prerequisites without making changes
  --dry-run               Alias for --check-only
    --no-start              Finish setup without launching backend/frontend
  -h, --help              Show this help text
USAGE
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
    shift
done

have_command() {
    command -v "$1" &> /dev/null
}

python_run() {
    "${PYTHON_CMD[@]}" "$@"
}

detect_python_command() {
    if have_command python3; then
        PYTHON_CMD=(python3)
    elif have_command python; then
        PYTHON_CMD=(python)
    elif have_command py; then
        PYTHON_CMD=(py -3)
    else
        echo -e "${RED}Python 3 not found. Please install Python 3.10+${NC}"
        exit 1
    fi
}

detect_docker_compose_command() {
    if [ -n "$DOCKER_PATH" ] && [ -x "$DOCKER_PATH" ]; then
        DOCKER_COMPOSE_CMD=("$DOCKER_PATH" compose)
    elif have_command docker-compose; then
        DOCKER_COMPOSE_CMD=(docker-compose)
    elif have_command docker && docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD=(docker compose)
    fi
}

detect_node_command() {
    if have_command node; then
        NODE_CMD=(node)
        if have_command npm; then
            NPM_CMD=(npm)
        fi
        return 0
    fi

    # In WSL/Git-Bash, try resolving Windows Node via cmd.exe / where.exe
    local cmd_runner=""
    if have_command cmd.exe; then
        cmd_runner="cmd.exe"
    elif [ -x "/mnt/c/Windows/System32/cmd.exe" ]; then
        cmd_runner="/mnt/c/Windows/System32/cmd.exe"
    elif [ -x "/c/Windows/System32/cmd.exe" ]; then
        cmd_runner="/c/Windows/System32/cmd.exe"
    fi

    if [ -n "$cmd_runner" ]; then
        local node_win_raw=""
        node_win_raw="$($cmd_runner /C where node 2> /dev/null | head -n 1 | tr -d '\r' || true)"
        if [ -n "$node_win_raw" ]; then
            local node_wsl_path="$node_win_raw"
            if have_command wslpath; then
                node_wsl_path="$(wslpath -u "$node_win_raw" 2> /dev/null || echo "$node_win_raw")"
            fi
            if [ -x "$node_wsl_path" ]; then
                NODE_CMD=("$node_wsl_path")
                NPM_CMD=("$cmd_runner" /C npm)
                return 0
            fi
        fi
    fi

    local node_windows=""
    node_windows=$(find_windows_exe node \
        "/mnt/c/Program Files/nodejs/node.exe" \
        "/mnt/c/Program Files (x86)/nodejs/node.exe" \
        "/c/Program Files/nodejs/node.exe" \
        "/c/Program Files (x86)/nodejs/node.exe") || true

    if [ -n "$node_windows" ]; then
        NODE_CMD=("$node_windows")
        if [ -n "$cmd_runner" ]; then
            NPM_CMD=("$cmd_runner" /C npm)
        else
            local node_dir
            node_dir="$(dirname "$node_windows")"
            if [ -x "$node_dir/npm" ]; then
                NPM_CMD=("$node_dir/npm")
            fi
        fi
        return 0
    fi

    if have_command npm; then
        NPM_CMD=(npm)
    fi

    return 1
}

# Try to locate a Windows-installed executable if `docker` or `node` aren't on PATH
find_windows_exe() {
    local name="$1"
    shift
    for p in "$@"; do
        if [ -x "$p" ]; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

prompt_yes_no() {
    local prompt_text="$1"
    local default_answer="${2:-n}"
    local answer=""

    if $AUTO_YES; then
        echo "y"
        return 0
    fi

    if [ -t 0 ]; then
        read -r -p "$prompt_text" answer
    else
        answer="$default_answer"
    fi

    echo "${answer:-$default_answer}"
}

normalize_model_name() {
    local model_name="$1"
    echo "${model_name%%:*}"
}

model_is_installed() {
    local desired_model_name
    desired_model_name="$(normalize_model_name "$1")"

    if ! have_command ollama; then
        return 1
    fi

    while IFS= read -r installed_model; do
        [ "$(normalize_model_name "$installed_model")" = "$desired_model_name" ] && return 0
    done < <(ollama list 2>/dev/null | awk 'NR>1 {print $1}')

    return 1
}

wait_for_url() {
    local url="$1"
    local attempts="${2:-15}"
    local delay_seconds="${3:-2}"

    if ! have_command curl; then
        return 1
    fi

    for ((attempt=1; attempt<=attempts; attempt++)); do
        if curl -fsS "$url" > /dev/null 2>&1; then
            return 0
        fi
        sleep "$delay_seconds"
    done

    return 1
}

python_exec_works() {
    local py="$1"
    if [ -z "$py" ]; then
        return 1
    fi
    "$py" -c "import sys" > /dev/null 2>&1
}

detect_lmstudio_url() {
    LMSTUDIO_DETECTED_URL=""
    local wsl_host_ip=""
    if [ -f "/etc/resolv.conf" ]; then
        wsl_host_ip="$(awk '/^nameserver / {print $2; exit}' /etc/resolv.conf 2>/dev/null || true)"
    fi

    if wait_for_url "http://127.0.0.1:1234/v1/models" 1 1 || wait_for_url "http://127.0.0.1:1234" 1 1; then
        LMSTUDIO_DETECTED_URL="http://127.0.0.1:1234"
    elif wait_for_url "http://localhost:1234/v1/models" 1 1 || wait_for_url "http://localhost:1234" 1 1; then
        LMSTUDIO_DETECTED_URL="http://localhost:1234"
    elif wait_for_url "http://host.docker.internal:1234/v1/models" 1 1 || wait_for_url "http://host.docker.internal:1234" 1 1; then
        LMSTUDIO_DETECTED_URL="http://host.docker.internal:1234"
    elif [ -n "$wsl_host_ip" ] && (wait_for_url "http://${wsl_host_ip}:1234/v1/models" 1 1 || wait_for_url "http://${wsl_host_ip}:1234" 1 1); then
        LMSTUDIO_DETECTED_URL="http://${wsl_host_ip}:1234"
    elif wait_for_url "http://localhost:8081/v1/models" 1 1 || wait_for_url "http://localhost:8081" 1 1; then
        LMSTUDIO_DETECTED_URL="http://localhost:8081"
    elif wait_for_url "http://localhost:8080/v1/models" 1 1 || wait_for_url "http://localhost:8080" 1 1; then
        # 8080 may be used by other services; this is fallback-only
        LMSTUDIO_DETECTED_URL="http://localhost:8080"
    fi

    [ -n "$LMSTUDIO_DETECTED_URL" ]
}

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     HF-Tutor Setup Script             ║${NC}"
echo -e "${BLUE}║  Multi-Agent AI Tutoring System       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if running in correct directory
if [ ! -f "main.py" ] || [ ! -f "requirements.txt" ] || [ ! -f "package.json" ]; then
    echo -e "${RED}Error: Please run this script from the app root directory${NC}"
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

detect_python_command
detect_node_command || true
detect_docker_compose_command || true

# Create virtual environment using multiple fallbacks to avoid 'py' issues
create_venv() {
    # Try the detected python command first
    if [ ${#PYTHON_CMD[@]} -gt 0 ]; then
        if "${PYTHON_CMD[@]}" -m venv venv 2>/dev/null; then
            return 0
        fi
    fi

    # Try common python executables explicitly
    if have_command python3; then
        if python3 -m venv venv 2>/dev/null; then
            return 0
        fi
    fi
    if have_command python; then
        if python -m venv venv 2>/dev/null; then
            return 0
        fi
    fi
    # Windows py launcher
    if have_command py; then
        if py -3 -m venv venv 2>/dev/null; then
            return 0
        fi
    fi

    return 1
}

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================
print_header "Step 1: Checking Prerequisites"

echo "Detecting Python..."
PYTHON_VERSION="$("${PYTHON_CMD[@]}" --version 2>&1 | awk '{print $2}' || true)"
echo -e "Python version: ${GREEN}${PYTHON_VERSION:-unknown}${NC}"

if have_command node; then
    NODE_VERSION=$(node --version)
    echo -e "Node.js version: ${GREEN}$NODE_VERSION${NC}"
else
    if [ ${#NODE_CMD[@]} -gt 0 ]; then
        NODE_VERSION=$("${NODE_CMD[@]}" --version 2>/dev/null | tr -d '\r' || true)
        if [ -n "$NODE_VERSION" ]; then
            echo -e "Node.js version: ${GREEN}${NODE_VERSION}${NC} (found at ${NODE_CMD[*]})"
        else
            echo -e "${GREEN}Node.js detected${NC} (found at ${NODE_CMD[*]})"
        fi
    else
        echo -e "${YELLOW}Node.js not found. Frontend features will be limited.${NC}"
    fi
fi

if have_command docker; then
    DOCKER_VERSION=$(docker --version 2>/dev/null || true)
    echo -e "Docker version: ${GREEN}${DOCKER_VERSION:-unknown}${NC}"
else
    # Try common Windows Docker paths
    DOCKER_FALLBACK=$(find_windows_exe docker "/c/Program Files/Docker/Docker/resources/bin/docker.exe" "/c/Program Files/Docker/Docker/docker.exe" "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe" ) || true
    if [ -n "$DOCKER_FALLBACK" ]; then
        DOCKER_VERSION=$("$DOCKER_FALLBACK" --version 2>/dev/null || true)
        echo -e "Docker version: ${GREEN}${DOCKER_VERSION:-unknown}${NC} (found at $DOCKER_FALLBACK)"
        # export a wrapper so other code uses this path
        DOCKER_PATH="$DOCKER_FALLBACK"
        DOCKER_COMPOSE_CMD=("$DOCKER_PATH" compose)
    else
        echo -e "${YELLOW}Docker not found. SearXNG research features will be disabled.${NC}"
    fi
fi

if have_command ollama; then
    OLLAMA_VERSION=$(ollama --version 2>/dev/null || true)
    echo -e "Ollama version: ${GREEN}${OLLAMA_VERSION:-unknown}${NC}"
else
    echo -e "${YELLOW}Ollama not found. Ollama-dependent features will be disabled.${NC}"
fi

check_success "Prerequisites check completed"

# ============================================================================
# Step 2: Create Virtual Environment
# ============================================================================
print_header "Step 2: Setting Up Python Virtual Environment"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    if create_venv; then
        check_success "Virtual environment created"
    else
        echo -e "${RED}Failed to create virtual environment with available Python interpreters.${NC}"
        exit 1
    fi
else
    # Check if venv appears valid and runnable in current shell
    if ! python_exec_works "venv/bin/python" && ! python_exec_works "venv/Scripts/python.exe"; then
        echo -e "${YELLOW}Existing 'venv' directory found but no python executable detected. Recreating venv...${NC}"
        rm -rf venv
        if create_venv; then
            check_success "Virtual environment (re)created"
        else
            echo -e "${RED}Failed to recreate virtual environment.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Virtual environment already exists${NC}"
    fi
fi

# Activate virtual environment (portable for Unix and Windows-generated venvs)
echo "Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    # Unix/macOS layout
    # shellcheck disable=SC1091
    # shellcheck disable=SC1090
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    # Windows layout
    # shellcheck disable=SC1091
    # Use bash-friendly path if running under Git Bash / MSYS
    if [[ -n "${MSYSTEM:-}" || "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* ]]; then
        source "venv/Scripts/activate"
    else
        # If not running under a Unix-like shell, attempt to fallback to `py -3 -m venv` activation
        source "venv/Scripts/activate"
    fi
else
    echo -e "${YELLOW}Activation script not found; you may need to activate the venv manually:${NC}"
    echo "  source venv/bin/activate   # Unix"
    echo "  venv\\Scripts\\activate   # Windows PowerShell"
fi

check_success "Virtual environment activated (or activation instructions provided)"

# ============================================================================
# Step 3: Install Python Dependencies
# ============================================================================
print_header "Step 3: Installing Python Dependencies"

if $CHECK_ONLY; then
    echo "Check-only mode: skipping pip upgrade and dependency installation."
else

# Determine the Python executable currently on PATH (should be venv's after activation)
if python_exec_works "venv/bin/python"; then
    VENV_PYTHON="venv/bin/python"
elif python_exec_works "venv/Scripts/python.exe"; then
    VENV_PYTHON="venv/Scripts/python.exe"
else
    VENV_PYTHON="$(python -c 'import sys; print(sys.executable)' 2>/dev/null || true)"
    if ! python_exec_works "$VENV_PYTHON"; then
        VENV_PYTHON=""
    fi
    if [ -z "$VENV_PYTHON" ]; then
        VENV_PYTHON="${PYTHON_CMD[0]}"
    fi
fi
PIP_CMD=("$VENV_PYTHON" -m pip)

echo "Upgrading pip..."
# Use venv pip; if system blocks installs, suggest --break-system-packages to user instead of forcing it here
"${PIP_CMD[@]}" install --upgrade pip setuptools wheel
check_success "Pip upgraded"

echo "Installing requirements..."
if [ -f "requirements.txt" ]; then
    "${PIP_CMD[@]}" install -r requirements.txt
    check_success "Python dependencies installed"
else
    echo -e "${RED}requirements.txt not found${NC}"
    exit 1
fi

# Install additional recommended packages (non-fatal)
echo "Installing optional development tools (non-fatal)..."
"${PIP_CMD[@]}" install pytest pytest-cov black flake8 mypy || true
echo -e "${GREEN}Optional development tools step completed (errors ignored)${NC}"
fi

# ============================================================================
# Step 4: Install Node.js Dependencies
# ============================================================================
print_header "Step 4: Installing Node.js Dependencies"

if $CHECK_ONLY; then
    if [ ${#NODE_CMD[@]} -gt 0 ]; then
        echo "Check-only mode: Node.js detected (${NODE_CMD[*]}), skipping npm install."
    else
        echo -e "${YELLOW}Check-only mode: Node.js not detected; skipping npm install.${NC}"
    fi
elif [ ${#NODE_CMD[@]} -gt 0 ] && [ -f "package.json" ]; then
    echo "Installing frontend packages..."
    if have_command pnpm && [ -f "pnpm-lock.yaml" ]; then
        pnpm install
    elif have_command yarn && [ -f "yarn.lock" ]; then
        yarn install
    elif [ ${#NPM_CMD[@]} -gt 0 ]; then
        "${NPM_CMD[@]}" install
    else
        echo -e "${YELLOW}npm not available in this shell; skipping frontend install.${NC}"
    fi
    check_success "Node.js dependencies installed"
else
    echo -e "${YELLOW}Skipping Node.js dependencies (Node.js not available or package.json missing)${NC}"
fi

# ============================================================================
# Step 5: Pull Ollama Models
# ============================================================================
print_header "Step 5: Setting Up Ollama / LMStudio Models"

# Detect LMStudio before model setup so we can treat it as a valid provider even without Ollama CLI
if [ -z "${LMSTUDIO_HOST_OVERRIDE:-}" ] && detect_lmstudio_url; then
    echo -e "${GREEN}Detected LMStudio responding at ${LMSTUDIO_DETECTED_URL}${NC}"
fi

# Proceed if Ollama CLI is present, or Ollama HTTP server responds, or LMStudio detected
if have_command ollama || wait_for_url "${OLLAMA_HOST}/api/tags" 1 1 || [ -n "$LMSTUDIO_DETECTED_URL" ]; then
    models_to_pull=(
        "qwen2.5:14b-instruct-q4_K_M"
        "llama3.2:3b"
        "mistral:7b-instruct"
    )

    echo "This step can pull required LLM models (several GB)."
    if $CHECK_ONLY; then
        echo "Check-only mode: listing installed models..."
        if have_command ollama; then
            ollama list || true
        elif [ -n "$LMSTUDIO_DETECTED_URL" ]; then
            echo "LMStudio detected at $LMSTUDIO_DETECTED_URL — querying available models..."
            curl -fsS "$LMSTUDIO_DETECTED_URL/api/models" 2>/dev/null || echo "No model list endpoint available"
        else
            curl -fsS "${OLLAMA_HOST}/api/tags" 2>/dev/null || echo "Ollama HTTP endpoint not responding"
        fi
    else
        pull_now=$(prompt_yes_no "Pull models now? (y/N): " n)
        if [[ "$pull_now" =~ ^[Yy]$ ]]; then
            # Ensure Ollama is reachable, attempt to start if available but not running
            # Prefer LMStudio if configured
            if [ -n "$LMSTUDIO_DETECTED_URL" ]; then
                echo "LMStudio detected at $LMSTUDIO_DETECTED_URL; model management may differ. Please use LMStudio UI to install models."
            else
                if have_command ollama; then
                    if ! wait_for_url "${OLLAMA_HOST}/api/tags" 3 1; then
                        echo "Ollama not responding at ${OLLAMA_HOST}. Attempting 'ollama serve' in background..."
                        ollama serve > /dev/null 2>&1 &
                        sleep 3
                    fi

                    for m in "${models_to_pull[@]}"; do
                        if model_is_installed "$m"; then
                            echo -e "${GREEN}$m already installed${NC}"
                            continue
                        fi
                        echo "Pulling $m..."
                        ollama pull "$m" || { echo -e "${YELLOW}Failed pulling $m (continue)${NC}"; }
                    done
                else
                    echo -e "${YELLOW}Ollama CLI not found; cannot pull models automatically. Use LMStudio or the Ollama CLI to install models.${NC}"
                fi
            fi
            echo -e "${GREEN}Model pull step finished (errors ignored)${NC}"
        else
            echo -e "${YELLOW}Skipping model pull. Run 'ollama pull <model>' manually later.${NC}"
        fi
    fi
else
    echo -e "${YELLOW}No Ollama CLI or HTTP endpoint detected and no LMStudio found. Skipping model setup.${NC}"
fi

# ============================================================================
# Step 6: Set Up SearXNG with Docker
# ============================================================================
print_header "Step 6: Setting Up SearXNG (Research Engine)"
detect_docker_compose_command

# Detect an existing SearXNG instance (common custom port 8001, then 8080)
SEARXNG_DETECTED_URL=""
if wait_for_url "http://localhost:8001" 2 1; then
    SEARXNG_DETECTED_URL="http://localhost:8001"
    echo -e "${GREEN}Detected SearXNG responding at ${SEARXNG_DETECTED_URL}${NC}"
elif wait_for_url "http://localhost:8080" 2 1; then
    SEARXNG_DETECTED_URL="http://localhost:8080"
    echo -e "${GREEN}Detected SearXNG responding at ${SEARXNG_DETECTED_URL}${NC}"
fi

# Detect LMStudio (optional local LLM UI) if not already detected in Step 5
if [ -z "$LMSTUDIO_DETECTED_URL" ] && [ -z "${LMSTUDIO_HOST_OVERRIDE:-}" ] && detect_lmstudio_url; then
    echo -e "${GREEN}Detected LMStudio responding at ${LMSTUDIO_DETECTED_URL}${NC}"
fi
if [ ${#DOCKER_COMPOSE_CMD[@]} -gt 0 ]; then
    echo "SearXNG will be set up using Docker Compose (${DOCKER_COMPOSE_CMD[*]})"

        # If SearXNG is already running, skip startup and inform the user
        if [ -n "$SEARXNG_DETECTED_URL" ]; then
                echo -e "${GREEN}SearXNG already running at ${SEARXNG_DETECTED_URL}; skipping Docker startup.${NC}"
        else
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

        if $CHECK_ONLY; then
            echo "Check-only mode: skipping SearXNG Docker startup prompt."
        else
            start_searxng=$(prompt_yes_no "Start SearXNG now using Docker Compose? (y/N): " n)
            if [[ "$start_searxng" =~ ^[Yy]$ ]]; then
                if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; then
                    echo "Using compose file to start searxng..."
                    "${DOCKER_COMPOSE_CMD[@]}" up -d searxng || echo -e "${YELLOW}Docker compose up returned non-zero (check logs)${NC}"
                    echo -e "${GREEN}SearXNG start attempted; check http://localhost:8080${NC}"
                else
                    echo -e "${YELLOW}docker-compose.yml not found. Creating a minimal compose file (searxng only).${NC}"
                    cat > docker-compose.searxng.yml << 'YAML_EOF'
version: '3.8'
services:
    searxng:
    image: searxng/searxng:latest
    container_name: searxng
    ports:
        - "8080:8080"
    volumes:
        - ./searxng/settings.yml:/etc/searxng/settings.yml:ro
    restart: unless-stopped
YAML_EOF
                    "${DOCKER_COMPOSE_CMD[@]}" -f docker-compose.searxng.yml up -d || echo -e "${YELLOW}Failed to start SearXNG via temporary compose file${NC}"
                    echo -e "${GREEN}SearXNG start attempted; check http://localhost:8080${NC}"
                fi
            else
                echo -e "${YELLOW}Skipping SearXNG startup. Run '${DOCKER_COMPOSE_CMD[*]} up -d searxng' later.${NC}"
            fi
        fi
        fi
else
        echo -e "${YELLOW}Docker or docker-compose not available. SearXNG research features will be disabled.${NC}"
        echo -e "${YELLOW}To enable later: install Docker and run 'docker compose up -d searxng' or 'docker-compose up -d searxng'${NC}"
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
if $CHECK_ONLY; then
    echo "Check-only: skipping DB init"
else
    if python_run - <<'PY'
from api.core.database import init_db
try:
    init_db()
    print('Database initialized successfully')
except Exception as e:
    print('Database initialization note:', e)
PY
    then
        check_success "Database setup complete"
    else
        echo -e "${YELLOW}Database initialization had issues; it will be initialized on first run${NC}"
    fi
fi

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
    # Prefer detected SearXNG URL if present (from earlier checks)
    if [ -n "$SEARXNG_DETECTED_URL" ]; then
        DEFAULT_SEARXNG_URL="$SEARXNG_DETECTED_URL"
    else
        DEFAULT_SEARXNG_URL="http://localhost:8080"
    fi

    # Prefer explicit LMStudio override, then detected host if present
    if [ -n "${LMSTUDIO_HOST_OVERRIDE:-}" ]; then
        DEFAULT_LMSTUDIO_URL="$LMSTUDIO_HOST_OVERRIDE"
    elif [ -n "$LMSTUDIO_DETECTED_URL" ]; then
        DEFAULT_LMSTUDIO_URL="$LMSTUDIO_DETECTED_URL"
    else
        DEFAULT_LMSTUDIO_URL=""
    fi

    cat > .env << ENV_EOF
# HF-Tutor Environment Configuration

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=qwen2.5:14b-instruct-q4_K_M

# SearXNG Configuration
SEARXNG_URL=${DEFAULT_SEARXNG_URL}
LMSTUDIO_HOST=${DEFAULT_LMSTUDIO_URL}

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
python_run - <<'PY'
import importlib
modules = ['fastapi', 'uvicorn', 'pydantic']
ok = True
for m in modules:
    try:
        importlib.import_module(m)
        print(f'✓ {m} OK')
    except Exception as e:
        print(f'⚠ {m}: {e}')
        ok = False

for modpath in ['api.services.agents', 'api.services.memory_palace', 'api.services.orchestrator']:
    try:
        importlib.import_module(modpath)
        print(f'✓ {modpath} OK')
    except Exception as e:
        print(f'⚠ {modpath}: {e}')
        ok = False

if not ok:
    print('One or more imports failed; please check the stack and pip packages.')
PY

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
echo -e "  1. ${YELLOW}Review .env${NC} and update settings if needed"
echo -e "  2. ${YELLOW}Start Ollama${NC}: ollama serve"
echo -e "  3. ${YELLOW}Start backend${NC}: python main.py"
echo -e "  4. ${YELLOW}Start frontend${NC}: npm run dev (in a new terminal)"
echo ""
echo "Quick start commands:"
echo -e "  ${BLUE}./start_backend.py${NC}  - Start the backend server"
echo -e "  ${BLUE}npm run dev${NC}         - Start the frontend dev server"
echo ""
echo "Access points:"
echo -e "  Frontend:  ${GREEN}http://localhost:5173${NC}"
echo -e "  Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "  API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
if [ -n "$SEARXNG_DETECTED_URL" ]; then
    echo -e "  SearXNG:   ${GREEN}${SEARXNG_DETECTED_URL}${NC}"
else
    echo -e "  SearXNG:   ${GREEN}http://localhost:8080${NC}"
fi

if $CHECK_ONLY || ! $START_SERVICES; then
    echo ""
    echo -e "${BLUE}Setup finished without launching dev servers.${NC}"
    echo -e "${BLUE}Use --no-start to skip auto-launch in the future.${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Happy Learning with HF-Tutor! 📚${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}Starting backend and frontend dev servers...${NC}"

cleanup_services() {
    echo ""
    echo -e "${YELLOW}Stopping dev servers...${NC}"
    if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
}

trap cleanup_services INT TERM EXIT

if [ -x "venv/bin/python" ]; then
    BACKEND_CMD=("venv/bin/python" "start_backend.py")
elif [ -x "venv/Scripts/python.exe" ]; then
    BACKEND_CMD=("venv/Scripts/python.exe" "start_backend.py")
else
    BACKEND_CMD=("${PYTHON_CMD[@]}" "start_backend.py")
fi

if [ ${#NPM_CMD[@]} -eq 0 ]; then
    echo -e "${RED}npm command was not detected, so the frontend cannot be started automatically.${NC}"
    echo -e "${YELLOW}You can still run it manually with 'npm run dev'.${NC}"
    trap - INT TERM EXIT
    exit 1
fi

"${BACKEND_CMD[@]}" > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}Backend started in background (PID ${BACKEND_PID}), logging to backend.log${NC}"

"${NPM_CMD[@]}" run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started in background (PID ${FRONTEND_PID}), logging to frontend.log${NC}"

echo ""
echo "Waiting for backend and frontend to become reachable..."
if wait_for_url "http://localhost:8000/api/v1/health" 30 2; then
    echo -e "${GREEN}Backend is reachable at http://localhost:8000/api/v1/health${NC}"
else
    echo -e "${YELLOW}Backend did not become reachable in time. Check backend.log${NC}"
    cleanup_services
    exit 1
fi

FRONTEND_HOSTS=("http://localhost:5173" "http://localhost:3000")
FRONTEND_REACHABLE=""
for h in "${FRONTEND_HOSTS[@]}"; do
    if wait_for_url "$h" 30 2; then
        echo -e "${GREEN}Frontend is reachable at ${h}${NC}"
        FRONTEND_REACHABLE="$h"
        break
    fi
done
if [ -z "$FRONTEND_REACHABLE" ]; then
    echo -e "${YELLOW}Frontend did not become reachable in time. Check frontend.log${NC}"
    cleanup_services
    exit 1
fi

echo ""
echo -e "${BLUE}Services are running. Press Ctrl+C to stop both.${NC}"
wait "$BACKEND_PID" "$FRONTEND_PID"

trap - INT TERM EXIT
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Happy Learning with HF-Tutor! 📚${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
