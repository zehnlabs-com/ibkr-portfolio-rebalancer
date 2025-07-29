"""
Redis Queue Service for Event Processor
"""
import json
import time
import yaml
import os
import redis.asyncio as redis
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.config import config
from app.logger import AppLogger
from app.models.events import EventInfo

app_logger = AppLogger(__name__)


class QueueService:
    """Redis queue service for consuming rebalance events"""
    
    def __init__(self, service_container):
        self.redis = None
        self._redis_url = f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
        self.service_container = service_container
        self.notification_service = service_container.get_notification_service()
    
    async def _get_redis(self):
        """Get or create Redis connection"""
        if self.redis is None:
            self.redis = await redis.from_url(self._redis_url, decode_responses=True)
        return self.redis
    
    def _load_account_config(self, account_id: str) -> Dict[str, Any]:
        """
        Load account configuration from accounts.yaml
        
        Args:
            account_id: The account ID to look up
            
        Returns:
            Dict containing account configuration or empty dict if not found
        """
        try:
            accounts_path = os.path.join("/app", "accounts.yaml")
            if not os.path.exists(accounts_path):
                app_logger.log_warning(f"accounts.yaml not found at {accounts_path}")
                return {}
            
            with open(accounts_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            if not yaml_data:
                return {}
            
            # Extract accounts array from new YAML structure
            accounts_data = yaml_data.get('accounts', [])
            
            # Find account configuration
            for account in accounts_data:
                if account.get('account_id') == account_id:
                    return {
                        'strategy_name': account.get('notification', {}).get('channel', ''),
                        'cash_reserve_percent': account.get('rebalancing', {}).get('cash_reserve_percent', 0.0),
                        'replacement_set': account.get('replacement_set')
                    }
            
            app_logger.log_warning(f"Account {account_id} not found in accounts.yaml")
            return {}
            
        except Exception as e:
            app_logger.log_error(f"Failed to load account config for {account_id}: {e}")
            return {}
        
    async def get_next_event(self) -> Optional[EventInfo]:
        """
        Get next event from queue with timeout
        
        Returns:
            EventInfo: Event object if available, None if timeout
        """
        try:
            redis = await self._get_redis()
            result = await redis.brpop(
                "rebalance_queue", 
                timeout=config.processing.queue_timeout
            )
            
            if result:
                queue_name, event_json = result
                event_data = json.loads(event_json)
                exec_command = event_data.get('exec')
                if not exec_command:
                    app_logger.log_error(f"Event missing exec command: {event_data}")
                    return None
                
                # Parse datetime fields (assuming system timezone consistency)
                received_at = event_data.get('received_at')
                if received_at and isinstance(received_at, str):
                    received_at = datetime.fromisoformat(received_at.replace('Z', ''))
                elif not received_at:
                    received_at = datetime.now()
                
                created_at = event_data.get('created_at')
                if created_at and isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', ''))
                elif not created_at:
                    created_at = datetime.now()
                
                # Create EventInfo object from raw data
                event_info = EventInfo(
                    event_id=event_data.get('event_id'),
                    account_id=event_data.get('account_id'),
                    exec_command=exec_command,
                    status=event_data.get('status', 'pending'),
                    payload=event_data,
                    received_at=received_at,
                    times_queued=event_data.get('times_queued', 1),
                    created_at=created_at
                )
                
                app_logger.log_debug(f"Retrieved event from queue", event_info)
                return event_info
            
            return None
            
        except Exception as e:
            app_logger.log_error(f"Failed to get event from queue: {e}")
            return None
    
    async def requeue_event(self, event_info: EventInfo) -> EventInfo:
        """
        Put event back in queue for retry (at back of queue - FIFO retry)
        Increments times_queued counter
        """
        try:
            redis = await self._get_redis()
            account_id = event_info.account_id
            exec_command = event_info.exec_command
            
            deduplication_key = f"{account_id}:{exec_command}"
            
            # Increment times_queued counter
            event_info.times_queued += 1
            
            # Convert EventInfo back to the dictionary format expected by queue
            event_data = {
                **event_info.payload,
                'event_id': event_info.event_id,
                'account_id': event_info.account_id,
                'exec': event_info.exec_command,
                'status': event_info.status,
                'received_at': event_info.received_at.isoformat() if event_info.received_at else None,
                'times_queued': event_info.times_queued,
                'created_at': event_info.created_at.isoformat() if event_info.created_at else None
            }
            
            # Add to back of queue (rpush) and tracking set
            pipe = redis.pipeline()
            pipe.rpush("rebalance_queue", json.dumps(event_data))
            pipe.sadd("active_events_set", deduplication_key)
            await pipe.execute()
            
            app_logger.log_info(f"Event requeued for retry", event_info)
            
            return event_info
            
        except Exception as e:
            app_logger.log_error(f"Failed to requeue event: {e}")
            raise
    
    async def remove_from_queued(self, account_id: str, exec_command: str = None):
        """Remove account+command from active events set"""
        try:
            redis = await self._get_redis()
            
            if exec_command:
                # Remove specific account+command combination
                deduplication_key = f"{account_id}:{exec_command}"
                await redis.srem("active_events_set", deduplication_key)
                app_logger.log_debug(f"Removed event from active set")
            else:
                # Legacy support: remove all events for account
                active_events = await redis.smembers("active_events_set")
                keys_to_remove = [key for key in active_events if key.startswith(f"{account_id}:")]
                if keys_to_remove:
                    await redis.srem("active_events_set", *keys_to_remove)
                    app_logger.log_debug(f"Removed {len(keys_to_remove)} events for account from active set")
        except Exception as e:
            app_logger.log_error(f"Failed to remove from active events set: {e}")
            raise
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        try:
            redis = await self._get_redis()
            return await redis.llen("rebalance_queue")
        except Exception as e:
            app_logger.log_error(f"Failed to get queue length: {e}")
            return 0
    
    async def get_active_events(self) -> set:
        """Get set of currently active event keys (account_id:exec_command)"""
        try:
            redis = await self._get_redis()
            return await redis.smembers("active_events_set")
        except Exception as e:
            app_logger.log_error(f"Failed to get active events: {e}")
            return set()
    
    async def get_queued_accounts(self) -> set:
        """Get set of currently queued account IDs (legacy compatibility)"""
        try:
            redis = await self._get_redis()
            active_events = await redis.smembers("active_events_set")
            # Extract account IDs from account_id:exec_command keys
            accounts = set()
            for event_key in active_events:
                if ':' in event_key:
                    account_id = event_key.split(':', 1)[0]
                    accounts.add(account_id)
            return accounts
        except Exception as e:
            app_logger.log_error(f"Failed to get queued accounts: {e}")
            return set()
    
    async def requeue_event_retry(self, event_info: EventInfo) -> EventInfo:
        """
        Put event in retry queue for retry after configured delay
        Increments times_queued counter and removes from active events
        """
        try:
            redis = await self._get_redis()
            account_id = event_info.account_id
            exec_command = event_info.exec_command
            
            deduplication_key = f"{account_id}:{exec_command}"
            
            # Increment times_queued counter
            event_info.times_queued += 1
            
            # Convert EventInfo back to dictionary format for queue storage
            event_data = {
                **event_info.payload,
                'event_id': event_info.event_id,
                'account_id': event_info.account_id,
                'exec': event_info.exec_command,
                'status': event_info.status,
                'received_at': event_info.received_at.isoformat() if event_info.received_at else None,
                'times_queued': event_info.times_queued,
                'created_at': event_info.created_at.isoformat() if event_info.created_at else None
            }
            
            # Add to retry queue with current timestamp as score
            # Remove from active events set (no longer active until retry)
            current_time = int(time.time())
            pipe = redis.pipeline()
            pipe.zadd("rebalance_retry_set", {json.dumps(event_data): current_time})
            pipe.srem("active_events_set", deduplication_key)
            await pipe.execute()
            
            # Send retry notification
            await self.notification_service.send_notification(event_info, 'event_retry')
            
            app_logger.log_info(f"Event added to retry queue for retry", event_info)
            
            return event_info
            
        except Exception as e:
            app_logger.log_error(f"Failed to add event to retry queue: {e}")
            raise
    
    async def process_retry_events(self):
        """
        Process retry events that are ready for retry
        Move ready events from retry queue to main queue
        """
        try:
            redis = await self._get_redis()
            current_time = int(time.time())
            cutoff_time = current_time - config.processing.retry_delay_seconds
            
            # Find events ready for retry (added before cutoff time)
            ready_events = await redis.zrangebyscore(
                "rebalance_retry_set", 
                0, 
                cutoff_time
            )
            
            if not ready_events:
                app_logger.log_debug("No retry events ready for retry")
                return
            
            app_logger.log_info(f"Found {len(ready_events)} retry events ready for retry")
            
            # Move ready events to main queue and back to active set
            pipe = redis.pipeline()
            for event_json in ready_events:
                event_data = json.loads(event_json)
                account_id = event_data['account_id']
                exec_command = event_data.get('exec')
                deduplication_key = f"{account_id}:{exec_command}"
                
                # Add to main queue and active set
                pipe.lpush("rebalance_queue", event_json)
                pipe.sadd("active_events_set", deduplication_key)
                
                # Remove from retry queue
                pipe.zrem("rebalance_retry_set", event_json)
                
                app_logger.log_debug(f"Moving retry event to main queue")
            
            await pipe.execute()
            
            app_logger.log_info(f"Moved {len(ready_events)} retry events to main queue for retry")
            
        except Exception as e:
            app_logger.log_error(f"Failed to process retry events: {e}")
    
    async def get_retry_events_count(self) -> int:
        """Get count of events in retry queue"""
        try:
            redis = await self._get_redis()
            return await redis.zcard("rebalance_retry_set")
        except Exception as e:
            app_logger.log_error(f"Failed to get retry events count: {e}")
            return 0
    
    async def is_connected(self) -> bool:
        """Check if Redis connection is active"""
        try:
            redis = await self._get_redis()
            await redis.ping()
            return True
        except Exception:
            return False
    
    async def add_to_delayed_queue(self, event_info: EventInfo, next_execution_time: datetime) -> EventInfo:
        """
        Add event to delayed execution queue with specific execution time
        
        Args:
            event_info: Event to delay
            next_execution_time: When the event should be executed
            
        Returns:
            Updated EventInfo object
        """
        try:
            redis = await self._get_redis()
            account_id = event_info.account_id
            exec_command = event_info.exec_command
            
            deduplication_key = f"{account_id}:{exec_command}"
            
            # Convert EventInfo to dictionary format for queue storage
            event_data = {
                **event_info.payload,
                'event_id': event_info.event_id,
                'account_id': event_info.account_id,
                'exec': event_info.exec_command,
                'status': 'delayed',
                'received_at': event_info.received_at.isoformat() if event_info.received_at else None,
                'times_queued': event_info.times_queued,
                'created_at': event_info.created_at.isoformat() if event_info.created_at else None,
                'delayed_until': next_execution_time.isoformat()
            }
            
            # Add to delayed execution queue with execution timestamp as score
            # Remove from active events set (no longer active until ready for execution)
            execution_timestamp = int(next_execution_time.timestamp())
            pipe = redis.pipeline()
            pipe.zadd("delayed_execution_set", {json.dumps(event_data): execution_timestamp})
            pipe.srem("active_events_set", deduplication_key)
            await pipe.execute()
            
            # Send delayed notification
            await self.notification_service.send_notification(event_info, 'event_delayed', {'delayed_until': next_execution_time.strftime('%H:%M')})
            
            app_logger.log_info(f"Event added to delayed execution queue until {next_execution_time.strftime('%Y-%m-%d %H:%M:%S')}", event_info)
            
            return event_info
            
        except Exception as e:
            app_logger.log_error(f"Failed to add event to delayed execution queue: {e}")
            raise
    
    async def get_ready_delayed_events(self) -> List[str]:
        """
        Get events from delayed execution queue that are ready for execution
        
        Returns:
            List of event JSON strings ready for execution
        """
        try:
            redis = await self._get_redis()
            current_timestamp = int(time.time())
            
            # Find events ready for execution (execution time <= current time)
            ready_events = await redis.zrangebyscore(
                "delayed_execution_set", 
                0, 
                current_timestamp
            )
            
            return ready_events
            
        except Exception as e:
            app_logger.log_error(f"Failed to get ready delayed events: {e}")
            return []
    
    async def process_delayed_events(self):
        """
        Process delayed events that are ready for execution
        Move ready events from delayed queue to main queue
        """
        try:
            redis = await self._get_redis()
            ready_events = await self.get_ready_delayed_events()
            
            if not ready_events:
                app_logger.log_debug("No delayed events ready for execution")
                return
            
            app_logger.log_info(f"Found {len(ready_events)} delayed events ready for execution")
            
            # Move ready events to main queue and back to active set
            pipe = redis.pipeline()
            for event_json in ready_events:
                event_data = json.loads(event_json)
                account_id = event_data['account_id']
                exec_command = event_data.get('exec')
                deduplication_key = f"{account_id}:{exec_command}"
                
                # Reset status from 'delayed' back to original status
                if 'delayed_until' in event_data:
                    del event_data['delayed_until']
                event_data['status'] = event_data.get('original_status', 'pending')
                
                # Add to main queue and active set
                pipe.lpush("rebalance_queue", json.dumps(event_data))
                pipe.sadd("active_events_set", deduplication_key)
                
                # Remove from delayed execution queue
                pipe.zrem("delayed_execution_set", event_json)
                
                app_logger.log_debug(f"Moving delayed event to main queue for execution")
            
            await pipe.execute()
            
            app_logger.log_info(f"Moved {len(ready_events)} delayed events to main queue for execution")
            
        except Exception as e:
            app_logger.log_error(f"Failed to process delayed events: {e}")
    
    async def get_delayed_events_count(self) -> int:
        """Get count of events in delayed execution queue"""
        try:
            redis = await self._get_redis()
            return await redis.zcard("delayed_execution_set")
        except Exception as e:
            app_logger.log_error(f"Failed to get delayed events count: {e}")
            return 0
    
    async def get_delayed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from delayed execution queue with details"""
        try:
            redis = await self._get_redis()
            
            # Get events with scores (execution timestamps)
            events_with_scores = await redis.zrange(
                "delayed_execution_set", 
                0, 
                limit - 1, 
                withscores=True
            )
            
            events = []
            for event_json, score in events_with_scores:
                try:
                    event_data = json.loads(event_json)
                    # Add execution timestamp info
                    event_data['execution_timestamp'] = score
                    event_data['execution_time'] = datetime.fromtimestamp(score).isoformat()
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
            
            return events
            
        except Exception as e:
            app_logger.log_error(f"Failed to get delayed events: {e}")
            return []
    
    async def recover_stuck_active_events(self) -> int:
        """
        Recover events stuck in active_events_set after service restart
        
        When the event processor restarts, events may be stuck in the active_events_set
        because they were being processed when the service went down. This method
        moves all such events back to the rebalance_queue for reprocessing.
        
        Returns:
            int: Number of events recovered
        """
        try:
            redis = await self._get_redis()
            
            # Get all events currently in active_events_set
            active_event_keys = await redis.smembers("active_events_set")
            
            if not active_event_keys:
                return 0
            
            app_logger.log_info(f"Found {len(active_event_keys)} active events during startup")
            
            # For each active event key, we need to reconstruct and requeue the event
            # Since we only have the deduplication key (account_id:exec_command), 
            # we create a minimal event structure for reprocessing
            recovered_count = 0
            
            pipe = redis.pipeline()
            for event_key in active_event_keys:
                try:
                    # Parse account_id and exec_command from deduplication key
                    account_id, exec_command = event_key.split(':', 1)
                    
                    # Load account configuration from accounts.yaml
                    account_config = self._load_account_config(account_id)
                    
                    # Create event data for reprocessing with required account properties
                    recovery_event_data = {
                        'event_id': f"recovery_{int(time.time())}_{account_id}_{exec_command}",
                        'account_id': account_id,
                        'exec': exec_command,
                        'created_at': datetime.now().isoformat(),
                        'times_queued': 1,
                        'strategy_name': account_config.get('strategy_name', ''),
                        'cash_reserve_percent': account_config.get('cash_reserve_percent', 0.0),
                        'replacement_set': account_config.get('replacement_set'),
                    }
                    
                    # Add back to rebalance queue and active events set
                    pipe.lpush("rebalance_queue", json.dumps(recovery_event_data))
                    # Keep in active_events_set since it's now queued for processing
                    
                    recovered_count += 1
                    app_logger.log_debug(f"Recovering stuck event: {event_key}")
                    
                except Exception as e:
                    app_logger.log_error(f"Failed to recover stuck event {event_key}: {e}")
                    continue
            
            await pipe.execute()
            
            app_logger.log_info(f"Successfully queued {recovered_count} events to rebalance queue")
            return recovered_count
            
        except Exception as e:
            app_logger.log_error(f"Failed to recover stuck active events: {e}")
            return 0
    
