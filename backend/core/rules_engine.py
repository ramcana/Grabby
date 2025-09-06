"""
Smart Rules Engine for Grabby
Provides intelligent automation for download management based on configurable rules.
"""
import re
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import logging

from .event_bus import get_event_bus, Event
from .queue_manager import QueuePriority, QueueStatus

logger = logging.getLogger(__name__)

class RuleConditionType(Enum):
    """Types of rule conditions"""
    URL_PATTERN = "url_pattern"
    DOMAIN = "domain"
    TITLE_PATTERN = "title_pattern"
    UPLOADER = "uploader"
    DURATION = "duration"
    FILE_SIZE = "file_size"
    VIEW_COUNT = "view_count"
    UPLOAD_DATE = "upload_date"
    TIME_OF_DAY = "time_of_day"
    DAY_OF_WEEK = "day_of_week"
    QUEUE_SIZE = "queue_size"
    BANDWIDTH_USAGE = "bandwidth_usage"

class RuleActionType(Enum):
    """Types of rule actions"""
    SET_PRIORITY = "set_priority"
    SET_PROFILE = "set_profile"
    SET_QUALITY = "set_quality"
    SET_OUTPUT_PATH = "set_output_path"
    RATE_LIMIT = "rate_limit"
    SCHEDULE_DOWNLOAD = "schedule_download"
    BLOCK_DOWNLOAD = "block_download"
    NOTIFY = "notify"
    AUTO_ORGANIZE = "auto_organize"
    EXTRACT_AUDIO = "extract_audio"

class ComparisonOperator(Enum):
    """Comparison operators for conditions"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES = "matches"
    NOT_MATCHES = "not_matches"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    IN_RANGE = "in_range"

@dataclass
class RuleCondition:
    """A single condition in a rule"""
    condition_type: RuleConditionType
    operator: ComparisonOperator
    value: Any
    case_sensitive: bool = False
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate this condition against the given context"""
        try:
            actual_value = self._get_context_value(context)
            if actual_value is None:
                return False
            
            return self._compare_values(actual_value, self.value, self.operator)
            
        except Exception as e:
            logger.error(f"Error evaluating condition {self.condition_type}: {e}")
            return False
    
    def _get_context_value(self, context: Dict[str, Any]) -> Any:
        """Extract the relevant value from context"""
        mapping = {
            RuleConditionType.URL_PATTERN: lambda c: c.get('url', ''),
            RuleConditionType.DOMAIN: lambda c: self._extract_domain(c.get('url', '')),
            RuleConditionType.TITLE_PATTERN: lambda c: c.get('title', ''),
            RuleConditionType.UPLOADER: lambda c: c.get('uploader', ''),
            RuleConditionType.DURATION: lambda c: c.get('duration_seconds', 0),
            RuleConditionType.FILE_SIZE: lambda c: c.get('file_size', 0),
            RuleConditionType.VIEW_COUNT: lambda c: c.get('view_count', 0),
            RuleConditionType.UPLOAD_DATE: lambda c: c.get('upload_date'),
            RuleConditionType.TIME_OF_DAY: lambda c: datetime.now().hour,
            RuleConditionType.DAY_OF_WEEK: lambda c: datetime.now().weekday(),
            RuleConditionType.QUEUE_SIZE: lambda c: c.get('queue_size', 0),
            RuleConditionType.BANDWIDTH_USAGE: lambda c: c.get('bandwidth_usage', 0),
        }
        
        extractor = mapping.get(self.condition_type)
        return extractor(context) if extractor else None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.netloc.lower()
        except:
            return ''
    
    def _compare_values(self, actual: Any, expected: Any, operator: ComparisonOperator) -> bool:
        """Compare two values using the specified operator"""
        if operator == ComparisonOperator.EQUALS:
            return self._normalize_value(actual) == self._normalize_value(expected)
        elif operator == ComparisonOperator.NOT_EQUALS:
            return self._normalize_value(actual) != self._normalize_value(expected)
        elif operator == ComparisonOperator.CONTAINS:
            return self._normalize_value(expected) in self._normalize_value(str(actual))
        elif operator == ComparisonOperator.NOT_CONTAINS:
            return self._normalize_value(expected) not in self._normalize_value(str(actual))
        elif operator == ComparisonOperator.MATCHES:
            return bool(re.search(expected, str(actual), 0 if self.case_sensitive else re.IGNORECASE))
        elif operator == ComparisonOperator.NOT_MATCHES:
            return not bool(re.search(expected, str(actual), 0 if self.case_sensitive else re.IGNORECASE))
        elif operator == ComparisonOperator.GREATER_THAN:
            return float(actual) > float(expected)
        elif operator == ComparisonOperator.LESS_THAN:
            return float(actual) < float(expected)
        elif operator == ComparisonOperator.GREATER_EQUAL:
            return float(actual) >= float(expected)
        elif operator == ComparisonOperator.LESS_EQUAL:
            return float(actual) <= float(expected)
        elif operator == ComparisonOperator.IN_RANGE:
            if isinstance(expected, (list, tuple)) and len(expected) == 2:
                return float(expected[0]) <= float(actual) <= float(expected[1])
        
        return False
    
    def _normalize_value(self, value: Any) -> str:
        """Normalize value for comparison"""
        result = str(value)
        return result if self.case_sensitive else result.lower()

@dataclass
class RuleAction:
    """An action to be executed when a rule matches"""
    action_type: RuleActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    async def execute(self, context: Dict[str, Any], rules_engine: 'SmartRulesEngine') -> bool:
        """Execute this action"""
        try:
            handler = getattr(rules_engine, f'_execute_{self.action_type.value}', None)
            if handler:
                return await handler(context, self.parameters)
            else:
                logger.warning(f"No handler for action type: {self.action_type}")
                return False
        except Exception as e:
            logger.error(f"Error executing action {self.action_type}: {e}")
            return False

@dataclass
class Rule:
    """A complete rule with conditions and actions"""
    id: str
    name: str
    description: str
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    enabled: bool = True
    priority: int = 0  # Higher numbers = higher priority
    condition_logic: str = "AND"  # "AND" or "OR"
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if this rule matches the given context"""
        if not self.enabled or not self.conditions:
            return False
        
        results = [condition.evaluate(context) for condition in self.conditions]
        
        if self.condition_logic == "OR":
            return any(results)
        else:  # AND
            return all(results)
    
    async def execute_actions(self, context: Dict[str, Any], rules_engine: 'SmartRulesEngine') -> List[bool]:
        """Execute all actions for this rule"""
        results = []
        for action in self.actions:
            result = await action.execute(context, rules_engine)
            results.append(result)
        
        # Update trigger statistics
        self.last_triggered = datetime.now()
        self.trigger_count += 1
        
        return results

class SmartRulesEngine:
    """Main rules engine for intelligent download management"""
    
    def __init__(self, rules_file: Optional[str] = None):
        self.rules: List[Rule] = []
        self.rules_file = rules_file or "rules.json"
        self.event_bus = get_event_bus()
        self.statistics = {
            'rules_triggered': 0,
            'actions_executed': 0,
            'last_evaluation': None
        }
        
        # Set up event listeners
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Set up event bus listeners"""
        self.event_bus.subscribe('download.queued', self._on_download_queued)
        self.event_bus.subscribe('download.started', self._on_download_started)
        self.event_bus.subscribe('download.progress', self._on_download_progress)
        self.event_bus.subscribe('download.completed', self._on_download_completed)
        self.event_bus.subscribe('queue.status_changed', self._on_queue_status_changed)
    
    async def _on_download_queued(self, event: Event):
        """Handle download queued event"""
        await self.evaluate_rules('download_queued', event.data)
    
    async def _on_download_started(self, event: Event):
        """Handle download started event"""
        await self.evaluate_rules('download_started', event.data)
    
    async def _on_download_progress(self, event: Event):
        """Handle download progress event"""
        await self.evaluate_rules('download_progress', event.data)
    
    async def _on_download_completed(self, event: Event):
        """Handle download completed event"""
        await self.evaluate_rules('download_completed', event.data)
    
    async def _on_queue_status_changed(self, event: Event):
        """Handle queue status changed event"""
        await self.evaluate_rules('queue_status_changed', event.data)
    
    async def evaluate_rules(self, trigger_event: str, context: Dict[str, Any]) -> List[Rule]:
        """Evaluate all rules against the given context"""
        triggered_rules = []
        
        # Add trigger event to context
        context['trigger_event'] = trigger_event
        context['timestamp'] = datetime.now()
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            try:
                if rule.matches(context):
                    logger.info(f"Rule '{rule.name}' triggered for {trigger_event}")
                    
                    # Execute rule actions
                    results = await rule.execute_actions(context, self)
                    triggered_rules.append(rule)
                    
                    # Update statistics
                    self.statistics['rules_triggered'] += 1
                    self.statistics['actions_executed'] += len(results)
                    
            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.name}': {e}")
        
        self.statistics['last_evaluation'] = datetime.now()
        return triggered_rules
    
    # Action execution methods
    async def _execute_set_priority(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Set download priority"""
        try:
            download_id = context.get('download_id')
            priority = params.get('priority', 'medium')
            
            if download_id:
                # Update priority in queue manager
                await self.event_bus.emit('queue.priority_changed', {
                    'download_id': download_id,
                    'priority': priority
                })
                return True
        except Exception as e:
            logger.error(f"Failed to set priority: {e}")
        return False
    
    async def _execute_set_profile(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Set download profile"""
        try:
            download_id = context.get('download_id')
            profile = params.get('profile', 'default')
            
            if download_id:
                await self.event_bus.emit('download.profile_changed', {
                    'download_id': download_id,
                    'profile': profile
                })
                return True
        except Exception as e:
            logger.error(f"Failed to set profile: {e}")
        return False
    
    async def _execute_set_quality(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Set download quality"""
        try:
            download_id = context.get('download_id')
            quality = params.get('quality', 'best[height<=1080]')
            
            if download_id:
                await self.event_bus.emit('download.quality_changed', {
                    'download_id': download_id,
                    'quality': quality
                })
                return True
        except Exception as e:
            logger.error(f"Failed to set quality: {e}")
        return False
    
    async def _execute_set_output_path(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Set custom output path"""
        try:
            download_id = context.get('download_id')
            output_path = params.get('output_path')
            
            if download_id and output_path:
                await self.event_bus.emit('download.output_path_changed', {
                    'download_id': download_id,
                    'output_path': output_path
                })
                return True
        except Exception as e:
            logger.error(f"Failed to set output path: {e}")
        return False
    
    async def _execute_rate_limit(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Apply rate limiting"""
        try:
            download_id = context.get('download_id')
            rate_limit = params.get('rate_limit')
            
            if download_id and rate_limit:
                await self.event_bus.emit('download.rate_limit_changed', {
                    'download_id': download_id,
                    'rate_limit': rate_limit
                })
                return True
        except Exception as e:
            logger.error(f"Failed to set rate limit: {e}")
        return False
    
    async def _execute_schedule_download(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Schedule download for later"""
        try:
            download_id = context.get('download_id')
            delay_minutes = params.get('delay_minutes', 60)
            
            if download_id:
                scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
                await self.event_bus.emit('download.scheduled', {
                    'download_id': download_id,
                    'scheduled_time': scheduled_time
                })
                return True
        except Exception as e:
            logger.error(f"Failed to schedule download: {e}")
        return False
    
    async def _execute_block_download(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Block download"""
        try:
            download_id = context.get('download_id')
            reason = params.get('reason', 'Blocked by rule')
            
            if download_id:
                await self.event_bus.emit('download.blocked', {
                    'download_id': download_id,
                    'reason': reason
                })
                return True
        except Exception as e:
            logger.error(f"Failed to block download: {e}")
        return False
    
    async def _execute_notify(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Send notification"""
        try:
            message = params.get('message', 'Rule triggered')
            severity = params.get('severity', 'info')
            
            await self.event_bus.emit('notification.send', {
                'message': message,
                'severity': severity,
                'context': context
            })
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
        return False
    
    async def _execute_auto_organize(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Auto-organize download"""
        try:
            download_id = context.get('download_id')
            organization_pattern = params.get('pattern', '{uploader}/{title}')
            
            if download_id:
                await self.event_bus.emit('download.auto_organize', {
                    'download_id': download_id,
                    'pattern': organization_pattern
                })
                return True
        except Exception as e:
            logger.error(f"Failed to auto-organize: {e}")
        return False
    
    async def _execute_extract_audio(self, context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Extract audio from video"""
        try:
            download_id = context.get('download_id')
            audio_format = params.get('format', 'mp3')
            
            if download_id:
                await self.event_bus.emit('download.extract_audio', {
                    'download_id': download_id,
                    'format': audio_format
                })
                return True
        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
        return False
    
    # Rule management methods
    def add_rule(self, rule: Rule) -> bool:
        """Add a new rule"""
        try:
            # Check for duplicate IDs
            if any(r.id == rule.id for r in self.rules):
                logger.warning(f"Rule with ID '{rule.id}' already exists")
                return False
            
            self.rules.append(rule)
            logger.info(f"Added rule: {rule.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add rule: {e}")
            return False
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID"""
        try:
            original_count = len(self.rules)
            self.rules = [r for r in self.rules if r.id != rule_id]
            
            if len(self.rules) < original_count:
                logger.info(f"Removed rule: {rule_id}")
                return True
            else:
                logger.warning(f"Rule not found: {rule_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to remove rule: {e}")
            return False
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID"""
        return next((r for r in self.rules if r.id == rule_id), None)
    
    def update_rule(self, rule_id: str, updated_rule: Rule) -> bool:
        """Update an existing rule"""
        try:
            for i, rule in enumerate(self.rules):
                if rule.id == rule_id:
                    self.rules[i] = updated_rule
                    logger.info(f"Updated rule: {rule_id}")
                    return True
            
            logger.warning(f"Rule not found for update: {rule_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update rule: {e}")
            return False
    
    def list_rules(self) -> List[Rule]:
        """Get all rules"""
        return self.rules.copy()
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False
    
    # Persistence methods
    def save_rules(self, file_path: Optional[str] = None) -> bool:
        """Save rules to file"""
        try:
            path = file_path or self.rules_file
            
            # Convert rules to serializable format
            rules_data = []
            for rule in self.rules:
                rule_dict = {
                    'id': rule.id,
                    'name': rule.name,
                    'description': rule.description,
                    'enabled': rule.enabled,
                    'priority': rule.priority,
                    'condition_logic': rule.condition_logic,
                    'created_at': rule.created_at.isoformat(),
                    'last_triggered': rule.last_triggered.isoformat() if rule.last_triggered else None,
                    'trigger_count': rule.trigger_count,
                    'conditions': [
                        {
                            'condition_type': c.condition_type.value,
                            'operator': c.operator.value,
                            'value': c.value,
                            'case_sensitive': c.case_sensitive
                        }
                        for c in rule.conditions
                    ],
                    'actions': [
                        {
                            'action_type': a.action_type.value,
                            'parameters': a.parameters
                        }
                        for a in rule.actions
                    ]
                }
                rules_data.append(rule_dict)
            
            with open(path, 'w') as f:
                json.dump(rules_data, f, indent=2)
            
            logger.info(f"Saved {len(self.rules)} rules to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
            return False
    
    def load_rules(self, file_path: Optional[str] = None) -> bool:
        """Load rules from file"""
        try:
            path = file_path or self.rules_file
            
            if not Path(path).exists():
                logger.info(f"Rules file not found: {path}")
                return True  # Not an error, just no rules to load
            
            with open(path, 'r') as f:
                rules_data = json.load(f)
            
            loaded_rules = []
            for rule_dict in rules_data:
                # Parse conditions
                conditions = []
                for c_dict in rule_dict.get('conditions', []):
                    condition = RuleCondition(
                        condition_type=RuleConditionType(c_dict['condition_type']),
                        operator=ComparisonOperator(c_dict['operator']),
                        value=c_dict['value'],
                        case_sensitive=c_dict.get('case_sensitive', False)
                    )
                    conditions.append(condition)
                
                # Parse actions
                actions = []
                for a_dict in rule_dict.get('actions', []):
                    action = RuleAction(
                        action_type=RuleActionType(a_dict['action_type']),
                        parameters=a_dict.get('parameters', {})
                    )
                    actions.append(action)
                
                # Create rule
                rule = Rule(
                    id=rule_dict['id'],
                    name=rule_dict['name'],
                    description=rule_dict['description'],
                    conditions=conditions,
                    actions=actions,
                    enabled=rule_dict.get('enabled', True),
                    priority=rule_dict.get('priority', 0),
                    condition_logic=rule_dict.get('condition_logic', 'AND'),
                    created_at=datetime.fromisoformat(rule_dict['created_at']),
                    last_triggered=datetime.fromisoformat(rule_dict['last_triggered']) if rule_dict.get('last_triggered') else None,
                    trigger_count=rule_dict.get('trigger_count', 0)
                )
                loaded_rules.append(rule)
            
            self.rules = loaded_rules
            logger.info(f"Loaded {len(self.rules)} rules from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rules engine statistics"""
        return {
            **self.statistics,
            'total_rules': len(self.rules),
            'enabled_rules': len([r for r in self.rules if r.enabled]),
            'disabled_rules': len([r for r in self.rules if not r.enabled])
        }
    
    def create_default_rules(self) -> List[Rule]:
        """Create a set of default rules"""
        default_rules = []
        
        # Rule 1: High priority for short videos
        rule1 = Rule(
            id="short_video_priority",
            name="High Priority for Short Videos",
            description="Set high priority for videos under 5 minutes",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.DURATION,
                    operator=ComparisonOperator.LESS_THAN,
                    value=300  # 5 minutes in seconds
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.SET_PRIORITY,
                    parameters={'priority': 'high'}
                )
            ]
        )
        default_rules.append(rule1)
        
        # Rule 2: Audio extraction for music channels
        rule2 = Rule(
            id="music_audio_extract",
            name="Extract Audio from Music Channels",
            description="Automatically extract audio from known music channels",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.UPLOADER,
                    operator=ComparisonOperator.MATCHES,
                    value=r".*music.*|.*audio.*|.*sound.*",
                    case_sensitive=False
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.EXTRACT_AUDIO,
                    parameters={'format': 'mp3'}
                )
            ]
        )
        default_rules.append(rule2)
        
        # Rule 3: Rate limiting during peak hours
        rule3 = Rule(
            id="peak_hours_rate_limit",
            name="Rate Limit During Peak Hours",
            description="Apply rate limiting during peak internet hours (6-10 PM)",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.TIME_OF_DAY,
                    operator=ComparisonOperator.IN_RANGE,
                    value=[18, 22]  # 6 PM to 10 PM
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.RATE_LIMIT,
                    parameters={'rate_limit': '500K'}
                )
            ]
        )
        default_rules.append(rule3)
        
        # Rule 4: Auto-organize by uploader
        rule4 = Rule(
            id="organize_by_uploader",
            name="Organize Downloads by Uploader",
            description="Automatically organize downloads into uploader folders",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.UPLOADER,
                    operator=ComparisonOperator.NOT_EQUALS,
                    value=""
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.AUTO_ORGANIZE,
                    parameters={'pattern': '{uploader}/{title}'}
                )
            ]
        )
        default_rules.append(rule4)
        
        # Rule 5: Block large files when queue is full
        rule5 = Rule(
            id="block_large_files_full_queue",
            name="Block Large Files When Queue Full",
            description="Block downloads over 1GB when queue has more than 10 items",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.FILE_SIZE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=1073741824  # 1GB in bytes
                ),
                RuleCondition(
                    condition_type=RuleConditionType.QUEUE_SIZE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=10
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.BLOCK_DOWNLOAD,
                    parameters={'reason': 'File too large and queue is full'}
                ),
                RuleAction(
                    action_type=RuleActionType.NOTIFY,
                    parameters={
                        'message': 'Large file blocked due to full queue',
                        'severity': 'warning'
                    }
                )
            ]
        )
        default_rules.append(rule5)
        
        return default_rules

# Factory function
def create_rules_engine(rules_file: Optional[str] = None) -> SmartRulesEngine:
    """Create and initialize a rules engine"""
    engine = SmartRulesEngine(rules_file)
    
    # Try to load existing rules
    if not engine.load_rules():
        # If no rules exist, create defaults
        default_rules = engine.create_default_rules()
        for rule in default_rules:
            engine.add_rule(rule)
        engine.save_rules()
    
    return engine
