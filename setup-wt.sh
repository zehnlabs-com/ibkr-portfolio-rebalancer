#!/bin/bash

# IBKR Portfolio Rebalancer Setup Script with Whiptail Interface
# Usage: 
#   Cloud:  curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup-wt.sh | sudo bash -s -- --cloud
#   Local:  curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup-wt.sh | bash -s -- --local

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
    echo "  Cloud:  curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup-wt.sh | sudo bash -s -- --cloud"
    echo "  Local:  curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup-wt.sh | bash -s -- --local"
    exit 1
fi

# Install whiptail if not present
install_whiptail() {
    if ! command -v whiptail &> /dev/null; then
        if [ "$ENVIRONMENT" = "cloud" ]; then
            apt-get update -qq
            apt-get install -y whiptail
        else
            echo "Error: whiptail is not installed."
            echo "Please install it first:"
            echo "  Ubuntu/Debian: sudo apt install whiptail"
            echo "  CentOS/RHEL:   sudo yum install newt"
            echo "  macOS:         brew install newt"
            exit 1
        fi
    fi
}

# Helper functions for whiptail dialogs
show_msgbox() {
    whiptail --title "$1" --msgbox "$2" 20 70
}

show_yesno() {
    whiptail --title "$1" --yesno "$2" 15 60
}

show_inputbox() {
    whiptail --title "$1" --inputbox "$2" 12 60 "$3" 3>&1 1>&2 2>&3
}

show_passwordbox() {
    whiptail --title "$1" --passwordbox "$2" 12 60 3>&1 1>&2 2>&3
}

show_infobox() {
    whiptail --title "$1" --infobox "$2" 8 50
}

show_gauge() {
    whiptail --title "$1" --gauge "$2" 8 50 "$3"
}

# Detect Docker Compose command
get_docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null; then
        echo "docker compose"
    else
        show_msgbox "Error" "Neither 'docker-compose' nor 'docker compose' is available"
        exit 1
    fi
}

# Check if running as root (cloud only)
check_root() {
    if [ "$ENVIRONMENT" = "cloud" ] && [ "$EUID" -ne 0 ]; then
        show_msgbox "Error" "Cloud setup must be run as root (use sudo)"
        exit 1
    fi
    
    if [ "$ENVIRONMENT" = "local" ] && [ "$EUID" -eq 0 ]; then
        show_msgbox "Error" "Local setup should not be run as root (remove sudo)"
        exit 1
    fi
}

# Check if Docker is installed
check_docker() {
    show_infobox "Setup Progress" "Checking Docker installation..."
    
    # Remove Docker image banner if it exists
    rm -rf /etc/update-motd.d/99-one-click
    
    if ! command -v docker &> /dev/null; then
        if [ "$ENVIRONMENT" = "cloud" ]; then
            show_msgbox "Error" "Docker is not installed. Please install Docker first.\n\nVisit: https://docs.docker.com/get-docker/"
        else
            show_msgbox "Error" "Docker is not installed. Please install Docker Desktop first.\n\nVisit: https://www.docker.com/products/docker-desktop/"
        fi
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        if [ "$ENVIRONMENT" = "cloud" ]; then
            show_infobox "Setup Progress" "Starting Docker daemon..."
            systemctl start docker
            sleep 5
            if ! docker info &> /dev/null; then
                show_msgbox "Error" "Failed to start Docker daemon. Please check Docker installation."
                exit 1
            fi
        else
            show_msgbox "Error" "Docker is not running. Please start Docker Desktop and try again."
            exit 1
        fi
    fi
}

# Check git installation
check_git() {
    show_infobox "Setup Progress" "Checking git installation..."
    
    if ! command -v git &> /dev/null; then
        if [ "$ENVIRONMENT" = "cloud" ]; then
            show_infobox "Setup Progress" "Installing git..."
            apt-get install -y git
        else
            show_msgbox "Error" "Git is not installed. Please install git first:\n\nWindows: https://git-scm.com/download/windows\nmacOS: brew install git\nLinux: sudo apt install git (Ubuntu/Debian)"
            exit 1
        fi
    fi
}

# Setup Tailscale for secure remote access
setup_tailscale() {
    # Only setup Tailscale for cloud installations
    if [ "$ENVIRONMENT" = "cloud" ]; then
        # Check if Tailscale is already installed and running
        if command -v tailscale &> /dev/null && tailscale status &> /dev/null 2>&1; then
            show_msgbox "Tailscale" "Tailscale is already installed and authenticated"
            INSTALL_TAILSCALE=false
            return
        fi
        
        # Check if Tailscale is installed but not authenticated
        if command -v tailscale &> /dev/null; then
            show_msgbox "Tailscale" "Tailscale is installed but not authenticated"
            INSTALL_TAILSCALE=true
            return
        fi
        
        if show_yesno "Tailscale Setup" "Tailscale provides secure remote access to your services from anywhere.\n\nWould you like to set up Tailscale?"; then
            show_infobox "Setup Progress" "Setting up Tailscale repository..."
            
            # Add Tailscale repository (no sudo needed, already running as root in cloud)
            curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
            curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list
            
            INSTALL_TAILSCALE=true
        else
            INSTALL_TAILSCALE=false
        fi
    fi
}

# System updates (cloud only)
update_system() {
    if [ "$ENVIRONMENT" = "cloud" ]; then
        show_infobox "Setup Progress" "Updating system packages..."
        
        # Set debconf to non-interactive mode to avoid prompts
        export DEBIAN_FRONTEND=noninteractive
        
        # Update package lists
        apt-get update -qq
        
        # Upgrade packages silently with automatic yes to all prompts
        apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qq
    fi
}

# Configure Tailscale serve for Management Service
configure_tailscale_serve() {
    if command -v tailscale &> /dev/null && tailscale status &> /dev/null 2>&1; then
        # Check if serve is already configured
        if tailscale serve status 2>/dev/null | grep -q "/ms/.*http://127.0.0.1:8000"; then
            show_msgbox "Tailscale" "Tailscale serve is already configured for Management Service at /ms/"
        else
            # Set up Tailscale serve for Management Service - MUST succeed
            show_infobox "Setup Progress" "Setting up Tailscale serve for Management Service..."
            if ! tailscale serve --bg --set-path /ms 8000; then
                show_msgbox "Error" "Failed to configure Tailscale serve for Management Service\n\nThis is a required step for remote access to the Management API"
                exit 1
            fi
            show_msgbox "Success" "Tailscale serve configured successfully for Management Service at /ms/"
        fi
    fi
}

# Complete Tailscale setup after system update
complete_tailscale_setup() {
    if [ "$INSTALL_TAILSCALE" = "true" ]; then
        # Check if already authenticated (in case of re-run)
        if tailscale status &> /dev/null 2>&1; then
            show_msgbox "Tailscale" "Tailscale is already authenticated"
            configure_tailscale_serve
            return
        fi
        
        # Install Tailscale package if not already installed
        if ! command -v tailscale &> /dev/null; then
            show_infobox "Setup Progress" "Installing Tailscale package..."
            apt-get install -y tailscale
        fi
        
        # Authentication loop
        while true; do
            TAILSCALE_AUTH_KEY=$(show_inputbox "Tailscale Authentication" "Enter your Tailscale auth key\n\nGenerate one at:\nhttps://login.tailscale.com/admin/settings/keys")
            
            if [ -z "$TAILSCALE_AUTH_KEY" ]; then
                if show_yesno "Tailscale Setup" "No auth key entered. Would you like to skip Tailscale setup?"; then
                    break
                else
                    continue
                fi
            fi

            show_infobox "Setup Progress" "Authenticating Tailscale..."
            
            if tailscale up --hostname ibkr-portfolio-rebalancer-9897 --auth-key="$TAILSCALE_AUTH_KEY" 2>/dev/null; then
                unset TAILSCALE_AUTH_KEY  # Immediately clear from memory
                show_msgbox "Success" "Tailscale authenticated successfully!"
                configure_tailscale_serve
                break
            else
                unset TAILSCALE_AUTH_KEY  # Clear even on failure
                if show_yesno "Tailscale Error" "Tailscale authentication failed.\n\nWould you like to try again?"; then
                    continue
                else
                    break
                fi
            fi
        done
    fi
}

# Create directory structure
create_directories() {
    show_infobox "Setup Progress" "Creating directory structure..."
    
    if [ "$ENVIRONMENT" = "cloud" ]; then
        # Create base directory
        mkdir -p /home/docker/zehnlabs
        cd /home/docker/zehnlabs
    fi
}

# Clone repository
clone_repository() {
    if [ -d "ibkr-portfolio-rebalancer" ]; then
        show_infobox "Setup Progress" "Repository exists, updating..."
        cd ibkr-portfolio-rebalancer
        
        if git pull origin main; then
            show_msgbox "Success" "Repository updated successfully!"
        else
            show_msgbox "Warning" "Git pull failed, repository may have local changes"
        fi
    else
        show_infobox "Setup Progress" "Cloning IBKR Portfolio Rebalancer repository..."
        
        git clone https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer.git
        cd ibkr-portfolio-rebalancer
        
        show_msgbox "Success" "Repository cloned successfully!"
    fi
}

# Copy configuration files
copy_config_files() {
    show_infobox "Setup Progress" "Setting up configuration files..."
    
    # Copy .env.example to .env
    if [ -f ".env.example" ]; then
        if [ ! -f ".env" ]; then
            cp .env.example .env
        fi
    else
        show_msgbox "Error" ".env.example not found - cannot create initial environment configuration"
        exit 1
    fi
    
    # Copy accounts.example.yaml to accounts.yaml
    if [ -f "accounts.example.yaml" ]; then
        if [ ! -f "accounts.yaml" ]; then
            cp accounts.example.yaml accounts.yaml
        fi
    else
        show_msgbox "Error" "accounts.example.yaml not found - cannot create initial accounts configuration"
        exit 1
    fi
}

# Get user's email for Zehnlabs registration
get_user_email() {
    show_msgbox "Account Registration" "To complete setup, you need a valid email address registered with Zehnlabs.\n\n📧 To find your registered email address:\n   1. Open Telegram and find @FintechZL_bot\n   2. Send the command: /api\n   3. The bot will show your registered email address"
    
    while true; do
        USER_EMAIL=$(show_inputbox "Email Address" "Enter your Zehnlabs registered email address:")
        
        if [ -z "$USER_EMAIL" ]; then
            show_msgbox "Error" "Email address is required"
            continue
        fi
        
        # Basic email validation
        if [[ "$USER_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
            if show_yesno "Confirm Email" "You entered: $USER_EMAIL\n\nIs this correct?"; then
                # Create clerk-users.json file
                echo "[ \"$USER_EMAIL\" ]" > clerk-users.json
                break
            fi
        else
            show_msgbox "Error" "Invalid email format. Please enter a valid email address."
        fi
    done
}

# Register with Zehnlabs API
register_with_zehnlabs() {
    show_infobox "Setup Progress" "Registering with Zehnlabs..."
    
    # Get Tailscale FQDN
    local API_DOMAIN=""
    if command -v tailscale &> /dev/null && tailscale status &> /dev/null 2>&1; then
        API_DOMAIN=$(tailscale status --json | jq -r '.Self.DNSName // empty' | sed 's/\.$//')
        if [ -z "$API_DOMAIN" ]; then
            show_msgbox "Error" "Could not get Tailscale hostname. Ensure Tailscale is properly configured."
            exit 1
        fi        
    else
        show_msgbox "Error" "Tailscale is required for registration. Please ensure Tailscale is installed and authenticated."
        exit 1
    fi
    
    # Prepare JSON payload
    local PAYLOAD=$(cat <<EOF
{
  "email": "$USER_EMAIL",
  "api_base_url": "https://$API_DOMAIN/ms"
}
EOF
)
    
    # Make API call and capture response
    local RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "https://workers.fintech.zehnlabs.com/api/v1/auth/register")
    
    # Extract HTTP status code and body
    local HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local RESPONSE_BODY=$(echo "$RESPONSE" | sed 's/HTTPSTATUS:[0-9]*$//')
    
    # Check if request was successful
    if [ "$HTTP_STATUS" -eq 200 ]; then
        # Extract message from JSON response
        local MESSAGE=$(echo "$RESPONSE_BODY" | jq -r '.message // "Registration successful"')
        REGISTRATION_MESSAGE="$MESSAGE"
        show_msgbox "Success" "Authentication successful!"
    else
        # Extract error message if available
        local ERROR_MESSAGE=$(echo "$RESPONSE_BODY" | jq -r '.message // .error // "Registration failed"')
        show_msgbox "Error" "Authentication failed (HTTP $HTTP_STATUS): $ERROR_MESSAGE"
        exit 1
    fi
}

# Display registration success and start management service
display_registration_success() {
    show_infobox "Setup Progress" "Starting Management Service..."
    
    $DOCKER_COMPOSE_CMD up --build -d management-service
    
    # Wait a moment for service to start
    sleep 30
    
    # Verify management service is running
    if $DOCKER_COMPOSE_CMD ps management-service 2>/dev/null | grep -q "Up\|running"; then
        SERVICE_STATUS="✓ Management service is running"
    else
        SERVICE_STATUS="Management service may still be starting. Check logs with: $DOCKER_COMPOSE_CMD logs management-service"
    fi
    
    show_msgbox "Setup Complete! 🎉" "$REGISTRATION_MESSAGE\n\n$SERVICE_STATUS\n\n📧 You will receive an email shortly with instructions to access the control panel where you can complete the final configuration of your setup."
}

# Set up file permissions
setup_permissions() {
    show_infobox "Setup Progress" "Setting up file permissions..."
    
    # Make scripts executable
    chmod +x setup.sh setup-wt.sh
    if [ -f "reload.sh" ]; then
        chmod +x reload.sh
    fi
    if [ -d "tools" ]; then
        chmod +x tools/*.sh
    fi
    
    # Set proper ownership for cloud only
    if [ "$ENVIRONMENT" = "cloud" ] && [ -n "$SUDO_USER" ]; then
        chown -R "$SUDO_USER:$SUDO_USER" .
    fi
    
    # Create and set log directory permissions for Docker containers
    mkdir -p event-broker/logs event-processor/logs management-service/logs
    chmod 777 event-broker/logs event-processor/logs management-service/logs
}

# Main execution
main() {
    # Install whiptail first
    install_whiptail
    
    # Welcome screen
    show_msgbox "IBKR Portfolio Rebalancer Setup" "Welcome to the IBKR Portfolio Rebalancer setup wizard!\n\nThis interactive setup will guide you through the installation process.\n\nEnvironment: $ENVIRONMENT"
    
    # Set Docker Compose command
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    check_root
    check_docker
    check_git
    setup_tailscale
    update_system
    complete_tailscale_setup
    create_directories
    clone_repository
    copy_config_files
    setup_permissions
    get_user_email
    register_with_zehnlabs
    display_registration_success
}

# Run main function
main "$@"