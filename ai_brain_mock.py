"""
Mock AI Brain - Pattern-based responses for K9 Soldier
This works WITHOUT an LLM by using rule-based pattern detection
"""

import time
import json

class MockAIBrain:
    def __init__(self):
        self.conversation_history = []
        self.patterns_detected = []
    
    def chat(self, message, context_8cv=None, room='room-4'):
        """Generate response based on patterns, not LLM"""
        message_lower = message.lower()
        response = None
        suggestion = None
        
        # Pattern: 8CV status inquiry
        if any(word in message_lower for word in ['8cv', 'status', 'health', 'engine']):
            if context_8cv:
                gear = context_8cv.get('gear', 'UNKNOWN')
                cycle = context_8cv.get('cycle', 0)
                health = context_8cv.get('health', 0)
                
                if health < 30:
                    response = f"⚠️ ALERT: 8CV health critical at {health}/50. Gear: {gear}, Cycle: {cycle}. Top: {context_8cv.get('top_loop', '?')}, Bottom: {context_8cv.get('bottom_loop', '?')}. Recommend immediate inspection."
                elif gear == 'GEAR_3_UNDISPUTED':
                    response = f"🔥 System in Gear 3 (UNDISPUTED) at cycle {cycle}. Health: {health}/50. High alert mode. This gear is for extreme load only."
                    if cycle > 50 and health == 50:
                        suggestion = {
                            'priority': 'HIGH',
                            'type': 'gear_optimization',
                            'title': 'Consider downshifting from Gear 3',
                            'content': f'System stable at {health}/50 for {cycle} cycles in UNDISPUTED mode. This may be over-reactive. Suggest shifting to Gear 2.',
                            'action': 'shift_gear',
                            'params': {'target': 'GEAR_2_ACTIVE', 'reason': 'AI pattern: prolonged Gear 3 with perfect health'}
                        }
                else:
                    response = f"✓ 8CV running smoothly. Gear: {gear}, Cycle: {cycle}, Health: {health}/50."
            else:
                response = "8CV context not available. Ensure the engine is running."
        
        # Pattern: Buzzkill questions
        elif 'buzzkill' in message_lower:
            response = """Buzzkill is the 8CV safety mechanism with three tiers:

• **T1 Surgical**: Minor anomaly detected. Targeted response, specific room affected.
• **T2 Scorched**: Partial loop failure (top OR bottom). Multiple rooms regenerate keys.
• **T3 Live Burn**: Critical breach. All rooms destroyed, full system reset.

If you're seeing repeated buzzkills, check R3 (PassPatrol) crossover integrity."""
        
        # Pattern: Crossover / R3 questions
        elif any(word in message_lower for word in ['crossover', 'r3', 'passpatrol']):
            response = """R3 (PassPatrol) is the crossover node where top and bottom 8CV loops meet. It's the shared point in the figure-8 topology.

**Why it matters:**
• R3 output from bottom loop MUST match its input to top loop
• If crossover validation fails, it indicates timing stress or key derivation corruption
• This is the most critical room because both loops depend on it

**Troubleshooting crossover failures:**
1. Check R3 logic lock status
2. Verify R3 hasn't been modified recently
3. Run crossover validation test
4. Check system load (may be timing-related)"""
        
        # Pattern: Gear shift requests
        elif 'gear' in message_lower and any(word in message_lower for word in ['shift', 'change', 'switch', 'move']):
            if context_8cv:
                current_gear = context_8cv.get('gear', 'UNKNOWN')
                response = f"Current gear: {current_gear}. Which gear do you want? (GEAR_1_STANDBY, GEAR_2_ACTIVE, GEAR_3_UNDISPUTED)"
                suggestion = {
                    'priority': 'INFO',
                    'type': 'gear_shift_request',
                    'title': 'Manual gear shift',
                    'content': 'User requesting gear change. Specify target gear and reason.',
                    'action': 'shift_gear',
                    'params': {'target': 'GEAR_2_ACTIVE', 'reason': 'User request'}
                }
            else:
                response = "Cannot shift gear without 8CV context."
        
        # Pattern: Help / capabilities
        elif any(word in message_lower for word in ['help', 'what can', 'capabilities', 'how to']):
            response = """I'm your K9 soldier AI. I can:

• 👁️ Monitor 8CV engine in real-time
• 🔍 Detect patterns (repeated buzzkills, health anomalies)
• 💡 Suggest proactive fixes (gear shifts, room inspections)
• 📝 Remember context across sessions
• 🔒 Respect logic locks (I can't modify locked code)
• ⚡ Observe terminal activity and suggest improvements

All my actions require your approval. I serve, I don't command.

**Ask me about:**
• 8CV status, health, gears
• Buzzkill tiers and troubleshooting
• Crossover validation (R3)
• Room-specific issues"""
        
        # Pattern: Room-specific questions
        elif any(f'room {i}' in message_lower or f'r{i}' in message_lower for i in range(5)):
            room_names = {
                0: "SovereignFuel (R0) - Token Generator",
                1: "LogicLock (R1) - Code Protection",
                2: "FileCenter (R2) - Data Management", 
                3: "PassPatrol (R3) - Crossover Node",
                4: "FlowControl (R4) - Execution Terminal"
            }
            
            for i, name in room_names.items():
                if f'room {i}' in message_lower or f'r{i}' in message_lower:
                    response = f"**{name}**\n\n"
                    if i == 3:
                        response += "Critical room! R3 is the crossover point where top and bottom 8CV loops meet. Changes here affect the entire system."
                    elif i == 0:
                        response += "Token generator and encryption root. If R0 is compromised, all downstream rooms fail."
                    elif i == 1:
                        response += "Code protection layer. Locked modules cannot be edited without unlocking first."
                    elif i == 2:
                        response += "File management and storage. Changes here affect data persistence."
                    elif i == 4:
                        response += "Execution terminal. This is where commands run and code executes."
                    break
        
        # Default: Generic helpful response
        else:
            if context_8cv:
                response = f"I'm analyzing your message. Current 8CV state: Gear {context_8cv.get('gear', '?')}, Cycle {context_8cv.get('cycle', 0)}, Health {context_8cv.get('health', 0)}/50. How can I help?"
            else:
                response = "I'm your K9 soldier AI. Ask me about 8CV status, buzzkills, rooms, or say 'help' for capabilities."
        
        # Log conversation
        self.conversation_history.append({
            'ts': time.time(),
            'message': message,
            'response': response,
            'room': room
        })
        
        return {
            'response': response,
            'suggestion': suggestion,
            'context': context_8cv,
            'note': None
        }
    
    def detect_patterns(self, context_8cv, history_cycles):
        """Analyze 8CV state and detect patterns proactively"""
        suggestions = []
        
        if not context_8cv:
            return suggestions
        
        gear = context_8cv.get('gear', '')
        health = context_8cv.get('health', 0)
        cycle = context_8cv.get('cycle', 0)
        
        # Pattern 1: Stuck in Gear 3 with perfect health
        if gear == 'GEAR_3_UNDISPUTED' and health == 50 and cycle > 50:
            suggestions.append({
                'priority': 'HIGH',
                'type': 'gear_optimization',
                'title': 'System stuck in Gear 3',
                'content': f'Been in UNDISPUTED mode for {cycle} cycles with perfect health. This is unusual. Consider downshifting to Gear 2.',
                'action': 'shift_gear',
                'params': {'target': 'GEAR_2_ACTIVE', 'reason': 'AI pattern: prolonged Gear 3'}
            })
        
        # Pattern 2: Health degrading
        if 15 <= health < 30:
            suggestions.append({
                'priority': 'CRITICAL',
                'type': 'health_degradation',
                'title': 'Health approaching critical',
                'content': f'Current health: {health}/50. Buzzkill T2 may trigger soon. Check loop status.',
                'action': 'inspect_loops',
                'params': {}
            })
        
        # Pattern 3: Repeated gear shifts (from history)
        if history_cycles and len(history_cycles) >= 5:
            gears = [c.get('gear', '') for c in history_cycles[-5:]]
            if len(set(gears)) >= 4:  # Gear changed 4+ times in last 5 cycles
                suggestions.append({
                    'priority': 'WARNING',
                    'type': 'instability',
                    'title': 'Frequent gear shifts detected',
                    'content': 'System shifting gears frequently. This indicates load instability or over-reactive Commander.',
                    'action': 'analyze_load',
                    'params': {}
                })
        
        return suggestions

# Global instance
ai_brain = MockAIBrain()
