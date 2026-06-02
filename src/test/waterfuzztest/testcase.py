
class TestCase:
    
    def __init__(self, mechanic=None, object_blocks=None, object_mobs=None,
                 environment=None, action_sequence=None):
        self.x = 0
        self.y = 70
        self.z = 0 
        self.mechanic = mechanic if mechanic else "the water gravity related violation of physics rule"
        if object_blocks:
            self.object_blocks = object_blocks
        else:
            self.object_blocks = [
                ("water", "block_water_1", (self.x+1,self.y,self.z)), 
                ("water", "block_water_2", (self.x+6,self.y,self.z))
            ]

        if object_mobs:
            self.object_mobs = object_mobs
        else:
            self.object_mobs = []

        if environment:
            self.environment = environment
        else:
            self.environment = []

        if action_sequence:
            self.action_sequence = action_sequence
        else:
            self.action_sequence = [] # dimension 1 means stimulation time, dimension 3 if it exists means the index of object_blocks/object_mobs/environment. 



