import asyncio
import math
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from ib_async import IB, Stock, MarketOrder, Contract
from app.config import config
from app.logger import AppLogger

app_logger = AppLogger(__name__)
class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self.ib.RequestTimeout = 10.0  # Match rebalancer-api timeout
        
        # Use fixed client ID from environment (like the working old code)
        self.client_id = random.randint(1000, 2999)
        
        # Add synchronization locks
        self._connection_lock = asyncio.Lock()
        self._order_lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        if self.ib.isConnected():  # This method is synchronous and safe to use
            return True
        
        try:
            # Direct connection like the old working code
            app_logger.log_debug(f"Attempting to connect to IB Gateway at {config.ibkr.host}:{config.ibkr.port} with client ID {self.client_id}")
            await self.ib.connectAsync(
                host=config.ibkr.host,
                port=config.ibkr.port,
                clientId=self.client_id,
                timeout=10  # Use same timeout as old working code
            )
            app_logger.log_debug(f"Successfully connected to IB Gateway at {config.ibkr.host}:{config.ibkr.port}")
            return True
        except TimeoutError as e:
            app_logger.log_error(f"Connection timeout to IB Gateway at {config.ibkr.host}:{config.ibkr.port}: {e}")
            return False
        except ConnectionRefusedError as e:
            app_logger.log_error(f"Connection refused to IB Gateway at {config.ibkr.host}:{config.ibkr.port}: {e}")
            return False
        except Exception as e:
            app_logger.log_error(f"Failed to connect to IB Gateway at {config.ibkr.host}:{config.ibkr.port}: {type(e).__name__}: {e}")
            return False    
    
    
    async def get_account_value(self, account_id: str, tag: str = "NetLiquidation", event=None) -> float:
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
            # Use accountSummaryAsync like simple algorithm, but filter by account
            account_summary = await self.ib.accountSummaryAsync()
            for av in account_summary:
                if av.tag == tag and av.currency == "USD" and av.account == account_id:
                    return float(av.value)
            
            # If not found in summary, raise error like simple algorithm
            if tag == "NetLiquidation":
                raise Exception(f"Could not retrieve {tag} value for account {account_id} from IB.")
            return 0.0
        except Exception as e:
            app_logger.log_error(f"Failed to get account value: {e}", event)
            raise
    
    async def get_cash_balance(self, account_id: str) -> float:
        """Get available cash balance for the account"""
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
            account_values = self.ib.accountValues(account_id)
            # Try TotalCashValue first, fall back to AvailableFunds
            for av in account_values:
                if av.tag == "TotalCashValue" and av.currency == "USD":
                    return float(av.value)
            
            # Fallback to AvailableFunds if TotalCashValue not found
            for av in account_values:
                if av.tag == "AvailableFunds" and av.currency == "USD":
                    return float(av.value)
            
            return 0.0
        except Exception as e:
            app_logger.log_error(f"Failed to get cash balance: {e}")
            raise
    
    async def get_positions(self, account_id: str, event=None) -> List[Dict]:
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
            app_logger.log_debug(f"Requesting positions for account {account_id}", event)
            positions = await self.ib.reqPositionsAsync()
            
            result = []
            for position in positions:
                if position.account == account_id and position.position != 0:
                    # Calculate market value if not available
                    market_value = getattr(position, 'marketValue', position.position * position.avgCost)
                    
                    result.append({
                        'symbol': position.contract.symbol,
                        'position': position.position,
                        'market_value': market_value,
                        'avg_cost': position.avgCost
                    })
            
            app_logger.log_debug(f"Found {len(result)} positions for account {account_id}", event)
            return result
            
        except Exception as e:
            app_logger.log_error(f"Failed to get positions: {e}", event)
            raise
    
    
    async def _fetch_single_snapshot_price(self, contract: 'Contract') -> Optional[Tuple[str, float]]:
        """
        Phase 1 helper: Fetches a price for one contract using a snapshot.
        Improved error handling to avoid Error 300 issues.
        """
        ticker = None
        try:
            # Ensure contract is properly qualified to avoid Error 300
            if not hasattr(contract, 'conId') or not contract.conId:
                app_logger.log_warning(f"Contract {contract.symbol} not properly qualified, skipping snapshot")
                return None
                
            # Request market data snapshot
            ticker = self.ib.reqMktData(
                contract, genericTickList="", snapshot=True, regulatorySnapshot=False
            )
            
            if not ticker:
                app_logger.log_warning(f"Failed to create ticker for {contract.symbol}")
                return None
            
            price = float('nan')
            
            # Wait for ticker data with more generous timeout during market hours
            max_wait_time = 30  # 3 seconds total (30 * 0.1s)
            for i in range(max_wait_time):
                await asyncio.sleep(0.1)
                
                # Check for valid market data in priority order
                market_p = ticker.marketPrice()
                last_p = ticker.last
                close_p = ticker.close
                bid_p = ticker.bid
                ask_p = ticker.ask
                
                # Prefer live market price, then last trade, then mid-point of bid/ask, then close
                if not math.isnan(market_p) and market_p > 0:
                    price = market_p
                    break
                elif last_p and not math.isnan(last_p) and last_p > 0:
                    price = last_p
                    break
                elif (bid_p and ask_p and not math.isnan(bid_p) and not math.isnan(ask_p) 
                      and bid_p > 0 and ask_p > 0):
                    price = (bid_p + ask_p) / 2
                    break
                elif close_p and not math.isnan(close_p) and close_p > 0:
                    price = close_p
                    break
            
            if math.isnan(price) or price <= 0:
                return None
                
            return (contract.symbol, price)
            
        except Exception as e:
            app_logger.log_debug(f"Snapshot request failed for {contract.symbol}: {e}")
            return None
        finally:
            # Properly cancel market data subscription to avoid Error 300
            if ticker:
                try:
                    # Only attempt to cancel if ticker has a valid reqId
                    if hasattr(ticker, 'reqId') and ticker.reqId is not None:
                        self.ib.cancelMktData(ticker)
                    else:
                        app_logger.log_debug(f"Ticker for {contract.symbol} has no reqId, skipping cancelMktData")
                except Exception as e:
                    # Log but don't re-raise cancellation errors
                    app_logger.log_debug(f"Error cancelling market data for {contract.symbol}: {e}")

    async def _fetch_single_historical_price(self, contract: 'Contract') -> Optional[Tuple[str, float]]:
        """
        Phase 2 helper: Fetches the last closing price for one contract from historical data.
        """
        try:
            # Request the last 1 day of data to get the most recent close
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr="2 D",  # Request 2 days to ensure we get at least one bar
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1
            )
            if bars:
                # Return the close of the most recent bar
                return (contract.symbol, bars[-1].close)
            return None
        except Exception as e:
            app_logger.log_warning(f"Historical data fetch failed for {contract.symbol}: {e}")
            return None

    async def get_multiple_market_prices(self, symbols: List[str], event=None) -> Dict[str, float]:
        """
        Gets market prices using a robust, two-phase concurrent strategy.
        Phase 1: Concurrent snapshot requests for all symbols during market hours.
        Phase 2: Historical data fallback for any symbols that failed Phase 1.
        """
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        if not symbols:
            return {}
        
        # Qualify all contracts first to ensure proper contract specifications
        contracts = [Stock(s, 'SMART', 'USD') for s in symbols]
        try:
            qualified_contracts = await self.ib.qualifyContractsAsync(*contracts)
            # Filter out any contracts that failed qualification
            qualified_contracts = [c for c in qualified_contracts if hasattr(c, 'conId') and c.conId]
            
            if len(qualified_contracts) != len(symbols):
                failed_symbols = [s for s in symbols if s not in [c.symbol for c in qualified_contracts]]
                app_logger.log_warning(f"Failed to qualify contracts for: {failed_symbols}", event)
                
        except Exception as e:
            app_logger.log_error(f"Failed to qualify contracts for symbols {symbols}: {e}", event)
            raise RuntimeError(f"Could not qualify contracts for: {symbols}. Cannot proceed.")

        prices: Dict[str, float] = {}
        contracts_map = {c.symbol: c for c in qualified_contracts}

        # --- Phase 1: Concurrent Snapshot Requests ---
        # Use gather with return_exceptions=True to handle individual failures gracefully
        snapshot_tasks = [self._fetch_single_snapshot_price(c) for c in qualified_contracts]
        snapshot_results = await asyncio.gather(*snapshot_tasks, return_exceptions=True)
        
        successful_snapshots = 0
        for i, result in enumerate(snapshot_results):
            if isinstance(result, Exception):
                app_logger.log_debug(f"Snapshot exception for {qualified_contracts[i].symbol}: {result}")
                continue
            if result:
                symbol, price = result
                prices[symbol] = price
                successful_snapshots += 1

        # --- Phase 2: Concurrent Historical Fallback ---
        successful_historical = 0
        remaining_symbols = [s for s in symbols if s not in prices]
        if remaining_symbols:
            remaining_contracts = [contracts_map[s] for s in remaining_symbols if s in contracts_map]
            
            if remaining_contracts:
                historical_tasks = [self._fetch_single_historical_price(c) for c in remaining_contracts]
                historical_results = await asyncio.gather(*historical_tasks, return_exceptions=True)

                for i, result in enumerate(historical_results):
                    if isinstance(result, Exception):
                        app_logger.log_debug(f"Historical exception for {remaining_contracts[i].symbol}: {result}")
                        continue
                    if result:
                        symbol, price = result
                        prices[symbol] = price
                        successful_historical += 1

        # --- Final Check ---
        final_missing = [s for s in symbols if s not in prices]
        if final_missing:
            app_logger.log_error(f"Could not fetch prices for: {final_missing} after all fallbacks", event)
            raise RuntimeError(f"Could not fetch price for: {final_missing} after all fallbacks.")
        
        # Single consolidated completion log
        phase2_msg = f", Phase 2 (Historical): {successful_historical}/{len(remaining_symbols) if remaining_symbols else 0}" if remaining_symbols else ""
        app_logger.log_info(f"Market prices retrieved for {len(symbols)} symbols - Phase 1 (Snapshot): {successful_snapshots}/{len(qualified_contracts)}{phase2_msg}")
        return prices
    
    
    async def place_order(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT", event=None, 
                        time_in_force: str = "DAY", extended_hours: bool = False):
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        contract = Stock(symbol, 'SMART', 'USD')
        
        # Use the async version for consistency
        try:
            qualified_contracts = await self.ib.qualifyContractsAsync(contract)
            if not qualified_contracts:
                raise Exception(f"Could not qualify contract for {symbol}")
            contract = qualified_contracts[0]
        except Exception as e:
            app_logger.log_error(f"Failed to qualify contract for {symbol}: {e}", event)
            raise RuntimeError(f"Could not qualify contract for: {symbol}. Cannot proceed.")

        action = "BUY" if quantity > 0 else "SELL"        
        
        order = MarketOrder(action, abs(quantity))
        if extended_hours:
            order.outsideRth = True
        order.account = account_id
        
        trade = self.ib.placeOrder(contract, order)
        app_logger.log_info(f"Order placed: ID={trade.order.orderId}; {action} {abs(quantity)} shares of {symbol}", event)
        
        return trade
    
    async def cancel_all_orders(self, account_id: str, event=None) -> List[Dict]:
        """Cancel all pending orders for the given account.
        
        This method cancels all pending orders and waits up to 60 seconds for 
        confirmation from the brokerage. If any orders remain pending after 
        the timeout, an exception is raised to prevent conflicting orders 
        during rebalancing.
        
        Returns:
            List[Dict]: Details of orders that were cancelled
            
        Raises:
            Exception: If orders cannot be cancelled within 60 seconds
        """
        async with self._order_lock:
            if not await self.ensure_connected():
                raise Exception("Unable to establish IBKR connection")
            
            try:
                open_orders = self.ib.openOrders()
                cancelled_orders = []
                
                for order in open_orders:
                    if order.account == account_id:
                            
                        # Get contract symbol
                        symbol = 'Unknown'
                        if hasattr(order, 'contract') and order.contract:
                            symbol = getattr(order.contract, 'symbol', 'Unknown')
                        
                        order_details = {
                            'order_id': str(order.orderId),
                            'symbol': symbol,
                            'quantity': abs(order.totalQuantity),
                            'action': order.action,
                            'order_type': order.orderType,
                            'status': 'OpenOrder'
                        }
                        cancelled_orders.append(order_details)
                        
                        self.ib.cancelOrder(order)
                        app_logger.log_debug(f"Cancelled order {order.orderId} for {account_id}: {order.action} {abs(order.totalQuantity)} {symbol}", event)
                
                if cancelled_orders:
                    # Wait for all cancellations to be confirmed
                    await self._wait_for_orders_cancelled(account_id, max_wait_seconds=60)
                
                app_logger.log_info(f"Cancelled {len(cancelled_orders)} pending orders for account {account_id}", event)
                return cancelled_orders
                
            except Exception as e:
                app_logger.log_error(f"Failed to cancel orders for account {account_id}: {e}", event)
                raise
    
    async def _wait_for_orders_cancelled(self, account_id: str, max_wait_seconds: int = 60):
        """Wait for all pending orders to be cancelled for the account"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            trades = self.ib.trades()
            pending_orders = [
                trade for trade in trades 
                if (trade.order.account == account_id and 
                    trade.orderStatus.status in ['PreSubmitted', 'Submitted', 'PendingSubmit'])
            ]
            
            if not pending_orders:
                app_logger.log_debug(f"All orders successfully cancelled for account {account_id}")
                return
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= max_wait_seconds:
                pending_ids = [trade.order.orderId for trade in pending_orders]
                error_msg = f"Timeout waiting for order cancellations for account {account_id}. Still pending: {pending_ids}"
                app_logger.log_error(error_msg)
                raise Exception(error_msg)
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    
    async def ensure_connected(self) -> bool:
        async with self._connection_lock:
            if not self.ib.isConnected():
                return await self.connect()
            
            # Active validation with timeout to detect stale connections
            try:
                await asyncio.wait_for(
                    self.ib.reqCurrentTimeAsync(), 
                    timeout=5.0
                )
                return True
            except (asyncio.TimeoutError, Exception) as e:
                app_logger.log_warning(f"Stale connection detected ({type(e).__name__}: {e}), reconnecting...")
                return await self.connect()
    
    async def get_contract_details(self, symbols: List[str], event=None) -> Dict[str, Any]:
        """
        Get contract details for multiple symbols including trading hours information
        
        Returns:
            Dict mapping symbol to contract details containing tradingHours, liquidHours, timeZone
        """
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        if not symbols:
            return {}
        
        try:
            contracts = [Stock(symbol, 'SMART', 'USD') for symbol in symbols]
            contract_details = {}
            
            for contract in contracts:
                try:
                    # Get contract details
                    details_list = await self.ib.reqContractDetailsAsync(contract)
                    
                    if details_list:
                        # Take the first matching contract details
                        details = details_list[0]
                        
                        contract_details[contract.symbol] = {
                            'tradingHours': details.tradingHours,
                            'liquidHours': details.liquidHours,
                            'timeZone': details.timeZoneId,
                            'contractDetails': details
                        }
                        
                        app_logger.log_debug(f"Got contract details for {contract.symbol}: timeZone={details.timeZoneId}", event)
                    else:
                        app_logger.log_warning(f"No contract details found for {contract.symbol}", event)
                        
                except Exception as e:
                    app_logger.log_error(f"Failed to get contract details for {contract.symbol}: {e}", event)
                    # Continue with other symbols
                    
            return contract_details
            
        except Exception as e:
            app_logger.log_error(f"Failed to get contract details: {e}", event)
            raise
    
    def _parse_trading_hours(self, trading_hours_str: str) -> List[Dict[str, Any]]:
        """
        Parse IBKR trading hours string format
        
        Format: 'YYYYMMDD:HHMM-YYYYMMDD:HHMM;YYYYMMDD:CLOSED;...'
        
        Returns:
            List of trading sessions with start_time, end_time, is_closed
        """
        if not trading_hours_str:
            return []
        
        sessions = []
        for session_str in trading_hours_str.split(';'):
            session_str = session_str.strip()
            if not session_str:
                continue
                
            if ':CLOSED' in session_str:
                # Closed session
                date_str = session_str.split(':')[0]
                sessions.append({
                    'date': date_str,
                    'is_closed': True,
                    'start_time': None,
                    'end_time': None
                })
            elif '-' in session_str:
                # Active trading session
                try:
                    start_part, end_part = session_str.split('-')
                    start_date, start_time = start_part.split(':')
                    end_date, end_time = end_part.split(':')
                    
                    sessions.append({
                        'date': start_date,
                        'is_closed': False,
                        'start_time': f"{start_date}:{start_time}",
                        'end_time': f"{end_date}:{end_time}"
                    })
                except ValueError as e:
                    app_logger.log_warning(f"Failed to parse trading session: {session_str}")
                    continue
        
        return sessions
    
    def _is_within_trading_hours(self, sessions: List[Dict[str, Any]], current_time: datetime) -> Tuple[bool, Optional[datetime]]:
        """
        Check if current time is within any trading session
        
        Args:
            sessions: List of trading sessions from _parse_trading_hours
            current_time: Current datetime (should be in America/New_York timezone)
            
        Returns:
            Tuple of (is_within_hours, next_session_start_time)
        """
        current_date_str = current_time.strftime('%Y%m%d')
        current_time_str = current_time.strftime('%H%M')
        
        # Check if we're currently in a trading session
        for session in sessions:
            if session.get('is_closed', True):
                continue
                
            start_time_str = session.get('start_time', '')
            end_time_str = session.get('end_time', '')
            
            if not start_time_str or not end_time_str:
                continue
                
            try:
                # Parse start and end times
                start_date, start_time = start_time_str.split(':')
                end_date, end_time = end_time_str.split(':')
                
                # Convert to datetime objects
                start_dt = datetime.strptime(f"{start_date}:{start_time}", "%Y%m%d:%H%M")
                end_dt = datetime.strptime(f"{end_date}:{end_time}", "%Y%m%d:%H%M")
                
                # Check if current time is within this session
                if start_dt <= current_time <= end_dt:
                    return True, None
                    
            except ValueError:
                continue
        
        # Find next trading session start time
        next_start = None
        for session in sessions:
            if session.get('is_closed', True):
                continue
                
            start_time_str = session.get('start_time', '')
            if not start_time_str:
                continue
                
            try:
                start_date, start_time = start_time_str.split(':')
                start_dt = datetime.strptime(f"{start_date}:{start_time}", "%Y%m%d:%H%M")
                
                if start_dt > current_time:
                    if next_start is None or start_dt < next_start:
                        next_start = start_dt
                        
            except ValueError:
                continue
        
        return False, next_start
    
    async def check_trading_hours(self, symbols: List[str], event=None) -> Tuple[bool, Optional[datetime], Dict[str, bool]]:
        """
        Check if all symbols are currently within their trading hours
        
        Args:
            symbols: List of symbols to check
            event: Event context for logging
            
        Returns:
            Tuple of (all_within_hours, earliest_next_start, symbol_status_dict)
        """
        if not symbols:
            return True, None, {}
        
        try:
            # Get contract details for all symbols
            contract_details = await self.get_contract_details(symbols, event)
            
            current_time = datetime.now()  # System is in America/New_York timezone
            all_within_hours = True
            earliest_next_start = None
            symbol_status = {}
            
            for symbol in symbols:
                details = contract_details.get(symbol)
                if not details:
                    app_logger.log_error(f"No contract details available for {symbol}", event)
                    symbol_status[symbol] = False
                    all_within_hours = False
                    continue
                
                # Determine which hours to use based on EXTENDED_HOURS_ENABLED
                hours_str = details['liquidHours'] if not config.order.extended_hours_enabled else details['tradingHours']
                
                if not hours_str:
                    app_logger.log_warning(f"No trading hours available for {symbol}", event)
                    symbol_status[symbol] = False
                    all_within_hours = False
                    continue
                
                # Parse trading hours
                sessions = self._parse_trading_hours(hours_str)
                is_within, next_start = self._is_within_trading_hours(sessions, current_time)
                
                symbol_status[symbol] = is_within
                
                if not is_within:
                    all_within_hours = False
                    app_logger.log_info(f"Symbol {symbol} is outside trading hours", event)
                    
                    if next_start and (earliest_next_start is None or next_start < earliest_next_start):
                        earliest_next_start = next_start
                else:
                    app_logger.log_debug(f"Symbol {symbol} is within trading hours", event)
            
            hours_type = "liquid hours" if not config.order.extended_hours_enabled else "trading hours"
            if all_within_hours:
                app_logger.log_info(f"All symbols are within {hours_type}", event)
            else:
                next_str = earliest_next_start.strftime("%Y-%m-%d %H:%M:%S") if earliest_next_start else "unknown"
                app_logger.log_info(f"Some symbols outside {hours_type}, earliest next start: {next_str}", event)
            
            return all_within_hours, earliest_next_start, symbol_status
            
        except Exception as e:
            app_logger.log_error(f"Failed to check trading hours: {e}", event)
            raise
    
    
