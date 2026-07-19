#!/usr/bin/env python3
"""
Pipeline Executor — Wire UI commands to flow tools
Streams output to WebSocket for live terminal display
"""
import subprocess
import json
import os
from datetime import datetime

class PipelineExecutor:
    def __init__(self, websocket_broadcaster):
        self.ws = websocket_broadcaster
        self.current_file = None
        
    def execute(self, command: str, params: dict = None):
        """Route commands to actual flow tools"""
        params = params or {}
        
        if command == "FORGE":
            return self._run_forge()
        elif command == "SPLIT":
            return self._run_split()
        elif command == "SORT":
            return self._run_sort()
        elif command == "INTEGRATE":
            return self._run_integrate()
        elif command == "BUILD":
            return self._run_build()
        else:
            return {"ok": False, "error": f"Unknown pipeline command: {command}"}
    
    def _run_tool(self, tool_name: str, script: str, args: list = None):
        """Execute a flow tool and stream output"""
        args = args or []
        self._broadcast_terminal(f"⚡ Executing {tool_name}...")
        
        try:
            result = subprocess.run(
                ["python3", script] + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Stream stdout to terminal
            for line in result.stdout.split('\n'):
                if line.strip():
                    self._broadcast_terminal(line)
            
            # Stream stderr if present
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip():
                        self._broadcast_terminal(f"⚠️  {line}", error=True)
            
            success = result.returncode == 0
            self._broadcast_terminal(
                f"✅ {tool_name} completed" if success else f"❌ {tool_name} failed",
                error=not success
            )
            
            return {"ok": success, "output": result.stdout, "errors": result.stderr}
            
        except subprocess.TimeoutExpired:
            self._broadcast_terminal(f"⏱️  {tool_name} timed out", error=True)
            return {"ok": False, "error": "Timeout"}
        except Exception as e:
            self._broadcast_terminal(f"💥 {tool_name} crashed: {e}", error=True)
            return {"ok": False, "error": str(e)}
    
    def _run_forge(self):
        """Run flow_lock.py - the forge that locks logic"""
        return self._run_tool("FORGE (flow_lock)", "flow_lock.py")
    
    def _run_split(self):
        """Run flow_split.py - split code into chunks"""
        return self._run_tool("SPLIT (flow_split)", "flow_split.py")
    
    def _run_sort(self):
        """Run flow_sort.py - sort and organize"""
        return self._run_tool("SORT (flow_sort)", "flow_sort.py")
    
    def _run_integrate(self):
        """Run flow_integrate.py - merge components"""
        return self._run_tool("INTEGRATE (flow_integrate)", "flow_integrate.py")
    
    def _run_build(self):
        """Run final build step"""
        self._broadcast_terminal("🔨 BUILD: Compiling final artifact...")
        # Add your build logic here
        return {"ok": True, "message": "Build system ready"}
    
    def _broadcast_terminal(self, message: str, error: bool = False):
        """Send terminal output to Room 3 via WebSocket"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg_type = "error" if error else "info"
        
        payload = {
            "type": "terminal",
            "timestamp": timestamp,
            "message": message,
            "level": msg_type
        }
        
        # Broadcast to Room 3 (PassPatrol)
        if self.ws:
            try:
                self.ws.broadcast("room_3", message)
            except Exception as e:
                print(f"⚠️  Broadcast to room_3 failed: {e}")
