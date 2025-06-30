import asyncio
import argparse
import sys
from app.config import config
from app.services.ibkr_client import IBKRClient
from app.services.rebalancer_service import RebalancerService
from app.logger import setup_logger

logger = setup_logger(__name__)

async def dry_run_command(account_id: str = None):
    """Run a dry run rebalance for testing"""
    
    if not config.accounts:
        logger.error("No accounts configured")
        return
    
    # Find the account
    target_account = None
    if account_id:
        target_account = next((acc for acc in config.accounts if acc.account_id == account_id), None)
        if not target_account:
            logger.error(f"Account {account_id} not found")
            return
    else:
        target_account = config.accounts[0]
        logger.info(f"Using first configured account: {target_account.account_id}")
    
    ibkr_client = IBKRClient()
    rebalancer_service = RebalancerService(ibkr_client)
    
    try:
        await ibkr_client.connect()
        orders = await rebalancer_service.dry_run_rebalance(target_account)
        
        print(f"\n=== DRY RUN RESULTS FOR ACCOUNT {target_account.account_id} ===")
        if orders:
            print(f"Would execute {len(orders)} orders:")
            for i, order in enumerate(orders, 1):
                print(f"{i}. {order}")
        else:
            print("No rebalancing needed - portfolio is already balanced")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"Dry run failed: {e}")
    finally:
        await ibkr_client.disconnect()

async def list_accounts_command():
    """List all configured accounts"""
    if not config.accounts:
        print("No accounts configured")
        return
    
    print("\n=== CONFIGURED ACCOUNTS ===")
    for i, account in enumerate(config.accounts, 1):
        print(f"{i}. Account ID: {account.account_id}")
        print(f"   Notification Channel: {account.notification.channel}")
        print(f"   Allocations URL: {account.allocations.url}")
        print()

async def main():
    parser = argparse.ArgumentParser(description='Portfolio Rebalancer CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Dry run command
    dry_run_parser = subparsers.add_parser('dry-run', help='Run a dry run rebalance')
    dry_run_parser.add_argument('--account-id', help='Account ID (optional, uses first account if not specified)')
    
    # List accounts command
    subparsers.add_parser('list-accounts', help='List all configured accounts')
    
    args = parser.parse_args()
    
    if args.command == 'dry-run':
        await dry_run_command(args.account_id)
    elif args.command == 'list-accounts':
        await list_accounts_command()
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())