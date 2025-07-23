#!/bin/bash 

# Script to enqueue commands for accounts
# Usage: 
#   ./enqueue.sh -command rebalance -all              # Process all accounts
#   ./enqueue.sh -command rebalance -account U123456  # Process specific account

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACCOUNTS_FILE="$SCRIPT_DIR/../accounts.yaml"
API_URL="http://localhost:8000/queue/events"

show_usage() {
    echo "Usage: $0 -command COMMAND [OPTIONS]"
    echo "Commands:"
    echo "  Any valid command (e.g., rebalance, print-rebalance, print-positions, etc.)"
    echo "Options:"
    echo "  -all                Process all accounts from accounts.yaml"
    echo "  -account ACCOUNT_ID Process specific account"
    echo "  -h, --help         Show this help message"
}

send_curl_request() {
    local account_id="$1"
    local strategy_name="$2"
    local cash_reserve_percent="$3"
    local command="$4"
    
    echo "Sending $command request for account: $account_id (strategy: $strategy_name, cash_reserve: $cash_reserve_percent%)"
    
    curl -X POST "$API_URL" \
         -H "Content-Type: application/json" \
         -d '{
               "account_id": "'"$account_id"'",
               "exec_command": "'"$command"'",
               "strategy_name": "'"$strategy_name"'",
               "cash_reserve_percent": '"$cash_reserve_percent"'
             }'
    echo
}

parse_accounts_yaml() {
    local target_account="$1"
    
    if [[ ! -f "$ACCOUNTS_FILE" ]]; then
        echo "Error: accounts.yaml not found at $ACCOUNTS_FILE"
        exit 1
    fi
    
    # Parse YAML using awk to extract account_id, channel, and cash_reserve_percent
    awk '
    BEGIN { account_id = ""; channel = ""; cash_reserve_percent = "" }
    
    /^[[:space:]]*-[[:space:]]*account_id:/ {
        # Output previous account if complete
        if (account_id != "" && channel != "" && cash_reserve_percent != "") {
            if (target == "" || account_id == target) {
                print account_id "|" channel "|" cash_reserve_percent
            }
        }
        # Start new account
        gsub(/^[[:space:]]*-[[:space:]]*account_id:[[:space:]]*"?/, "")
        gsub(/"?[[:space:]]*$/, "")
        account_id = $0
        channel = ""
        cash_reserve_percent = ""
    }
    
    /^[[:space:]]+channel:/ {
        gsub(/^[[:space:]]+channel:[[:space:]]*"?/, "")
        gsub(/"?[[:space:]]*$/, "")
        gsub(/#.*$/, "")  # Remove comments
        gsub(/[[:space:]]+$/, "")  # Remove trailing spaces
        channel = $0
    }
    
    /^[[:space:]]+cash_reserve_percent:/ {
        gsub(/^[[:space:]]+cash_reserve_percent:[[:space:]]*/, "")
        gsub(/#.*$/, "")  # Remove comments first
        gsub(/[[:space:]]*$/, "")  # Remove trailing spaces
        cash_reserve_percent = $0
    }
    
    END {
        # Output the last account
        if (account_id != "" && channel != "" && cash_reserve_percent != "") {
            if (target == "" || account_id == target) {
                print account_id "|" channel "|" cash_reserve_percent
            }
        }
    }
    ' target="$target_account" "$ACCOUNTS_FILE"
}

main() {
    if [[ $# -lt 2 ]]; then
        show_usage
        exit 1
    fi
    
    # Parse command argument
    if [[ "$1" != "-command" ]]; then
        echo "Error: -command argument is required"
        show_usage
        exit 1
    fi
    
    command="$2"
    shift 2  # Remove -command and its value from arguments
    
    # Parse remaining arguments
    case "$1" in
        -all)
            echo "Processing all accounts from $ACCOUNTS_FILE with command: $command"
            while IFS='|' read -r account_id strategy_name cash_reserve_percent; do
                if [[ -n "$account_id" && -n "$strategy_name" && -n "$cash_reserve_percent" ]]; then
                    send_curl_request "$account_id" "$strategy_name" "$cash_reserve_percent" "$command"
                fi
            done < <(parse_accounts_yaml "")
            ;;
        -account)
            if [[ -z "$2" ]]; then
                echo "Error: Account ID required with -account option"
                show_usage
                exit 1
            fi
            account_id="$2"
            echo "Processing account: $account_id with command: $command"
            
            account_found=false
            while IFS='|' read -r acc_id strategy_name cash_reserve_percent; do
                if [[ "$acc_id" == "$account_id" ]]; then
                    send_curl_request "$acc_id" "$strategy_name" "$cash_reserve_percent" "$command"
                    account_found=true
                    break
                fi
            done < <(parse_accounts_yaml "$account_id")
            
            if [[ "$account_found" == false ]]; then
                echo "Error: Account $account_id not found in $ACCOUNTS_FILE"
                exit 1
            fi
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Error: Unknown option $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"