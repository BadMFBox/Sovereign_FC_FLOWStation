# What an agent file looks like
# WITHOUT Logic Lock:

# agents/room_2_agent.py
class Room2Agent:
    def run(self):
        # Agent can see everything
        # Agent can call anything
        # Agent can modify anything
        # Agent can send data anywhere
        import room_2.core.process    # ← FULL ACCESS
        import room_2.core.RoomEngine # ← FULL ACCESS
        # This is the hook vector
        # This is how logic gets stolen

# ─────────────────────────────────────────

# What an agent file looks like
# WITH Logic Lock:

# agents/room_2_agent.py
class Room2Agent:
    def run(self):
        # Agent gets a SURFACE only
        # The surface is what YOU defined
        # Everything below is locked
        from mesh.room_2 import get_surface
        surface = get_surface()
        # surface = {
        #   "validate": <locked_ref>,
        #   "process":  <locked_ref>,
        # }
        # Agent calls surface.validate()
        # Agent NEVER sees the logic inside
        # Agent CANNOT hook into it
        # Agent CANNOT modify it
        # Lock signature verified on every call
