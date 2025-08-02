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

# Function to prompt user input with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local is_secret="${4:-false}"
    
    if [ "$is_secret" = "true" ]; then
        echo -n -e "${YELLOW}$prompt${NC}"
        if [ -n "$default" ]; then
            echo -n " [default: ***]: "
        else
            echo -n ": "
        fi
        read -s user_input
        echo "" # New line after secret input
    else
        echo -n -e "${YELLOW}$prompt${NC}"
        if [ -n "$default" ]; then
            echo -n " [default: $default]: "
        else
            echo -n ": "
        fi
        read user_input
    fi
    
    if [ -z "$user_input" ]; then
        user_input="$default"
    fi
    
    eval "$var_name='$user_input'"
}

# Function to validate required fields
validate_required() {
    local value="$1"
    local field_name="$2"
    
    if [ -z "$value" ]; then
        print_error "$field_name is required and cannot be empty."
        return 1
    fi
    return 0
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
    mkdir -p /opt/docker/zehnlabs
    cd /opt/docker/zehnlabs
    
    print_success "Directory /opt/docker/zehnlabs created and set as working directory"
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

# Configure environment variables
configure_environment() {
    print_step "Configuring environment variables..."
    
    echo ""
    print_info "Please provide the following configuration values:"
    echo ""
    
    # Required variables
    print_info "=== Required Configuration ==="
    
    while true; do
        prompt_with_default "Interactive Brokers Username" "" "IB_USERNAME"
        if validate_required "$IB_USERNAME" "IB Username"; then
            break
        fi
    done
    
    while true; do
        prompt_with_default "Interactive Brokers Password" "" "IB_PASSWORD" "true"
        if validate_required "$IB_PASSWORD" "IB Password"; then
            break
        fi
    done
    
    while true; do
        prompt_with_default "Trading Mode (live/paper)" "paper" "TRADING_MODE"
        if [[ "$TRADING_MODE" == "live" || "$TRADING_MODE" == "paper" ]]; then
            break
        else
            print_error "Trading mode must be either 'live' or 'paper'"
        fi
    done
    
    while true; do
        prompt_with_default "Rebalance Event Subscription API Key" "" "REBALANCE_EVENT_SUBSCRIPTION_API_KEY" "true"
        if validate_required "$REBALANCE_EVENT_SUBSCRIPTION_API_KEY" "Rebalance Event Subscription API Key"; then
            break
        fi
    done
    
    while true; do
        prompt_with_default "Allocations API Key" "" "ALLOCATIONS_API_KEY" "true"
        if validate_required "$ALLOCATIONS_API_KEY" "Allocations API Key"; then
            break
        fi
    done
    
    # Optional variables with good defaults
    print_info ""
    print_info "=== Optional Configuration (using recommended defaults) ==="
    
    TIME_IN_FORCE="GTC"
    EXTENDED_HOURS_ENABLED="false"
    VNC_PASSWORD="password"
    LOG_LEVEL="INFO"
    USER_NOTIFICATIONS_ENABLED="true"
    
    print_info "Time in Force: $TIME_IN_FORCE"
    print_info "Extended Hours Enabled: $EXTENDED_HOURS_ENABLED"
    print_info "VNC Password: $VNC_PASSWORD"
    print_info "Log Level: $LOG_LEVEL"
    print_info "User Notifications Enabled: $USER_NOTIFICATIONS_ENABLED"
    
    # User notification configuration
    if [ "$USER_NOTIFICATIONS_ENABLED" = "true" ]; then
        echo ""
        print_info "=== User Notifications Configuration ==="
        print_info "The channel prefix helps identify your notifications."
        print_info "Example: Use your first initial + last name + 4-digit birth year (e.g., 'jsmith1990')"
        
        prompt_with_default "User Notifications Channel Prefix" "ZLF-2025" "USER_NOTIFICATIONS_CHANNEL_PREFIX"
        prompt_with_default "User Notifications Server URL" "https://ntfy.sh" "USER_NOTIFICATIONS_SERVER_URL"
        prompt_with_default "User Notifications Auth Token (optional)" "" "USER_NOTIFICATIONS_AUTH_TOKEN" "true"
        prompt_with_default "User Notifications Buffer Seconds" "60" "USER_NOTIFICATIONS_BUFFER_SECONDS"
    else
        USER_NOTIFICATIONS_CHANNEL_PREFIX="ZLF-2025"
        USER_NOTIFICATIONS_SERVER_URL="https://ntfy.sh"
        USER_NOTIFICATIONS_AUTH_TOKEN=""
        USER_NOTIFICATIONS_BUFFER_SECONDS="60"
    fi
    
    # Gateway restart time
    prompt_with_default "Auto Restart Time (24h format, e.g., '10:00 PM')" "10:00 PM" "AUTO_RESTART_TIME"
    
    # Create .env file
    print_step "Creating .env file..."
    
    cat > .env << EOF
# Interactive Brokers Configuration
IB_USERNAME=$IB_USERNAME
IB_PASSWORD=$IB_PASSWORD
TRADING_MODE=$TRADING_MODE

# API Keys
REBALANCE_EVENT_SUBSCRIPTION_API_KEY=$REBALANCE_EVENT_SUBSCRIPTION_API_KEY
ALLOCATIONS_API_KEY=$ALLOCATIONS_API_KEY

# Trading Configuration
TIME_IN_FORCE=$TIME_IN_FORCE
EXTENDED_HOURS_ENABLED=$EXTENDED_HOURS_ENABLED

# System Configuration
VNC_PASSWORD=$VNC_PASSWORD
LOG_LEVEL=$LOG_LEVEL
AUTO_RESTART_TIME=$AUTO_RESTART_TIME

# User Notifications
USER_NOTIFICATIONS_ENABLED=$USER_NOTIFICATIONS_ENABLED
USER_NOTIFICATIONS_CHANNEL_PREFIX=$USER_NOTIFICATIONS_CHANNEL_PREFIX
USER_NOTIFICATIONS_SERVER_URL=$USER_NOTIFICATIONS_SERVER_URL
USER_NOTIFICATIONS_AUTH_TOKEN=$USER_NOTIFICATIONS_AUTH_TOKEN
USER_NOTIFICATIONS_BUFFER_SECONDS=$USER_NOTIFICATIONS_BUFFER_SECONDS
EOF
    
    print_success ".env file created successfully!"
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

# Start services
start_services() {
    print_step "Starting services..."
    
    print_info "Building and starting Docker containers..."
    docker-compose up --build -d
    
    print_info "Waiting for services to start..."
    sleep 10
    
    print_success "Services started successfully!"
}

# Display final information
display_final_info() {
    echo ""
    print_success "Setup completed successfully!"
    echo ""
    print_info "=== Service URLs ==="
    print_info "Management Dashboard: http://localhost:8000"
    print_info "Account Setup Page: http://localhost:8000/setup/accounts"
    print_info "Health Check: http://localhost:8000/health"
    print_info "VNC Access (IBKR Gateway): http://localhost:6080 (password: $VNC_PASSWORD)"
    echo ""
    print_info "=== Useful Commands ==="
    print_info "View logs: docker-compose logs -f"
    print_info "Stop services: docker-compose down"
    print_info "Restart services: docker-compose restart"
    print_info "Manual rebalance: ./tools/rebalance.sh -all"
    echo ""
    print_info "=== Next Steps ==="
    print_info "1. Visit http://localhost:8000/setup/accounts to configure your IBKR accounts"
    print_info "2. Check the logs to ensure everything is running correctly"
    print_info "3. Access VNC at http://localhost:6080 to complete IBKR Gateway login"
    echo ""
    print_warning "IMPORTANT: Make sure to configure your accounts at the setup page before running any rebalancing operations!"
}

# Main execution
main() {
    print_header
    
    check_root
    update_system
    create_directories
    clone_repository
    configure_environment
    setup_permissions
    start_services
    display_final_info
}

# Run main function
main "$@"