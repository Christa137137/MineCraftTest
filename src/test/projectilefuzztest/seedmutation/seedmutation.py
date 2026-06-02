import os
import json
import random
import math
import copy
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import log_message

OBJECT_DATA = {
    "penetrable_media": [
        "honey_block", "slime_block", "cobweb", 
        "oak_leaves", "powder_snow", "mud"
    ],
    "medium_blocks": [
        "air", "water", "lava", "soul_sand"
    ],
    "projectiles": [
        "arrow", "trident", "snowball"
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
       
            s_val = fd.get("interaction_complexity", {}).get("fitness") or 0
            w_val = fd.get("fluid_fitness", {}).get("fitness") or 0
            o_val = fd.get("object_fitness", {}).get("fitness") or 0
            e_val = fd.get("environment_fitness", {}).get("fitness") or 0
            b_val = fd.get("projectile_trajectory_inconsistency", {}).get("fitness") or 0
            
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
                except Exception:
                    continue
                    
            return f"[Mutation] Success: {file_name} generated {energy} variants."
        except Exception as e:
            return f"[Mutation Error] {file_name}: {str(e)}"

    def hardcode_random_mutate(self, seed_data):
        mutated_data = copy.deepcopy(seed_data)
        
        num_ops = random.randint(1, 2)
        ops = random.sample([1, 2, 3, 4], num_ops)

        for op in ops:
            if op == 1: 
                obj_mobs = mutated_data.get("object_mobs", [])
                if len(obj_mobs) >= 2:
                    new_projectile = random.choice(OBJECT_DATA["projectiles"])
                    obj_mobs[0][0] = new_projectile
                    obj_mobs[1][0] = new_projectile

            elif op == 2: 
                seq = mutated_data.get("action_sequence", [])
                projectile_actions = [action for action in seq if len(action) >= 4 and action[1] == "projectile"]
                
                if len(projectile_actions) >= 2:
                    orig_v = projectile_actions[0][3]
                    if isinstance(orig_v, list) and len(orig_v) >= 3:
                        dx = random.uniform(-0.5, 0.5)
                        dy = random.uniform(-0.5, 0.5)
                        
                        new_vx = max(-3.0, min(3.0, round(orig_v[0] + dx, 2)))
                        new_vy = max(-3.0, min(3.0, round(orig_v[1] + dy, 2)))
                        new_vz = 0.0 
                        
                        for p_action in projectile_actions:
                            p_action[3] = [new_vx, new_vy, new_vz]

            elif op == 3: 
                env_list = mutated_data.get("environment", [])
                target_envs = [env for env in env_list if env[0] not in ["glass", "air"]]
                if target_envs:
                    env_to_mutate = random.choice(target_envs)
                    is_fluid = env_to_mutate[0] in OBJECT_DATA["medium_blocks"]
                    if is_fluid:
                        env_to_mutate[0] = random.choice(OBJECT_DATA["medium_blocks"])
                    else:
                        env_to_mutate[0] = random.choice(OBJECT_DATA["penetrable_media"])

            elif op == 4: 
                env_list = mutated_data.get("environment", [])
                target_envs = [env for env in env_list if env[0] not in ["glass", "air"]]
                if target_envs:
                    env_to_mutate = random.choice(target_envs)
                    if len(env_to_mutate) >= 3:
                        pos1 = env_to_mutate[1]
                        pos2 = env_to_mutate[2]
                        
                        axis = random.choice([0, 1])
                        delta = random.choice([-1, 1])
                        
                        if random.random() < 0.5:
                            pos1[axis] += delta
                            pos2[axis] += delta
                        else:
                            if delta > 0:
                                pos2[axis] += delta
                            else:
                                if pos2[axis] > pos1[axis]:
                                    pos2[axis] += delta
                        
                        pos1[axis] = max(-10, min(10 if axis != 1 else 90, pos1[axis]))
                        pos2[axis] = max(-10, min(10 if axis != 1 else 90, pos2[axis]))
                        if axis == 1:
                            pos1[1] = max(60, pos1[1])
                            pos2[1] = max(60, pos2[1])

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