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

# System updates
update_system() {
    print_step "Updating system packages..."
    
    # Set debconf to non-interactive mode to avoid prompts
    export DEBIAN_FRONTEND=noninteractive
    
    # Update package lists
    apt-get update -qq
    
    # Upgrade packages silently with automatic yes to all prompts
    apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qq
    
    # Start and enable Docker (in case it's not running)
    systemctl start docker
    systemctl enable docker
    
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
    
    git clone https://github.com/fintech-zehnlabs-com/ibkr-portfolio-rebalancer.git
    cd ibkr-portfolio-rebalancer
    
    print_success "Repository cloned successfully!"
}

# Start initial services (Redis and Management Service only)
start_initial_services() {
    print_step "Starting Redis and Management Service..."
    
    print_info "Building and starting initial services..."
    docker-compose up --build -d redis management-service
    
    print_info "Waiting for services to start..."
    sleep 10
    
    # Check if services are running
    if docker-compose ps redis | grep -q "Up" && docker-compose ps management-service | grep -q "Up"; then
        print_success "Initial services started successfully!"
    else
        print_error "Failed to start initial services. Please check the logs."
        exit 1
    fi
}

# Wait for user to complete account setup
wait_for_account_setup() {
    echo ""
    print_info "=== Account Setup Required ==="
    echo ""
    print_info "Please follow these steps to complete the setup:"
    echo ""
    print_info "1. Set up SSH port forwarding to access the management interface:"
    print_info "   ssh -L 8000:localhost:8000 your-username@your-server-ip"
    echo ""
    print_info "2. Open your web browser and navigate to:"
    print_info "   http://localhost:8000/setup"
    echo ""
    print_info "3. Complete the environment and account configuration"
    echo ""
    print_info "4. Once you've completed the setup, return here and press ENTER to continue"
    echo ""
    
    read -p "Press ENTER when you have completed the setup..." 
}

# Verify configuration files exist
verify_configuration() {
    print_step "Verifying configuration files..."
    
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please complete the account setup first."
        exit 1
    fi
    
    if [ ! -f "accounts.yaml" ]; then
        print_error "accounts.yaml file not found. Please complete the account setup first."
        exit 1
    fi
    
    print_success "Configuration files verified!"
}

# Stop initial services and start full stack
start_full_services() {
    print_step "Stopping initial services and starting full system..."
    
    print_info "Stopping Redis and Management Service..."
    docker-compose down
    
    print_info "Starting all services..."
    docker-compose up -d
    
    print_info "Waiting for all services to start..."
    sleep 15
    
    print_success "All services started successfully!"
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


# Display final information
display_final_info() {
    echo ""
    print_success "🎉 Congratulations! IBKR Portfolio Rebalancer setup completed successfully!"
    echo ""
    print_info "=== Service URLs ==="
    print_info "Management Dashboard: http://localhost:8000"
    print_info "Health Check: http://localhost:8000/health"
    print_info "Container Monitoring: http://localhost:8080 (Dozzle)"
    print_info "VNC Access (IBKR Gateway): http://localhost:6080"
    echo ""
    print_info "=== Useful Commands ==="
    print_info "View logs: docker-compose logs -f"
    print_info "Stop services: docker-compose down"
    print_info "Restart services: docker-compose restart"
    print_info "Manual rebalance: ./tools/rebalance.sh -all"
    echo ""
    print_info "=== Next Steps ==="
    print_info "1. Monitor your containers and logs at http://localhost:8080"
    print_info "2. Check system health at http://localhost:8000/health"
    print_info "3. Access VNC at http://localhost:6080 to complete IBKR Gateway login if needed"
    echo ""
    print_success "Your portfolio rebalancing system is now ready!"
}

# Main execution
main() {
    print_header
    
    check_root
    update_system
    create_directories
    clone_repository
    setup_permissions
    start_initial_services
    wait_for_account_setup
    verify_configuration
    start_full_services
    display_final_info
}

# Run main function
main "$@"