import os
import json
import random
from datetime import datetime

OBJECT_DATA = {
    "light_sources": [
        "glowstone", "sea_lantern", "shroomlight", "ochre_froglight",
        "pearlescent_froglight", "verdant_froglight", "lantern",
        "jack_o_lantern", "torch", "end_rod", "beacon", "crying_obsidian"
    ],
    "media": [
        "water", "soul_sand", "magma_block", "lava", "powder_snow",
        "glass", "tinted_glass", "white_stained_glass", "black_stained_glass",
        "slime_block", "honey_block", "oak_leaves", "spruce_leaves",
        "jungle_leaves", "azalea_leaves", "ice", "packed_ice", "blue_ice",
        "scaffolding", "iron_bars", "glass_pane", "oak_slab", "oak_stairs",
        "cobweb", "cherry_leaves"
    ]
}

class TestGeneration:
    def __init__(self, output_path, batch_size=20):
        self.output_path = output_path
        self.batch_size = batch_size
        os.makedirs(self.output_path, exist_ok=True)
        
        self.generic_mechanic = "Random Baseline: Compare light attenuation between standard air and an injected random medium inside a completely sealed darkroom."
        
        self.generate_batch()

    def generate_random_seed(self):
        width = random.randint(8, 15)
        height = random.randint(4, 7)
        depth = random.randint(8, 15)
        base_y = 70
        
        environment = []
        object_blocks = []
        action_sequence = []
        
        environment.append(["black_concrete", [-1, base_y - 1, -1], [width + 1, base_y + height, depth + 1]])
        
        environment.append(["air", [0, base_y, 0], [width, base_y + height - 1, depth]])
        
        med_x1 = random.randint(2, width - 3)
        med_x2 = med_x1 + random.randint(0, 2)
        medium = random.choice(OBJECT_DATA["media"])
        
        is_x_wall = random.choice([True, False])
        if is_x_wall:
            environment.append([medium, [med_x1, base_y, 0], [med_x2, base_y + height - 1, depth]])
        else:
            med_z1 = random.randint(2, depth - 3)
            med_z2 = med_z1 + random.randint(0, 2)
            environment.append([medium, [0, base_y, med_z1], [width, base_y + height - 1, med_z2]])

        num_sources = random.randint(1, 2)
        for i in range(num_sources):
            ls = random.choice(OBJECT_DATA["light_sources"])
            sy = random.randint(base_y, base_y + height - 1)
            
            if is_x_wall:
                sz = random.randint(0, depth)
                object_blocks.append([ls, f"source_{i}", [0, sy, sz], [0, sy, sz]])
            else:
                sx = random.randint(0, width)
                object_blocks.append([ls, f"source_{i}", [sx, sy, 0], [sx, sy, 0]])

        action_sequence.append([0, "environment", 0, None])
        action_sequence.append([0, "environment", 1, None])
        
        for i in range(len(object_blocks)):
            action_sequence.append([0, "object_blocks", i, None])

        if is_x_wall:
            measure_p1 = [width, base_y + 1, 0]
            measure_p2 = [width, base_y + 1, depth]
        else:
            measure_p1 = [0, base_y + 1, depth]
            measure_p2 = [width, base_y + 1, depth]

        action_sequence.append([1, "get_light_level", None, measure_p1, measure_p2])
        action_sequence.append([1, "environment", 2, None])
        action_sequence.append([6, "get_light_level", None, measure_p1, measure_p2])
        action_sequence.append([7, "sleep_till", None, None])

        seed_data = {
            "mechanic": self.generic_mechanic,
            "object_blocks": object_blocks,
            "object_mobs": [],
            "environment": environment,
            "action_sequence": sorted(action_sequence, key=lambda x: x[0])
        }
        
        return seed_data

    def generate_batch(self):
        for i in range(self.batch_size):
            seed_data = self.generate_random_seed()
            timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
            rand_id = random.randint(1000, 9999)
            file_name = f"seed_{timestamp}_{i}_{rand_id}.json"
            
            file_path = os.path.join(self.output_path, file_name)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(seed_data, f, indent=4, ensure_ascii=False)
                
        print(f"[Generation] Successfully generated {self.batch_size} random baseline files.")

if __name__ == "__main__":
    TestGeneration(output_path="./outputs/testcase", batch_size=20)