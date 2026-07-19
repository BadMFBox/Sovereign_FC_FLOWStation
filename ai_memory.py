"""
AI Memory Bank — Sovereign AI Notes System
Persistent memory that survives sessions, wiped working memory on logout
"""

import json
import os
from datetime import datetime
from pathlib import Path

class AIMemory:
    def __init__(self, room="room-4"):
        self.room = room
        self.notes_dir = Path("forge/ai_notes")
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.notes_file = self.notes_dir / f"{room}_notes.json"
        self.working_memory = []
        self.persistent_notes = self._load_notes()
    
    def _load_notes(self):
        """Load persistent notes from disk"""
        if self.notes_file.exists():
            with open(self.notes_file, 'r') as f:
                data = json.load(f)
                return data.get('notes', [])
        return []
    
    def _save_notes(self):
        """Save persistent notes to disk"""
        data = {
            "project": "Sovereign_FC_FLOWStation",
            "room": self.room,
            "last_updated": datetime.now().isoformat(),
            "notes": self.persistent_notes
        }
        with open(self.notes_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_note(self, content, note_type="observation", persistent=True):
        """Add a note to memory"""
        note = {
            "timestamp": datetime.now().isoformat(),
            "type": note_type,
            "content": content
        }
        
        if persistent:
            self.persistent_notes.append(note)
            self._save_notes()
        else:
            self.working_memory.append(note)
        
        return note
    
    def get_notes(self, note_type=None, persistent_only=False):
        """Retrieve notes, optionally filtered by type"""
        notes = self.persistent_notes.copy()
        
        if not persistent_only:
            notes.extend(self.working_memory)
        
        if note_type:
            notes = [n for n in notes if n['type'] == note_type]
        
        return notes
    
    def wipe_working_memory(self):
        """Clear working memory (on logout)"""
        count = len(self.working_memory)
        self.working_memory = []
        return count
    
    def get_context_summary(self):
        """Get a summary of current context"""
        return {
            "persistent_notes": len(self.persistent_notes),
            "working_memory": len(self.working_memory),
            "last_updated": self.persistent_notes[-1]['timestamp'] if self.persistent_notes else None
        }

# Global AI memory instance
ai_memory = AIMemory()

# Import mock AI
from ai_brain_mock import ai_brain

def ai_chat_with_8cv(message, room, engine=None, optimizer=None):
    """AI chat enhanced with 8CV awareness - uses mock brain for now"""
    
    # Get 8CV context
    context_8cv = get_8cv_context(engine) if engine else {}
    
    # Get recent history
    history = engine.get_health_history()[-10:] if engine else []
    history_cycles = [
        {
            'gear': h.gear.name if hasattr(h, 'gear') else 'UNKNOWN',
            'health': h.health_score,
            'cycle': h.cycle_id[:16]
        }
        for h in history
    ]
    
    # Use mock AI brain
    result = ai_brain.chat(message, context_8cv=context_8cv, room=room)
    
    # Also check for proactive patterns
    if not result.get('suggestion'):
        patterns = ai_brain.detect_patterns(context_8cv, history_cycles)
        if patterns:
            result['suggestion'] = patterns[0]  # Top priority
    
    return result
