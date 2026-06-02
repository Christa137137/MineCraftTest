import os
import json
import random
import math
import copy
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import log_message

OBJECT_DATA = {
    "gravity_blocks": ["anvil", "sand", "red_sand", "gravel", "pointed_dripstone", "dragon_egg", "suspicious_sand", "suspicious_gravel", "scaffolding"],
    "fluid_blocks": ["sponge", "wet_sponge", "magma_block", "soul_sand", "scaffolding", "powder_snow"],
    "mechanical_entities": ["oak_boat", "spruce_boat", "mangrove_boat", "minecart", "tnt_minecart", "chest_minecart", "hopper_minecart"],
    "swimming_mobs": ["dolphin", "glow_squid", "squid", "salmon", "cod", "pufferfish", "tropical_fish", "axolotl", "turtle", "drowned", "guardian", "elder_guardian", "frog", "tadpole"],
    "non_swimming_mobs": ["iron_golem", "villager", "piglin", "hoglin", "zoglin", "zombie", "skeleton", "creeper", "witch", "pillager", "ravager", "cow", "pig", "sheep", "chicken", "rabbit", "wolf", "cat", "panda", "polar_bear", "enderman"]
}

class SeedMutation:
    def __init__(self, input_path=None, output_path=None, max_workers=10):
        self.input_path = input_path  
        self.output_path = output_path 
        self.max_workers = max_workers
        
        if self.output_path and not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            
        self.mutation()

    def mutate_single_file(self, file_name):
        file_path = os.path.join(self.input_path, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                seed_data = json.load(f)

            original_mechanic = seed_data.get("mechanic", "Unknown")

            fd = seed_data.get("fitness", {})
       
            s_val = fd.get("interaction_complexity", {}).get("fitness") or 0
            w_val = fd.get("fluid_fitness", {}).get("fitness") or 0
            o_val = fd.get("object_fitness", {}).get("fitness") or 0
            e_val = fd.get("environment_fitness", {}).get("fitness") or 0
            b_val = fd.get("buoyancy_inconsistency", {}).get("fitness") or 0
            
            total_fitness = (s_val + w_val + o_val + e_val) * 0.05 + (b_val * 0.8)
            energy = math.ceil(3 * total_fitness) if total_fitness > 0 else 1

            for _ in range(energy):
                try:
                    mutated_json = self.hardcode_random_mutate(seed_data)
                    mutated_json["mechanic"] = original_mechanic
                    
                    rand_id = random.randint(1000, 9999)
                    timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
                    output_file_path = os.path.join(self.output_path, f"mutation_{timestamp}_{rand_id}.json")
                    
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        json.dump(mutated_json, f, ensure_ascii=False, indent=4)
                except Exception as ex:
                    continue
                    
            return f"[Mutation] Success: {file_name} generated {energy} variants."
        except Exception as e:
            return f"[Mutation Error] {file_name}: {str(e)}"

    def _build_voxel_grid(self, data):
        voxel = {}
        env_list = data.get("environment", [])
        for env in env_list:
            try:
                mat = env[0]
                pos1 = env[1]
                pos2 = env[2] if len(env) > 2 else env[1]
                for x in range(min(pos1[0], pos2[0]), max(pos1[0], pos2[0]) + 1):
                    for y in range(min(pos1[1], pos2[1]), max(pos1[1], pos2[1]) + 1):
                        for z in range(min(pos1[2], pos2[2]), max(pos1[2], pos2[2]) + 1):
                            voxel[(x, y, z)] = mat
            except Exception:
                continue
        return voxel

    def hardcode_random_mutate(self, seed_data):
        mutated_data = copy.deepcopy(seed_data)
        
        min_x, max_x = -10, 10
        min_y, max_y = 60, 90
        min_z, max_z = -10, 10
        
        if mutated_data.get("environment"):
            all_x, all_y, all_z = [], [], []
            for env in mutated_data["environment"]:
                try:
                    pos1 = env[1]
                    pos2 = env[2] if len(env) > 2 else env[1]
                    all_x.extend([pos1[0], pos2[0]])
                    all_y.extend([pos1[1], pos2[1]])
                    all_z.extend([pos1[2], pos2[2]])
                except: continue
            if all_x: min_x, max_x = min(all_x), max(all_x)
            if all_y: min_y, max_y = min(all_y), max(all_y)
            if all_z: min_z, max_z = min(all_z), max(all_z)

        # 强制至少选一个算子
        num_ops = random.randint(1, 3)
        ops = [random.choice([1, 2, 3, 4]) for _ in range(num_ops)]

        for op in ops:
            if op == 1: 
                for obj_key in ["object_mobs", "object_blocks"]:
                    obj_list = mutated_data.get(obj_key, [])
                    for obj in obj_list:
                        if len(obj) > 0 and random.random() < 0.1:
                            for cat, items in OBJECT_DATA.items():
                                if obj[0] in items:
                                    obj[0] = random.choice(items)
                                    break

            elif op == 2: 
                voxel_grid = self._build_voxel_grid(mutated_data)
                for obj_key in ["object_mobs", "object_blocks"]:
                    obj_list = mutated_data.get(obj_key, [])
                    for obj in obj_list:
                        if random.random() < 0.3:
                            try:
                                if len(obj) >= 3 and isinstance(obj[2], list) and len(obj[2]) >= 3:
                                    ox, oy, oz = obj[2][0], obj[2][1], obj[2][2]
                                    safe_neighbors = []
                                    for dx in [-1, 0, 1]:
                                        for dy in [-1, 0, 1]:
                                            for dz in [-1, 0, 1]:
                                                if dx == 0 and dy == 0 and dz == 0: continue
                                                nx, ny, nz = ox + dx, oy + dy, oz + dz
                                                mat = voxel_grid.get((nx, ny, nz), "air")
                                                if mat in ["air", "water"]:
                                                    safe_neighbors.append((nx, ny, nz))
                                    if safe_neighbors:
                                        nx, ny, nz = random.choice(safe_neighbors)
                                        obj[2] = [nx, ny, nz]
                                        if len(obj) >= 4 and isinstance(obj[3], list): 
                                            obj[3] = [nx, ny, nz]
                            except: continue
                                
            elif op == 3: 
                env_list = mutated_data.get("environment", [])
                if env_list:
                    idx = random.randint(0, len(env_list) - 1)
                    env = env_list[idx]
                    current_mat = env[0]
                    if current_mat == "glass": env[0] = "air"
                    elif current_mat == "air": env[0] = random.choice(["water", "glass"])
                    elif current_mat == "water": env[0] = random.choice(["air", "soul_sand", "magma_block"])

            elif op == 4: 
                if max_x > min_x and max_y > min_y and max_z > min_z:
                    rx = random.randint(min_x+1, max_x-1)
                    ry = random.randint(min_y+1, max_y-1)
                    rz = random.randint(min_z+1, max_z-1)
                    mat = random.choice(["water", "air"])
                    new_env = [mat, [rx, ry, rz], [rx, ry, rz]]
                    mutated_data.setdefault("environment", []).append(new_env)
                    env_idx = len(mutated_data["environment"]) - 1
                    mutated_data.setdefault("action_sequence", []).append([0, "environment", env_idx, None])

        if mutated_data.get("action_sequence"):
            def safe_int(val):
                try: return int(val)
                except: return 999999
            mutated_data["action_sequence"] = sorted(mutated_data["action_sequence"], key=lambda x: safe_int(x[0]) if len(x) > 0 else 999999)
            
        return mutated_data

    def mutation(self):
        if not os.path.exists(self.input_path) or not os.listdir(self.input_path):
            return

        json_files = [f for f in os.listdir(self.input_path) if f.endswith('.json')]
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.mutate_single_file, f) for f in json_files]
            for future in as_completed(futures):
                log_message(future.result())

if __name__ == "__main__":
    SeedMutation(input_path="outputs/evaluated", output_path="outputs/mutated_seeds")