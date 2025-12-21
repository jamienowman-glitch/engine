"""Editor History Engine (Undo/Redo)."""
from __future__ import annotations

import abc
from typing import List, Optional

class Command(abc.ABC):
    """Abstract base class for editor commands."""
    
    @abc.abstractmethod
    def execute(self) -> bool:
        """Executes the command. Returns True if successful."""
        pass
        
    @abc.abstractmethod
    def undo(self):
        """Reverts the command."""
        pass
        
    def redo(self):
        """Redoes the command (default execution)."""
        self.execute()


class HistoryStack:
    """Manages undo/redo stacks."""
    
    def __init__(self, max_depth: int = 50):
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_depth = max_depth
        
    def push_and_execute(self, cmd: Command) -> bool:
        """Executes a command and pushes it to history."""
        if cmd.execute():
            self.undo_stack.append(cmd)
            self.redo_stack.clear() # Clear redo on new action
            
            if len(self.undo_stack) > self.max_depth:
                self.undo_stack.pop(0) # Remove oldest
            return True
        return False
        
    def undo(self) -> bool:
        if not self.undo_stack:
            return False
            
        cmd = self.undo_stack.pop()
        cmd.undo()
        self.redo_stack.append(cmd)
        return True
        
    def redo(self) -> bool:
        if not self.redo_stack:
            return False
            
        cmd = self.redo_stack.pop()
        cmd.redo()
        self.undo_stack.append(cmd)
        return True
