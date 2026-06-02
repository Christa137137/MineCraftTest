
class TestCase:
    
    def __init__(self, x=632, y=120, z=-393, object_blocks=None, object_mobs=None,
                 environment=None, action_sequence=None):
        self.x = x
        self.y = y
        self.z = z
        self.pos = [x, y, z]
        self.mechanic = "the water gravity related violation of physics rule"
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
            self.object_mobs = [
                ("villager", "mob_villager_1",(self.x+4,self.y+2,self.z))
            ]

        if environment:
            self.environment = environment
        else:
            self.environment = [
                ("glass", (self.x,self.y-1,self.z-1), (self.x+7,self.y,self.z+1)),
                ("air", (self.x+1,self.y,self.z), (self.x+6,self.y,self.z))
            ]

        if action_sequence:
            self.action_sequence = action_sequence
        else:
            self.action_sequence = [
                (0, "env_blocks", 0),  
                (0, "env_blocks", 1),  
                (0, "obj_block", 0), 
                (0, "obj_block", 1),                    
                (2, "obj_mob", 0),
                (4, "sleep_get_state")
            ] # dimension 1 means stimulation time



