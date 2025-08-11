#!/bin/bash

# IBKR Portfolio Rebalancer Setup Script
# Usage: 
#   Cloud:  curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup.sh | sudo bash -s -- --cloud
#   Local:  curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup.sh | bash -s -- --local

set -e

# Parse command line arguments - REQUIRED
ENVIRONMENT=""
INSTALL_TAILSCALE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --cloud)
            ENVIRONMENT="cloud"
            shift
            ;;
        --local)
            ENVIRONMENT="local"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: curl -fsSL ... | [sudo] bash -s -- [--cloud|--local]"
            exit 1
            ;;
    esac
done

# Require environment to be specified
if [ -z "$ENVIRONMENT" ]; then
    echo "Error: Environment must be specified"
    echo "Usage:"
    echo "  Cloud:  curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup.sh | sudo bash -s -- --cloud"
    echo "  Local:  curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup.sh | bash -s -- --local"
    exit 1
fi

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


# Check if running as root (cloud only)
check_root() {
    if [ "$ENVIRONMENT" = "cloud" ] && [ "$EUID" -ne 0 ]; then
        print_error "Cloud setup must be run as root (use sudo)"
        exit 1
    fi
    
    if [ "$ENVIRONMENT" = "local" ] && [ "$EUID" -eq 0 ]; then
        print_error "Local setup should not be run as root (remove sudo)"
        exit 1
    fi
}

# Check if Docker is installed
check_docker() {
    print_step "Checking Docker installation..."
    
    # Remove Docker image banner if it exists
    rm -rf /etc/update-motd.d/99-one-click
    
    if ! command -v docker &> /dev/null; then
        if [ "$ENVIRONMENT" = "cloud" ]; then
            print_error "Docker is not installed. Please install Docker first."
            print_info "Visit: https://docs.docker.com/get-docker/"
        else
            print_error "Docker is not installed. Please install Docker Desktop first."
            print_info "Visit: https://www.docker.com/products/docker-desktop/"
        fi
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        if [ "$ENVIRONMENT" = "cloud" ]; then
            print_warning "Docker daemon is not running. Attempting to start..."
            systemctl start docker
            sleep 5
            if ! docker info &> /dev/null; then
                print_error "Failed to start Docker daemon. Please check Docker installation."
                exit 1
            fi
        else
            print_error "Docker is not running. Please start Docker Desktop and try again."
            exit 1
        fi
    fi
    
    print_success "Docker is installed and running!"
}

# Check git installation
check_git() {
    print_step "Checking git installation..."
    
    if ! command -v git &> /dev/null; then
        if [ "$ENVIRONMENT" = "cloud" ]; then
            print_info "Installing git..."
            apt-get install -y git
        else
            print_error "Git is not installed. Please install git first:"
            print_info "  Windows: https://git-scm.com/download/windows"
            print_info "  macOS:   brew install git"
            print_info "  Linux:   sudo apt install git (Ubuntu/Debian)"
            exit 1
        fi
    fi
    
    print_success "Git is available!"
}

# Setup Tailscale for secure remote access
setup_tailscale() {
    # Only setup Tailscale for cloud installations
    if [ "$ENVIRONMENT" = "cloud" ]; then
        print_step "Tailscale Setup"
        
        # Check if Tailscale is already installed and running
        if command -v tailscale &> /dev/null && tailscale status &> /dev/null 2>&1; then
            print_success "Tailscale is already installed and authenticated"
            INSTALL_TAILSCALE=false
            return
        fi
        
        # Check if Tailscale is installed but not authenticated
        if command -v tailscale &> /dev/null; then
            print_info "Tailscale is installed but not authenticated"
            INSTALL_TAILSCALE=true
            return
        fi
        
        echo ""
        echo "Tailscale provides secure remote access to your services from anywhere."
        echo "Would you like to set up Tailscale? (y/n)"
        read -r setup_choice < /dev/tty
        
        if [[ "$setup_choice" =~ ^[Yy]$ ]]; then
            print_info "Setting up Tailscale repository..."
            
            # Add Tailscale repository (no sudo needed, already running as root in cloud)
            curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
            curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list
            
            INSTALL_TAILSCALE=true
            print_success "Tailscale repository added successfully!"
        else
            INSTALL_TAILSCALE=false
            print_info "Skipping Tailscale setup"
        fi
    fi
}

# System updates (cloud only)
update_system() {
    if [ "$ENVIRONMENT" = "cloud" ]; then
        print_step "Updating system packages..."
        
        # Set debconf to non-interactive mode to avoid prompts
        export DEBIAN_FRONTEND=noninteractive
        
        # Update package lists
        apt-get update -qq
        
        # Upgrade packages silently with automatic yes to all prompts
        apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qq
        
        print_success "System updated successfully!"
    fi
}

# Configure Tailscale serve for Management Service
configure_tailscale_serve() {
    if command -v tailscale &> /dev/null && tailscale status &> /dev/null 2>&1; then
        # Check if serve is already configured
        if tailscale serve status 2>/dev/null | grep -q "/ms/.*http://127.0.0.1:8000"; then
            print_success "Tailscale serve is already configured for Management Service at /ms/"
        else
            # Set up Tailscale serve for Management Service - MUST succeed
            print_info "Setting up Tailscale serve for Management Service..."
            if ! tailscale serve --bg /ms/ http://127.0.0.1:8000; then
                print_error "Failed to configure Tailscale serve for Management Service"
                print_error "This is a required step for remote access to the Management API"
                exit 1
            fi
            print_success "Tailscale serve configured successfully for Management Service at /ms/"
        fi
    fi
}

# Complete Tailscale setup after system update
complete_tailscale_setup() {
    if [ "$INSTALL_TAILSCALE" = "true" ]; then
        # Check if already authenticated (in case of re-run)
        if tailscale status &> /dev/null 2>&1; then
            print_success "Tailscale is already authenticated"
            configure_tailscale_serve
            return
        fi
        
        # Install Tailscale package if not already installed
        if ! command -v tailscale &> /dev/null; then
            print_step "Installing Tailscale package..."
            apt-get install -y tailscale
        else
            print_info "Tailscale package already installed"
        fi
        
        print_info "Tailscale installed. Now we need to authenticate."
        
        # Authentication loop
        while true; do
            echo ""
            echo "Enter your Tailscale auth key (generate one at https://login.tailscale.com/admin/settings/keys):"
            read -r TAILSCALE_AUTH_KEY < /dev/tty  # -s for silent (no echo)
            echo ""  # New line after silent input

            print_info "Authenticating Tailscale..."
            
            if tailscale up --hostname ibkr-portfolio-rebalancer-9897 --auth-key="$TAILSCALE_AUTH_KEY" 2>/dev/null; then
                unset TAILSCALE_AUTH_KEY  # Immediately clear from memory
                print_success "Tailscale authenticated successfully!"
                configure_tailscale_serve
                break
            else
                unset TAILSCALE_AUTH_KEY  # Clear even on failure
                print_error "Tailscale authentication failed."
                echo "Would you like to [T]ry again or [S]kip? (T/S)"
                read -r choice < /dev/tty
                
                if [[ "$choice" =~ ^[Ss]$ ]]; then
                    print_info "Skipping Tailscale setup..."
                    break
                fi
            fi
        done
    fi
}

# Create directory structure
create_directories() {
    print_step "Creating directory structure..."
    
    if [ "$ENVIRONMENT" = "cloud" ]; then
        # Create base directory
        mkdir -p /home/docker/zehnlabs
        cd /home/docker/zehnlabs
        print_success "Directory /home/docker/zehnlabs created and set as working directory"
    else
        # For local, use current directory or create a sensible default
        if [ ! -d "ibkr-portfolio-rebalancer" ]; then
            print_info "Creating setup in current directory: $(pwd)"
        fi
        print_success "Using current directory for setup"
    fi
}

# Clone repository
clone_repository() {
    if [ -d "ibkr-portfolio-rebalancer" ]; then
        print_step "Repository already exists, updating..."
        cd ibkr-portfolio-rebalancer
        
        print_info "Pulling latest changes from repository..."
        if git pull origin main; then
            print_success "Repository updated successfully!"
        else
            print_warning "Git pull failed, repository may have local changes"
        fi
    else
        print_step "Cloning IBKR Portfolio Rebalancer repository..."
        
        git clone https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer.git
        cd ibkr-portfolio-rebalancer
        
        print_success "Repository cloned successfully!"
    fi
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
            print_info ".env already exists, keeping existing file"
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
            print_info "accounts.yaml already exists, keeping existing file"
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
    
    echo "🔗 Accessing Services:"
    
    # Check if Tailscale is installed and get hostname
    if command -v tailscale &> /dev/null && tailscale status &> /dev/null 2>&1; then
        # Get hostname and remove trailing period if present
        TAILSCALE_HOSTNAME=$(tailscale status --json | jq -r '.Self.DNSName // empty' | sed 's/\.$//')
        if [ -n "$TAILSCALE_HOSTNAME" ]; then
            echo "   You can access the following services from any device on your Tailscale network:"
            echo ""
            echo "📊 Manage Containers and View Logs:"
            echo "   http://$TAILSCALE_HOSTNAME:8080"
            echo ""
            echo "🔧 Management API:"
            echo "   http://$TAILSCALE_HOSTNAME:8000"
        else
            # Tailscale installed but no DNSName available
            echo ""
            echo "📊 Manage Containers and View Logs:"
            echo "   http://<Your Tailscale Host Name>:8080"
            echo ""
            echo "🔧 Management API:"
            echo "   http://<Your Tailscale Host Name>:8000"
        fi
    else
        # Tailscale not installed or not running, use localhost
        echo ""
        echo "📊 Manage Containers and View Logs:"
        echo "   http://localhost:8080"
        echo ""
        echo "🔧 Management API:"
        echo "   http://localhost:8000"
    fi
    
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
    
    # Set proper ownership for cloud only
    if [ "$ENVIRONMENT" = "cloud" ] && [ -n "$SUDO_USER" ]; then
        chown -R "$SUDO_USER:$SUDO_USER" .
        print_info "Changed ownership to $SUDO_USER"
    fi
    
    # Create and set log directory permissions for Docker containers
    mkdir -p event-broker/logs event-processor/logs management-service/logs
    chmod 777 event-broker/logs event-processor/logs management-service/logs
    print_info "Created log directories and set permissions to 777"
    
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
    check_git
    setup_tailscale
    update_system
    complete_tailscale_setup
    create_directories
    clone_repository
    rename_config_files
    setup_permissions
    show_documentation_and_wait
    start_all_services
    display_final_instructions
}

# Run main function
main "$@"