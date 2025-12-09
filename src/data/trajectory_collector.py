"""Trajectory collection for white agent actions."""

import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path


class TrajectoryCollector:
    """Collects trajectory of white agent actions."""
    
    def __init__(self, task_name: str):
        """
        Initialize trajectory collector.
        
        Args:
            task_name: Name of the task being evaluated
        """
        self.task_name = task_name
        self.actions: List[Dict[str, Any]] = []
        self.start_time = time.time()
    
    def add_action(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        timestamp: Optional[float] = None,
    ):
        """
        Add an action to the trajectory.
        
        Args:
            action_type: Type of action (e.g., "bash", "read_file", "write_file", "goto_url", "send_message")
            action_data: Action-specific data
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()
        
        action = {
            "type": action_type,
            "timestamp": timestamp,
            "data": action_data,
        }
        self.actions.append(action)
    
    def add_bash_command(self, command: str, output: Optional[str] = None):
        """Add a bash command to trajectory."""
        self.add_action("bash", {
            "command": command,
            "output": output,
        })
    
    def add_file_read(self, path: str, content: Optional[str] = None):
        """Add a file read action to trajectory."""
        self.add_action("read_file", {
            "path": path,
            "content": content,
        })
    
    def add_file_write(self, path: str, content: Optional[str] = None):
        """Add a file write action to trajectory."""
        self.add_action("write_file", {
            "path": path,
            "content": content,
        })
    
    def add_browser_navigation(self, url: str):
        """Add a browser navigation action to trajectory."""
        self.add_action("goto_url", {
            "url": url,
        })
    
    def add_message(self, recipient: str, content: str):
        """Add a message action to trajectory."""
        self.add_action("send_message", {
            "recipient": recipient,
            "content": content,
        })
    
    def save(self, output_path: str) -> str:
        """
        Save trajectory to JSON file.
        
        Args:
            output_path: Path to save trajectory file
        
        Returns:
            Path to saved file
        """
        trajectory = {
            "task_name": self.task_name,
            "start_time": self.start_time,
            "end_time": time.time(),
            "duration": time.time() - self.start_time,
            "actions": self.actions,
            "action_count": len(self.actions),
        }
        
        with open(output_path, 'w') as f:
            json.dump(trajectory, f, indent=2)
        
        return output_path
    
    def get_trajectory(self) -> Dict[str, Any]:
        """Get current trajectory as dictionary."""
        return {
            "task_name": self.task_name,
            "start_time": self.start_time,
            "end_time": time.time(),
            "duration": time.time() - self.start_time,
            "actions": self.actions,
            "action_count": len(self.actions),
        }


class A2ATrajectoryCollector(TrajectoryCollector):
    """
    Collects trajectory from A2A agent messages.
    
    This is a simplified collector that monitors A2A messages.
    In a full implementation, you'd need to parse agent responses
    to extract actual actions (bash commands, file operations, etc.).
    """
    
    def __init__(self, task_name: str):
        super().__init__(task_name)
        self.messages: List[Dict[str, Any]] = []
    
    def add_message(self, role: str, content: str, message_id: Optional[str] = None):
        """
        Add an A2A message to trajectory.
        
        Args:
            role: Message role ("user" or "agent")
            content: Message content
            message_id: Optional message ID
        """
        self.messages.append({
            "role": role,
            "content": content,
            "message_id": message_id,
            "timestamp": time.time(),
        })
        
        # Try to extract actions from agent messages
        if role == "agent":
            self._extract_actions_from_message(content)
    
    def _extract_actions_from_message(self, content: str):
        """
        Extract actions from agent message content.
        
        This is a simplified parser. In a real implementation,
        you'd need to parse the agent's response format to extract
        actual tool calls and actions.
        """
        # Placeholder: In real implementation, parse agent's tool calls
        # For now, we'll just record the message
        pass
    
    def save(self, output_path: str) -> str:
        """Save trajectory including A2A messages."""
        trajectory = self.get_trajectory()
        trajectory["messages"] = self.messages
        
        with open(output_path, 'w') as f:
            json.dump(trajectory, f, indent=2)
        
        return output_path

