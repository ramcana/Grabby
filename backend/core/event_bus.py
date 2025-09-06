"""
Event Bus System for Grabby Video Downloader
Enables real-time communication between components
"""
import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional, Set, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import json
import weakref
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)

class EventType(Enum):
    # Download lifecycle events
    DOWNLOAD_QUEUED = "download.queued"
    DOWNLOAD_STARTED = "download.started"
    DOWNLOAD_PROGRESS = "download.progress"
    DOWNLOAD_COMPLETED = "download.completed"
    DOWNLOAD_FAILED = "download.failed"
    DOWNLOAD_CANCELLED = "download.cancelled"
    DOWNLOAD_PAUSED = "download.paused"
    DOWNLOAD_RESUMED = "download.resumed"
    
    # Queue events
    QUEUE_ITEM_ADDED = "queue.item_added"
    QUEUE_ITEM_REMOVED = "queue.item_removed"
    QUEUE_STATUS_CHANGED = "queue.status_changed"
    QUEUE_CLEARED = "queue.cleared"
    
    # Playlist events
    PLAYLIST_STARTED = "playlist.started"
    PLAYLIST_ITEM_COMPLETED = "playlist.item_completed"
    PLAYLIST_COMPLETED = "playlist.completed"
    PLAYLIST_FAILED = "playlist.failed"
    
    # Plugin events
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_ERROR = "plugin.error"
    POST_PROCESS_STARTED = "post_process.started"
    POST_PROCESS_COMPLETED = "post_process.completed"
    POST_PROCESS_FAILED = "post_process.failed"
    
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SETTINGS_CHANGED = "settings.changed"
    
    # Engine events
    ENGINE_SELECTED = "engine.selected"
    ENGINE_SWITCHED = "engine.switched"
    ENGINE_ERROR = "engine.error"
    
    # Database events
    DATABASE_CONNECTED = "database.connected"
    DATABASE_DISCONNECTED = "database.disconnected"
    RECORD_CREATED = "record.created"
    RECORD_UPDATED = "record.updated"
    RECORD_DELETED = "record.deleted"

@dataclass
class Event:
    """Represents an event in the system"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.SYSTEM_STARTUP
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'id': self.id,
            'type': self.type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=EventType(data['type']),
            source=data.get('source', 'unknown'),
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data.get('data', {}),
            metadata=data.get('metadata', {})
        )

class EventHandler:
    """Base class for event handlers"""
    
    def __init__(self, handler_id: str, callback: Callable[[Event], Any]):
        self.id = handler_id
        self.callback = callback
        self.is_async = asyncio.iscoroutinefunction(callback)
    
    async def handle(self, event: Event):
        """Handle an event"""
        try:
            if self.is_async:
                await self.callback(event)
            else:
                self.callback(event)
        except Exception as e:
            logger.error(f"Error in event handler {self.id}: {e}")

class EventBus:
    """
    Central event bus for inter-component communication
    Supports both sync and async event handlers
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        
        # Event handlers organized by event type
        self.handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        
        # Wildcard handlers (listen to all events)
        self.wildcard_handlers: List[EventHandler] = []
        
        # Event history for debugging and replay
        self.event_history: List[Event] = []
        
        # WebSocket connections for real-time updates
        self.websocket_connections: Set[Any] = set()
        
        # Statistics
        self.stats = {
            'events_published': 0,
            'events_handled': 0,
            'handler_errors': 0,
            'start_time': datetime.now()
        }
        
        # Event filters
        self.filters: List[Callable[[Event], bool]] = []
        
        # Weak references to prevent memory leaks
        self._weak_refs: Set[weakref.ref] = set()
    
    def subscribe(self, 
                  event_type: Union[EventType, str], 
                  callback: Callable[[Event], Any],
                  handler_id: Optional[str] = None) -> str:
        """
        Subscribe to events of a specific type
        
        Args:
            event_type: Type of event to listen for
            callback: Function to call when event occurs
            handler_id: Optional custom handler ID
            
        Returns:
            Handler ID for unsubscribing
        """
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        
        handler_id = handler_id or f"handler_{len(self.handlers[event_type])}"
        handler = EventHandler(handler_id, callback)
        
        self.handlers[event_type].append(handler)
        
        logger.debug(f"Subscribed handler {handler_id} to {event_type.value}")
        return handler_id
    
    def subscribe_all(self, 
                      callback: Callable[[Event], Any],
                      handler_id: Optional[str] = None) -> str:
        """
        Subscribe to all events (wildcard subscription)
        
        Args:
            callback: Function to call for any event
            handler_id: Optional custom handler ID
            
        Returns:
            Handler ID for unsubscribing
        """
        handler_id = handler_id or f"wildcard_handler_{len(self.wildcard_handlers)}"
        handler = EventHandler(handler_id, callback)
        
        self.wildcard_handlers.append(handler)
        
        logger.debug(f"Subscribed wildcard handler {handler_id}")
        return handler_id
    
    def unsubscribe(self, event_type: Union[EventType, str], handler_id: str) -> bool:
        """
        Unsubscribe a handler from events
        
        Args:
            event_type: Type of event to unsubscribe from
            handler_id: ID of handler to remove
            
        Returns:
            True if handler was found and removed
        """
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        
        handlers = self.handlers[event_type]
        for i, handler in enumerate(handlers):
            if handler.id == handler_id:
                del handlers[i]
                logger.debug(f"Unsubscribed handler {handler_id} from {event_type.value}")
                return True
        
        return False
    
    def unsubscribe_all(self, handler_id: str) -> bool:
        """
        Unsubscribe a wildcard handler
        
        Args:
            handler_id: ID of handler to remove
            
        Returns:
            True if handler was found and removed
        """
        for i, handler in enumerate(self.wildcard_handlers):
            if handler.id == handler_id:
                del self.wildcard_handlers[i]
                logger.debug(f"Unsubscribed wildcard handler {handler_id}")
                return True
        
        return False
    
    async def publish(self, 
                      event_type: Union[EventType, str],
                      source: str,
                      data: Optional[Dict[str, Any]] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> Event:
        """
        Publish an event to all subscribers
        
        Args:
            event_type: Type of event
            source: Source component that generated the event
            data: Event data payload
            metadata: Additional metadata
            
        Returns:
            The published event
        """
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        
        event = Event(
            type=event_type,
            source=source,
            data=data or {},
            metadata=metadata or {}
        )
        
        # Apply filters
        for filter_func in self.filters:
            if not filter_func(event):
                logger.debug(f"Event {event.id} filtered out")
                return event
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Update statistics
        self.stats['events_published'] += 1
        
        # Handle the event
        await self._handle_event(event)
        
        # Broadcast to WebSocket connections
        await self._broadcast_to_websockets(event)
        
        logger.debug(f"Published event: {event_type.value} from {source}")
        return event
    
    async def _handle_event(self, event: Event):
        """Handle an event by calling all registered handlers"""
        
        # Get handlers for this specific event type
        handlers = self.handlers.get(event.type, [])
        
        # Add wildcard handlers
        all_handlers = handlers + self.wildcard_handlers
        
        # Execute all handlers
        tasks = []
        for handler in all_handlers:
            tasks.append(self._execute_handler(handler, event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_handler(self, handler: EventHandler, event: Event):
        """Execute a single event handler"""
        try:
            await handler.handle(event)
            self.stats['events_handled'] += 1
        except Exception as e:
            self.stats['handler_errors'] += 1
            logger.error(f"Handler {handler.id} failed for event {event.id}: {e}")
    
    async def _broadcast_to_websockets(self, event: Event):
        """Broadcast event to WebSocket connections"""
        if not self.websocket_connections:
            return
        
        message = json.dumps(event.to_dict())
        
        # Remove closed connections
        closed_connections = set()
        
        for ws in self.websocket_connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.debug(f"WebSocket connection closed: {e}")
                closed_connections.add(ws)
        
        # Clean up closed connections
        self.websocket_connections -= closed_connections
    
    def add_websocket(self, websocket):
        """Add a WebSocket connection for real-time updates"""
        self.websocket_connections.add(websocket)
        logger.debug(f"Added WebSocket connection, total: {len(self.websocket_connections)}")
    
    def remove_websocket(self, websocket):
        """Remove a WebSocket connection"""
        self.websocket_connections.discard(websocket)
        logger.debug(f"Removed WebSocket connection, total: {len(self.websocket_connections)}")
    
    def add_filter(self, filter_func: Callable[[Event], bool]):
        """Add an event filter function"""
        self.filters.append(filter_func)
    
    def remove_filter(self, filter_func: Callable[[Event], bool]):
        """Remove an event filter function"""
        if filter_func in self.filters:
            self.filters.remove(filter_func)
    
    def get_event_history(self, 
                          event_type: Optional[EventType] = None,
                          source: Optional[str] = None,
                          limit: int = 100) -> List[Event]:
        """
        Get event history with optional filtering
        
        Args:
            event_type: Filter by event type
            source: Filter by source
            limit: Maximum number of events to return
            
        Returns:
            List of events matching criteria
        """
        events = self.event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        if source:
            events = [e for e in events if e.source == source]
        
        return events[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        uptime = datetime.now() - self.stats['start_time']
        
        return {
            **self.stats,
            'uptime_seconds': uptime.total_seconds(),
            'active_handlers': sum(len(handlers) for handlers in self.handlers.values()),
            'wildcard_handlers': len(self.wildcard_handlers),
            'websocket_connections': len(self.websocket_connections),
            'event_history_size': len(self.event_history),
            'active_filters': len(self.filters)
        }
    
    def clear_history(self):
        """Clear event history"""
        self.event_history.clear()
        logger.info("Event history cleared")
    
    async def shutdown(self):
        """Shutdown the event bus"""
        await self.publish(EventType.SYSTEM_SHUTDOWN, "event_bus")
        
        # Close all WebSocket connections
        for ws in list(self.websocket_connections):
            try:
                await ws.close()
            except Exception:
                pass
        
        self.websocket_connections.clear()
        self.handlers.clear()
        self.wildcard_handlers.clear()
        
        logger.info("Event bus shutdown complete")

# Global event bus instance
_global_event_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus

def set_event_bus(event_bus: EventBus):
    """Set the global event bus instance"""
    global _global_event_bus
    _global_event_bus = event_bus

# Convenience functions
async def publish_event(event_type: Union[EventType, str], 
                       source: str,
                       data: Optional[Dict[str, Any]] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> Event:
    """Publish an event using the global event bus"""
    return await get_event_bus().publish(event_type, source, data, metadata)

def subscribe_to_event(event_type: Union[EventType, str], 
                      callback: Callable[[Event], Any],
                      handler_id: Optional[str] = None) -> str:
    """Subscribe to events using the global event bus"""
    return get_event_bus().subscribe(event_type, callback, handler_id)

def subscribe_to_all_events(callback: Callable[[Event], Any],
                           handler_id: Optional[str] = None) -> str:
    """Subscribe to all events using the global event bus"""
    return get_event_bus().subscribe_all(callback, handler_id)

# Example usage and testing
async def main():
    """Example usage of the event bus"""
    
    # Create event bus
    event_bus = EventBus()
    
    # Example event handlers
    async def download_handler(event: Event):
        print(f"Download event: {event.type.value} - {event.data}")
    
    def system_handler(event: Event):
        print(f"System event: {event.type.value} from {event.source}")
    
    # Subscribe to specific events
    event_bus.subscribe(EventType.DOWNLOAD_STARTED, download_handler)
    event_bus.subscribe(EventType.DOWNLOAD_COMPLETED, download_handler)
    
    # Subscribe to all system events
    event_bus.subscribe_all(system_handler, "system_logger")
    
    # Publish some test events
    await event_bus.publish(
        EventType.DOWNLOAD_STARTED,
        "downloader",
        {"url": "https://example.com/video", "title": "Test Video"}
    )
    
    await event_bus.publish(
        EventType.DOWNLOAD_PROGRESS,
        "downloader",
        {"url": "https://example.com/video", "progress": 50.0}
    )
    
    await event_bus.publish(
        EventType.DOWNLOAD_COMPLETED,
        "downloader",
        {"url": "https://example.com/video", "file_path": "/downloads/test.mp4"}
    )
    
    # Show statistics
    stats = event_bus.get_statistics()
    print(f"Event bus statistics: {stats}")
    
    # Show event history
    history = event_bus.get_event_history(limit=5)
    print(f"Recent events: {len(history)}")
    for event in history:
        print(f"  {event.timestamp}: {event.type.value} from {event.source}")

if __name__ == "__main__":
    asyncio.run(main())
