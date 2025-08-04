#!/bin/bash

# IBKR Portfolio Rebalancer Setup Script
# Usage: curl -fsSL https://raw.githubusercontent.com/your-org/ibkr-portfolio-rebalancer/main/setup.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  IBKR Portfolio Rebalancer Setup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Detect Docker Compose command
get_docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null; then
        echo "docker compose"
    else
        print_error "Neither 'docker-compose' nor 'docker compose' is available"
        exit 1
    fi
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}


# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if Docker is installed
check_docker() {
    print_step "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        print_info "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_warning "Docker daemon is not running. Attempting to start..."
        systemctl start docker
        sleep 5
        if ! docker info &> /dev/null; then
            print_error "Failed to start Docker daemon. Please check Docker installation."
            exit 1
        fi
    fi
    
    print_success "Docker is installed and running!"
}

# System updates
update_system() {
    print_step "Updating system packages..."
    
    # Set debconf to non-interactive mode to avoid prompts
    export DEBIAN_FRONTEND=noninteractive
    
    # Update package lists
    apt-get update -qq
    
    # Install git if not present
    if ! command -v git &> /dev/null; then
        print_info "Installing git..."
        apt-get install -y git
    fi
    
    # Upgrade packages silently with automatic yes to all prompts
    apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qq
    
    print_success "System updated successfully!"
}

# Create directory structure
create_directories() {
    print_step "Creating directory structure..."
    
    # Create base directory
    mkdir -p /home/docker/zehnlabs
    cd /home/docker/zehnlabs
    
    print_success "Directory /home/docker/zehnlabs created and set as working directory"
}

# Clone repository
clone_repository() {
    print_step "Cloning IBKR Portfolio Rebalancer repository..."
    
    if [ -d "ibkr-portfolio-rebalancer" ]; then
        print_warning "Repository directory already exists. Removing and re-cloning..."
        rm -rf ibkr-portfolio-rebalancer
    fi
    
    git clone https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer.git
    cd ibkr-portfolio-rebalancer
    
    print_success "Repository cloned successfully!"
}

# Create placeholder configuration files
create_placeholder_files() {
    print_step "Creating placeholder configuration files..."
    
    # Copy .env.example to .env if .env doesn't exist (required for Docker mount)
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_info "Created .env from template (.env.example)"
        else
            print_error ".env.example not found - cannot create initial environment configuration"
            exit 1
        fi
    fi
    
    # Create empty accounts.yaml file if it doesn't exist (required for Docker mount)
    if [ ! -f "accounts.yaml" ]; then
        touch accounts.yaml
        print_info "Created empty accounts.yaml file"
    fi
    
    print_success "Configuration files ready for Docker mounts"
}

# Start initial services (Redis and Management Service only)
start_initial_services() {
    print_step "Starting Redis and Management Service..."
    
    print_info "Building and starting initial services..."
    $DOCKER_COMPOSE_CMD up --build -d redis management-service
    
    print_info "Waiting for services to start..."
    sleep 10
    
    # Check if services are running
    if $DOCKER_COMPOSE_CMD ps redis | grep -q "Up" && $DOCKER_COMPOSE_CMD ps management-service | grep -q "Up"; then
        print_success "Initial services started successfully!"
    else
        print_error "Failed to start initial services. Please check the logs."
        exit 1
    fi
}

# Display setup completion instructions
display_setup_instructions() {
    echo ""
    print_success "Initial services started successfully!"
    echo ""
    print_info "=== Complete Setup via Web Interface ==="
    echo ""
    
    # Get the server's public IP address
    SERVER_IP=$(curl -s https://api.ipify.org 2>/dev/null || curl -s https://ipv4.icanhazip.com 2>/dev/null || echo "YOUR_SERVER_IP")
    
    print_info "To continue setup:"
    echo ""
    print_info "1. Set up SSH port forwarding (from your local machine):"
    print_info "   ssh -L 8000:localhost:8000 -L 8080:localhost:8080 root@$SERVER_IP"
    echo ""
    print_info "2. Open your browser and navigate to:"
    print_info "   http://localhost:8000/setup"
    echo ""
    print_info "3. Complete the configuration and click 'Complete Install'"
    echo ""
    print_success "Setup script completed. Continue in your web browser."
}



# Set up file permissions
setup_permissions() {
    print_step "Setting up file permissions..."
    
    # Make scripts executable
    chmod +x setup.sh
    if [ -f "reload.sh" ]; then
        chmod +x reload.sh
    fi
    if [ -d "tools" ]; then
        chmod +x tools/*.sh
    fi
    
    # Set proper ownership (assuming the user who will run this)
    if [ -n "$SUDO_USER" ]; then
        chown -R "$SUDO_USER:$SUDO_USER" .
        print_info "Changed ownership to $SUDO_USER"
    fi
    
    print_success "Permissions configured!"
}



# Main execution
main() {
    print_header
    
    # Set Docker Compose command
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    print_info "Using Docker Compose command: $DOCKER_COMPOSE_CMD"
    
    check_root
    check_docker
    update_system
    create_directories
    clone_repository
    setup_permissions
    create_placeholder_files
    start_initial_services
    display_setup_instructions
}

# Run main function
main "$@"