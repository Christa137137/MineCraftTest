from pathlib import Path
import sys
path_base = Path(__file__).resolve()
while path_base.name != "MineCraftTest":
    path_base = path_base.parent
sys.path.append(str(path_base))

import os
import json
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import log_message

OBJECT_DATA = {
    "penetrable_media": [
        "honey_block", "slime_block", "cobweb", "oak_leaves", 
        "powder_snow", "mud", "scaffolding", "sweet_berry_bush", 
        "sugar_cane", "bamboo", "vine", "kelp"
    ],
    "medium_blocks": ["water", "lava", "soul_sand", "magma_block"],
    "projectiles": ["arrow", "trident", "snowball", "egg", "ender_pearl"]
}

class TestGeneration():

    def __init__(self, output_path=None, initial_seed_num=1, max_workers=10):
        self.output_path = output_path
        self.initial_seed_num = initial_seed_num
        self.max_workers = max_workers
        self.generic_mechanic = "Projectiles must follow basic ballistic physics. 1. Gravity causes projectiles to follow a parabolic trajectory in air. 2. Dense fluids like water or lava introduce massive hydrodynamic drag, rapidly decelerating the projectile. 3. Projectiles should stop or shatter upon hitting solid blocks. 4. Aerodynamic drafts can alter trajectories."
        self.testgeneration()

    def generate_single_seed(self, index):
        try:
            projectile = random.choice(OBJECT_DATA["projectiles"])
            intervention_medium = random.choice(OBJECT_DATA["penetrable_media"] + OBJECT_DATA["medium_blocks"])
            
            profile = random.choice(["horizontal", "mortar", "vertical_up", "vertical_down"])
            
            sx, sy, sz = 0, 75, 0
            
            vx, vy, vz = 0.0, 0.0, 0.0
            env_p1, env_p2 = [0, 0, 0], [0, 0, 0]
            
            if profile == "horizontal":
                vx = round(random.uniform(1.5, 3.0) * random.choice([1, -1]), 2)
                vy = round(random.uniform(-0.5, 0.5), 2)
                dx_start = 2 if vx > 0 else -2
                dx_end = 8 if vx > 0 else -8
                env_p1 = [sx + min(dx_start, dx_end), sy - 5, sz - 5]
                env_p2 = [sx + max(dx_start, dx_end), sy + 5, sz + 5]
                
            elif profile == "mortar":
                vx = round(random.uniform(1.0, 3.0) * random.choice([1, -1]), 2)
                vy = round(random.uniform(1.0, 3.0), 2)
                dx_start = 3 if vx > 0 else -3
                dx_end = 7 if vx > 0 else -7
                env_p1 = [sx + min(dx_start, dx_end), sy, sz - 4]
                env_p2 = [sx + max(dx_start, dx_end), sy + 8, sz + 4]
                
            elif profile == "vertical_up":
                vx = round(random.uniform(-0.5, 0.5), 2)
                vy = round(random.uniform(1.5, 3.0), 2)
                env_p1 = [sx - 4, sy + 3, sz - 4]
                env_p2 = [sx + 4, sy + 10, sz + 4]
                
            elif profile == "vertical_down":
                vx = round(random.uniform(-0.5, 0.5), 2)
                vy = round(random.uniform(-3.0, -1.5), 2)
                env_p1 = [sx - 4, sy - 10, sz - 4]
                env_p2 = [sx + 4, sy - 2, sz + 4]

            json_data = {
                "mechanic": self.generic_mechanic,
                "object_blocks": [],
                "object_mobs": [
                    [projectile, "baseline", [sx, sy, sz]],
                    [projectile, "intervention", [sx, sy, sz]]
                ],
                "environment": [
                    ["air", env_p1, env_p2],
                    ["air", env_p1, env_p2],
                    [intervention_medium, env_p1, env_p2]
                ],
                "action_sequence": [
                    [0, "environment", 0, None],
                    [3, "projectile", 0, [vx, vy, vz]],
                    [5, "environment", 1, None],
                    [5, "environment", 2, None],
                    [8, "projectile", 1, [vx, vy, vz]],
                    [10, "sleep_till", None, None]
                ]
            }
    
            rand_id = random.randint(1000, 9999)
            timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
            file_name = f"seed_{timestamp}_{index}_{rand_id}.json"
            
            save_path = os.path.join(self.output_path, file_name)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            
            return f"[Generation] Success: {file_name}"
        except Exception as e:
            return f"[Generation] Thread-{index} Failed: {str(e)}"

    def testgeneration(self):
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.generate_single_seed, i) 
                for i in range(self.initial_seed_num)
            ]
            
            for future in as_completed(futures):
                res = future.result()
                results.append(res)
                log_message(res)
        
        return results

if __name__ == "__main__":
    TestGeneration(output_path="outputs/testcase", initial_seed_num=3, max_workers=10)