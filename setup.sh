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

# Rename configuration files
rename_config_files() {
    print_step "Setting up configuration files..."
    
    # Rename .env.example to .env
    if [ -f ".env.example" ]; then
        if [ ! -f ".env" ]; then
            mv .env.example .env
            print_info "Renamed .env.example to .env"
        else
            print_warning ".env already exists, keeping existing file"
        fi
    else
        print_error ".env.example not found - cannot create initial environment configuration"
        exit 1
    fi
    
    # Rename accounts.example.yaml to accounts.yaml
    if [ -f "accounts.example.yaml" ]; then
        if [ ! -f "accounts.yaml" ]; then
            mv accounts.example.yaml accounts.yaml
            print_info "Renamed accounts.example.yaml to accounts.yaml"
        else
            print_warning "accounts.yaml already exists, keeping existing file"
        fi
    else
        print_error "accounts.example.yaml not found - cannot create initial accounts configuration"
        exit 1
    fi
    
    print_success "Configuration files are ready for editing"
}

# Show documentation links and wait for user
show_documentation_and_wait() {
    print_step "Configuration Required"
    
    echo ""
    echo "=== CONFIGURATION REQUIRED ==="
    echo ""
    echo "Before proceeding, you need to edit two configuration files:"
    echo "  • .env (credentials and API keys)"
    echo "  • accounts.yaml (IBKR account settings)"
    echo ""
    echo "📖 Please follow the complete setup guide:"
    echo "   https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/blob/main/docs/editing-configuration.md"
    echo ""
    echo "📝 Once you have followed the guide and edited both files, press ENTER to continue..."
    
    # Read from /dev/tty to work with piped execution
    read -r < /dev/tty
}

# Start all services and verify
start_all_services() {
    print_step "Starting all services..."
    
    print_info "Building and starting Docker containers..."
    $DOCKER_COMPOSE_CMD up --build -d
    
    print_info "Waiting for services to initialize (this may take 2-3 minutes)..."
    
    # Wait progressively with status updates
    for i in {1..6}; do
        sleep 10
        print_info "Still initializing... ($((i*10))/60 seconds)"
    done
    
    # Check if all critical services are running
    print_step "Verifying services..."
    
    SERVICES=("redis" "ibkr-gateway" "event-broker" "event-processor" "management-service" "dozzle")
    ALL_RUNNING=true
    
    for service in "${SERVICES[@]}"; do
        if $DOCKER_COMPOSE_CMD ps "$service" 2>/dev/null | grep -q "Up\|running"; then
            print_success "✓ $service is running"
        else
            print_error "✗ $service is not running"
            ALL_RUNNING=false
        fi
    done
    
    if [ "$ALL_RUNNING" = false ]; then
        print_error "Some services failed to start. Check logs with: $DOCKER_COMPOSE_CMD logs"
        exit 1
    fi
    
    print_success "All services started successfully!"
}

# Display final instructions
display_final_instructions() {
    echo ""
    print_success "🎉 Installation Complete!"
    echo ""
    print_info "=== Access Your Services ==="
    echo ""    
   
    echo "🔗 IMPORTANT: Port Forwarding"
    echo "   To access these services securely, you need SSH port forwarding configured."
    echo "   📖 Setup Guide: https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/blob/main/docs/install/port-forwarding-setup.md"
    echo ""
    echo "📊 Manage Containers and View Logs:"
    echo "   http://localhost:8080"
    echo ""
    echo "🔧 Management API:"
    echo "   http://localhost:8000"
    echo ""
    echo "✅ Next Steps:"
    echo "📱 Set up Mobile/Desktop Notifications:"
    echo "   https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/blob/main/docs/user-notifications.md"
    echo ""
    print_success "Your IBKR Portfolio Rebalancer is now running!"
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
    rename_config_files
    show_documentation_and_wait
    start_all_services
    display_final_instructions
}

# Run main function
main "$@"