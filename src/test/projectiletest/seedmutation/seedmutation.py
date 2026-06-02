import os
import json
import random
import math
from datetime import datetime
from src.llm.llm import LLM
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import log_message

class SeedMutation:

    def __init__(self, input_path=None, output_path=None, max_workers=10):
        self.input_path = input_path  
        self.output_path = output_path 
        self.mutation_prompt_path = "src/test/projectiletest/seedmutation/seedmutation_prompt.json"
        self.llm = LLM()
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
            pf_val = fd.get("projectile_fitness", {}).get("fitness", 0)
            mc_val = fd.get("media_complexity", {}).get("fitness", 0)
            mf_val = fd.get("media_fitness", {}).get("fitness", 0)
            pt_val = fd.get("projectile_trajectory_inconsistency", {}).get("fitness", 0)
            
            total_fitness = (pf_val + mc_val + mf_val) * 0.05 + (pt_val * 0.85)
            energy = 1

            for i in range(energy):
                mutation_prompt = self.assemble_mutation_prompt(seed_data)
                llm_answer = self.llm.chat(mutation_prompt)
    
                try:
                    start = llm_answer.find('{')
                    end = llm_answer.rfind('}') + 1
                    mutated_json = json.loads(llm_answer[start:end])
                    mutated_json["mechanic"] = original_mechanic
                    
                    rand_id = random.randint(1000, 9999)
                    timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
                    output_file_path = os.path.join(self.output_path, f"mutation_{timestamp}_{rand_id}.json")
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        json.dump(mutated_json, f, ensure_ascii=False, indent=4)
                except Exception:
                    continue
            return f"[Mutation] Success: {file_name}"
        except Exception as e:
            return f"[Mutation Error] {file_name}: {str(e)}"

    def assemble_mutation_prompt(self, seed_data):
        with open(self.mutation_prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        with open('src/test/projectiletest/object_id.json', 'r', encoding='utf-8') as f:
            object_ids = f.read()

        current_case = {
            "mechanic": seed_data.get("mechanic", "Unknown"),
            "object_blocks": seed_data.get("object_blocks"),
            "object_mobs": seed_data.get("object_mobs"),
            "environment": seed_data.get("environment"),
            "action_sequence": seed_data.get("action_sequence"),
            # "logs": seed_data.get("logs", [])
        }

        fitness_data = seed_data.get("fitness", {})
        guidance = ""
        keys = ["projectile_fitness", "media_complexity", "media_fitness", "projectile_trajectory_inconsistency"]
        for key in keys:
            detail = fitness_data.get(key, {})
            if isinstance(detail, dict):
                reason = detail.get("reason", "No reason provided")
                score = detail.get("fitness", "No fitness score provided")
                direction = detail.get("direction", "No direction provided")
                guidance += f"[{key}] (Reason: {reason}) (Score: {score}) (Mutate direction: {direction})\n"

        prompt = prompt_template.replace("{{original_seed}}", json.dumps(current_case, indent=2, ensure_ascii=False))
        prompt = prompt.replace("{{mutation_guidance}}", guidance)
        prompt = prompt.replace("{{object_id_list}}", object_ids)
        history = []
        if os.path.exists("outputs/inconsistent_seeds/projectiletest/used_slugs.json"):
            with open("outputs/inconsistent_seeds/projectiletest/used_slugs.json", 'r', encoding='utf-8') as f:
                history = json.load(f)

        prompt = prompt.replace("{{used_slugs}}", str(history))
        return prompt

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