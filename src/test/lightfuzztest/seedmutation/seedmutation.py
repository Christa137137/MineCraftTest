import os
import json
import random
import math
import copy
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import log_message

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
            m_val = fd.get("media_complexity", {}).get("fitness", 0)
            l_val = fd.get("light_source_fitness", {}).get("fitness", 0)
            e_val = fd.get("environment_fitness", {}).get("fitness", 0)
            i_val = fd.get("light_intensity_inconsistency", {}).get("fitness", 0)
            
            try:
                m_val = float(m_val)
                l_val = float(l_val)
                e_val = float(e_val)
                i_val = float(i_val)
            except:
                pass
            
            total_fitness = (m_val + l_val + e_val) * 0.05 + (i_val * 0.85)
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

    def hardcode_random_mutate(self, seed_data):
        mutated_data = copy.deepcopy(seed_data)
        
        min_x, max_x = -10, 10
        min_y, max_y = 60, 90
        min_z, max_z = -10, 10
        
        if mutated_data.get("environment"):
            all_x, all_y, all_z = [], [], []
            for env in mutated_data["environment"]:
                try:
                    if env[0] != "black_concrete":
                        pos1 = env[1]
                        pos2 = env[2] if len(env) > 2 else env[1]
                        all_x.extend([pos1[0], pos2[0]])
                        all_y.extend([pos1[1], pos2[1]])
                        all_z.extend([pos1[2], pos2[2]])
                except Exception:
                    continue
            if all_x: min_x, max_x = min(all_x), max(all_x)
            if all_y: min_y, max_y = min(all_y), max(all_y)
            if all_z: min_z, max_z = min(all_z), max(all_z)

        num_ops = random.randint(1, 2)
        ops = random.sample([1, 2, 3, 4], num_ops)

        for op in ops:
            if op == 1: 
                obj_list = mutated_data.get("object_blocks", [])
                for obj in obj_list:
                    if len(obj) > 0 and obj[0] in OBJECT_DATA["light_sources"] and random.random() < 0.5:
                        obj[0] = random.choice(OBJECT_DATA["light_sources"])

            elif op == 2: 
                env_list = mutated_data.get("environment", [])
                for env in env_list:
                    if len(env) > 0 and env[0] in OBJECT_DATA["media"] and random.random() < 0.4:
                        env[0] = random.choice(OBJECT_DATA["media"])

            elif op == 3: 
                env_list = mutated_data.get("environment", [])
                for env in env_list:
                    if len(env) > 2 and env[0] in OBJECT_DATA["media"] and random.random() < 0.3:
                        try:
                            axis = random.choice([0, 1, 2])
                            delta = random.choice([-1, 1])
                            
                            if random.random() < 0.5:
                                env[1][axis] += delta
                                env[2][axis] += delta
                            else:
                                if delta > 0:
                                    env[2][axis] += delta
                                else:
                                    if env[2][axis] > env[1][axis]:
                                        env[2][axis] += delta
                            
                            env[1][axis] = max(min_x, min(max_x if axis != 1 else max_y, env[1][axis]))
                            env[2][axis] = max(min_x, min(max_x if axis != 1 else max_y, env[2][axis]))
                        except Exception:
                            continue

            elif op == 4: 
                if max_x > min_x and max_y > min_y and max_z > min_z:
                    rx = random.randint(min_x, max_x)
                    ry = random.randint(min_y, max_y)
                    rz = random.randint(min_z, max_z)
                    mat = random.choice(OBJECT_DATA["media"])
                    new_env = [mat, [rx, ry, rz], [rx, ry, rz]]
                    
                    mutated_data.setdefault("environment", []).append(new_env)
                    env_idx = len(mutated_data["environment"]) - 1
                    mutated_data.setdefault("action_sequence", []).append([1, "environment", env_idx, None])

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