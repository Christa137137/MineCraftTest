import os
import json
import random
import uuid

OBJECT_DATA = {
    "gravity_blocks": ["anvil", "sand", "red_sand", "gravel", "pointed_dripstone", "dragon_egg", "suspicious_sand", "suspicious_gravel", "scaffolding"],
    "fluid_blocks": ["sponge", "wet_sponge", "magma_block", "soul_sand", "scaffolding", "powder_snow"],
    "mechanical_entities": ["oak_boat", "spruce_boat", "mangrove_boat", "minecart", "tnt_minecart", "chest_minecart", "hopper_minecart"],
    "swimming_mobs": ["dolphin", "glow_squid", "squid", "salmon", "cod", "pufferfish", "tropical_fish", "axolotl", "turtle", "drowned", "guardian", "elder_guardian", "frog", "tadpole"],
    "non_swimming_mobs": ["iron_golem", "villager", "piglin", "hoglin", "zoglin", "zombie", "skeleton", "creeper", "witch", "pillager", "ravager", "cow", "pig", "sheep", "chicken", "rabbit", "wolf", "cat", "panda", "polar_bear", "enderman"]
}

class TestGeneration:
    def __init__(self, output_path, batch_size=20):
        self.output_path = output_path
        self.batch_size = batch_size
        os.makedirs(self.output_path, exist_ok=True)
        
        self.generic_mechanic = "Objects must follow basic water physics. 1. Heavy objects sink. 2. Light/partial medium objects float in still water. 3. ALL objects must fall downward in a waterfall."
        
        self.generate_batch()

    def generate_random_seed(self):

        width = random.randint(5, 10)
        height = random.randint(6, 10)
        depth = random.randint(5, 10)
        
        base_y = 70
        top_y = base_y + height
        
        # 50% capped, 50% open-top
        has_lid = random.choice([True, False])
        hollow_top = top_y - 1 if has_lid else top_y
        
        environment = []
        action_sequence = []
        
        # build the env
        environment.append(["glass", [0, base_y, 0], [width, top_y, depth]])
        environment.append(["air", [1, base_y + 1, 1], [width - 1, hollow_top, depth - 1]])
        
        # 50% with holes
        if random.random() < 0.5:
            num_holes = random.randint(1, 3)
            for _ in range(num_holes):
                # decide the hole position, can be on the floor or on the wall
                side = random.choice(["floor", "wall_x", "wall_z"])
                if side == "floor":
                    hx, hy, hz = random.randint(1, width-1), base_y, random.randint(1, depth-1)
                elif side == "wall_x":
                    hx, hy, hz = random.choice([0, width]), random.randint(base_y+1, hollow_top), random.randint(1, depth-1)
                else: # wall_z
                    hx, hy, hz = random.randint(1, width-1), random.randint(base_y+1, hollow_top), random.choice([0, depth])
                environment.append(["air", [hx, hy, hz], [hx, hy, hz]])

        # 50% set special interactive blocks
        if random.random() < 0.5:
            num_special = random.randint(1, 2)
            for _ in range(num_special):
                special_block = random.choice(OBJECT_DATA["fluid_blocks"])
                sx = random.randint(1, width - 1)
                sz = random.randint(1, depth - 1)
                environment.append([special_block, [sx, base_y, sz], [sx, base_y, sz]])

        # 50% generate obstacles
        if random.random() < 0.5:
            num_obstacles = random.randint(1, 2)
            for _ in range(num_obstacles):
                # random generate a vertical or horizontal glass obstacle
                if random.choice(["vertical", "horizontal"]) == "vertical":
                    ox_obs = random.randint(1, width - 1)
                    oz_obs = random.randint(1, depth - 1)
                    environment.append(["glass", [ox_obs, base_y + 1, oz_obs], [ox_obs, hollow_top, oz_obs]])
                else:
                    hy = random.randint(base_y + 1, hollow_top)
                    if random.choice([True, False]): # x coordinate
                        oz_obs = random.randint(1, depth - 1)
                        environment.append(["glass", [1, hy, oz_obs], [width - 1, hy, oz_obs]])
                    else: # z coordinate
                        ox_obs = random.randint(1, width - 1)
                        environment.append(["glass", [ox_obs, hy, 1], [ox_obs, hy, depth - 1]])

        # water block gen
        num_water = random.randint(1, 5)
        for _ in range(num_water):
            wx = random.randint(1, width - 1)
            wy = random.randint(base_y + 1, hollow_top)
            wz = random.randint(1, depth - 1)
            environment.append(["water", [wx, wy, wz], [wx, wy, wz]])




        object_blocks = []
        object_mobs = []
        num_objects = random.randint(1, 2)
        
        for i in range(num_objects):
            category_keys = list(OBJECT_DATA.keys())
            chosen_category = random.choice(category_keys)
            chosen_id = random.choice(OBJECT_DATA[chosen_category])
            
            # reserve at least 2 blocks 
            ox = random.randint(2, width - 2)
            oz = random.randint(2, depth - 2)
            # reserve at least 2 blocks from the top to avoid suffocation, and at least 1 block from the base
            oy = random.randint(base_y + 1, hollow_top - 2)
            
            # 3x3x3 aire zone
            environment.append(["air", [ox - 1, oy, oz - 1], [ox + 1, oy + 2, oz + 1]])
            


            instance_name = f"rand_obj_{i}"
            
            if chosen_category in ["gravity_blocks", "fluid_blocks"]:
                object_blocks.append([chosen_id, instance_name, [ox, oy, oz], [ox, oy, oz]])
                action_sequence.append([5, "object_blocks", len(object_blocks) - 1, None])
            else:
                object_mobs.append([chosen_id, instance_name, [ox, oy, oz]])
                action_sequence.append([5, "object_mobs", len(object_mobs) - 1, None])

        for i in range(len(environment)):
            action_sequence.append([0, "environment", i, None])

        action_sequence.append([30, "sleep_till", None, None])
        

        seed_data = {
            "mechanic": self.generic_mechanic,
            "object_blocks": object_blocks,
            "object_mobs": object_mobs,
            "environment": environment,
            "action_sequence": sorted(action_sequence, key=lambda x: x[0])  # make sure the action sequence is sorted
        }
        
        return seed_data

    def generate_batch(self):
        import random
        from datetime import datetime

        for i in range(self.batch_size):
            seed_data = self.generate_random_seed()
            timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
            rand_id = random.randint(1000, 9999)
            index = i
            file_name = f"seed_{timestamp}_{index}_{rand_id}.json"
            
            file_path = os.path.join(self.output_path, file_name)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(seed_data, f, indent=4)
                
        print(f"[Generation] Successfully generated {self.batch_size} files")

if __name__ == "__main__":
    TestGeneration(output_path="./random_baseline_seeds", batch_size=20)