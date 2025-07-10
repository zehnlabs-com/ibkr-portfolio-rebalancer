"""
Redis Queue Service for Event Processor
"""
import json
import time
import redis.asyncio as redis
from typing import Dict, Any, Optional, List
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__)


class QueueService:
    """Redis queue service for consuming rebalance events"""
    
    def __init__(self):
        self.redis = None
        self._redis_url = f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
    
    async def _get_redis(self):
        """Get or create Redis connection"""
        if self.redis is None:
            self.redis = await redis.from_url(self._redis_url, decode_responses=True)
        return self.redis
        
    async def get_next_event(self) -> Optional[Dict[str, Any]]:
        """
        Get next event from queue with timeout
        
        Returns:
            Dict[str, Any]: Event data if available, None if timeout
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
                logger.debug(f"Retrieved event from queue", extra={
                    'event_id': event_data.get('event_id'),
                    'account_id': event_data.get('account_id')
                })
                return event_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get event from queue: {e}")
            return None
    
    async def requeue_event(self, event_data: Dict[str, Any]):
        """
        Put event back in queue for retry (at back of queue - FIFO retry)
        Increments times_queued counter
        """
        try:
            redis = await self._get_redis()
            account_id = event_data['account_id']
            
            # Extract command from event data - required field
            exec_command = event_data.get('data', {}).get('exec')
            if not exec_command:
                logger.error(f"Event missing required 'exec' field for account {account_id}, cannot requeue", extra={
                    'account_id': account_id,
                    'event_id': event_data.get('event_id'),
                    'event_data': event_data
                })
                raise ValueError(f"Event missing required 'exec' field for account {account_id}")
            
            deduplication_key = f"{account_id}:{exec_command}"
            
            # Increment times_queued counter
            current_times_queued = event_data.get('times_queued')
            if current_times_queued is None:
                logger.error(f"Event missing required 'times_queued' field, cannot requeue for account {account_id}", extra={
                    'account_id': account_id,
                    'event_id': event_data.get('event_id'),
                    'event_data': event_data
                })
                raise ValueError(f"Event missing required 'times_queued' field for account {account_id}")
            
            event_data['times_queued'] = current_times_queued + 1
            
            # Add to back of queue (rpush) and tracking set
            pipe = redis.pipeline()
            pipe.rpush("rebalance_queue", json.dumps(event_data))
            pipe.sadd("active_events_set", deduplication_key)
            await pipe.execute()
            
            logger.info(f"Event requeued for retry", extra={
                'event_id': event_data.get('event_id'),
                'account_id': account_id,
                'exec_command': exec_command,
                'times_queued': event_data['times_queued'],
                'deduplication_key': deduplication_key
            })
            
        except Exception as e:
            logger.error(f"Failed to requeue event: {e}")
            raise
    
    async def remove_from_queued(self, account_id: str, exec_command: str = None):
        """Remove account+command from active events set"""
        try:
            redis = await self._get_redis()
            
            if exec_command:
                # Remove specific account+command combination
                deduplication_key = f"{account_id}:{exec_command}"
                await redis.srem("active_events_set", deduplication_key)
                logger.debug(f"Removed event from active set", extra={
                    'account_id': account_id,
                    'exec_command': exec_command,
                    'deduplication_key': deduplication_key
                })
            else:
                # Legacy support: remove all events for account
                active_events = await redis.smembers("active_events_set")
                keys_to_remove = [key for key in active_events if key.startswith(f"{account_id}:")]
                if keys_to_remove:
                    await redis.srem("active_events_set", *keys_to_remove)
                    logger.debug(f"Removed {len(keys_to_remove)} events for account from active set", extra={
                        'account_id': account_id,
                        'removed_keys': keys_to_remove
                    })
        except Exception as e:
            logger.error(f"Failed to remove from active events set: {e}")
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        try:
            redis = await self._get_redis()
            return await redis.llen("rebalance_queue")
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    async def get_active_events(self) -> set:
        """Get set of currently active event keys (account_id:exec_command)"""
        try:
            redis = await self._get_redis()
            return await redis.smembers("active_events_set")
        except Exception as e:
            logger.error(f"Failed to get active events: {e}")
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
            logger.error(f"Failed to get queued accounts: {e}")
            return set()
    
    async def requeue_event_delayed(self, event_data: Dict[str, Any]):
        """
        Put event in delayed queue for retry after configured delay
        Increments times_queued counter and removes from active events
        """
        try:
            redis = await self._get_redis()
            account_id = event_data['account_id']
            
            # Extract command from event data - required field
            exec_command = event_data.get('data', {}).get('exec')
            if not exec_command:
                logger.error(f"Event missing required 'exec' field for account {account_id}, cannot requeue", extra={
                    'account_id': account_id,
                    'event_id': event_data.get('event_id'),
                    'event_data': event_data
                })
                raise ValueError(f"Event missing required 'exec' field for account {account_id}")
            
            deduplication_key = f"{account_id}:{exec_command}"
            
            # Increment times_queued counter
            current_times_queued = event_data.get('times_queued')
            if current_times_queued is None:
                logger.error(f"Event missing required 'times_queued' field, cannot requeue for account {account_id}", extra={
                    'account_id': account_id,
                    'event_id': event_data.get('event_id'),
                    'event_data': event_data
                })
                raise ValueError(f"Event missing required 'times_queued' field for account {account_id}")
            
            event_data['times_queued'] = current_times_queued + 1
            
            # Add to delayed queue with current timestamp as score
            # Remove from active events set (no longer active until retry)
            current_time = int(time.time())
            pipe = redis.pipeline()
            pipe.zadd("rebalance_delayed_set", {json.dumps(event_data): current_time})
            pipe.srem("active_events_set", deduplication_key)
            await pipe.execute()
            
            logger.info(f"Event added to delayed queue for retry", extra={
                'event_id': event_data.get('event_id'),
                'account_id': account_id,
                'exec_command': exec_command,
                'times_queued': event_data['times_queued'],
                'deduplication_key': deduplication_key,
                'retry_after': current_time + config.processing.retry_delay_seconds
            })
            
        except Exception as e:
            logger.error(f"Failed to add event to delayed queue: {e}")
            raise
    
    async def process_delayed_events(self):
        """
        Process delayed events that are ready for retry
        Move ready events from delayed queue to main queue
        """
        try:
            redis = await self._get_redis()
            current_time = int(time.time())
            cutoff_time = current_time - config.processing.retry_delay_seconds
            
            # Find events ready for retry (added before cutoff time)
            ready_events = await redis.zrangebyscore(
                "rebalance_delayed_set", 
                0, 
                cutoff_time
            )
            
            if not ready_events:
                logger.debug("No delayed events ready for retry")
                return
            
            logger.info(f"Found {len(ready_events)} delayed events ready for retry")
            
            # Move ready events to main queue and back to active set
            pipe = redis.pipeline()
            for event_json in ready_events:
                event_data = json.loads(event_json)
                account_id = event_data['account_id']
                exec_command = event_data.get('data', {}).get('exec')
                deduplication_key = f"{account_id}:{exec_command}"
                
                # Add to main queue and active set
                pipe.lpush("rebalance_queue", event_json)
                pipe.sadd("active_events_set", deduplication_key)
                
                # Remove from delayed queue
                pipe.zrem("rebalance_delayed_set", event_json)
                
                logger.debug(f"Moving delayed event to main queue", extra={
                    'event_id': event_data.get('event_id'),
                    'account_id': account_id,
                    'exec_command': exec_command,
                    'times_queued': event_data.get('times_queued')
                })
            
            await pipe.execute()
            
            logger.info(f"Moved {len(ready_events)} delayed events to main queue for retry")
            
        except Exception as e:
            logger.error(f"Failed to process delayed events: {e}")
    
    async def get_delayed_events_count(self) -> int:
        """Get count of events in delayed queue"""
        try:
            redis = await self._get_redis()
            return await redis.zcard("rebalance_delayed_set")
        except Exception as e:
            logger.error(f"Failed to get delayed events count: {e}")
            return 0
    
    async def is_connected(self) -> bool:
        """Check if Redis connection is active"""
        try:
            redis = await self._get_redis()
            await redis.ping()
            return True
        except Exception:
            return False