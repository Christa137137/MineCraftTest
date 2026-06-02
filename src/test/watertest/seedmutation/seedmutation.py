import os
import json
import random
import math
import copy
from datetime import datetime
from src.llm.llm import LLM
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import log_message

class SeedMutation:
    def __init__(self, input_path=None, output_path=None, max_workers=10):
        self.input_path = input_path  
        self.output_path = output_path 
        self.mutation_prompt_path = "src/test/watertest/seedmutation/seedmutation_prompt.json"
        self.llm = LLM()
        self.max_workers = max_workers
        
        if self.output_path and not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            
        self.mutation()

    def get_best_feedback(self):
        try:
            tasks_dir = os.path.dirname(os.path.dirname(self.input_path))
            all_tasks = sorted([os.path.join(tasks_dir, d) for d in os.listdir(tasks_dir) if d.startswith("task")], key=os.path.getmtime)
            
            if len(all_tasks) < 2: return None
            
            last_gen_eval_dir = os.path.join(all_tasks[-2], "evaluation")
            if not os.path.exists(last_gen_eval_dir): return None
            
            files = [os.path.join(last_gen_eval_dir, f) for f in os.listdir(last_gen_eval_dir) if f.endswith('.json')]
            
            best_seed = None
            max_score = -1.0
            
            for f_path in files:
                with open(f_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    fit = data.get("fitness", {})
                    score = float(fit.get("buoyancy_inconsistency", {}).get("fitness", 0))
                    if score > max_score:
                        max_score = score
                        best_seed = {
                            "summary": fit.get("scene_summary", {}).get("content", "No summary"),
                            "direction": fit.get("buoyancy_inconsistency", {}).get("direction", "No direction")
                        }
            return best_seed
        except: return None

    def mutate_single_file(self, file_name):
        file_path = os.path.join(self.input_path, file_name)
        feedback = self.get_best_feedback()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                seed_data = json.load(f)

            original_mechanic = seed_data.get("mechanic", "Unknown")
            fd = seed_data.get("fitness", {})
            s_val = fd.get("interaction_complexity", {}).get("fitness", 0)
            w_val = fd.get("fluid_fitness", {}).get("fitness", 0)
            o_val = fd.get("object_fitness", {}).get("fitness", 0)
            e_val = fd.get("environment_fitness", {}).get("fitness", 0)
            b_val = fd.get("buoyancy_inconsistency", {}).get("fitness", 0)
            
            total_fitness = (s_val + w_val + o_val + e_val) * 0.05 + (b_val * 0.8)
            energy = 1 

            for i in range(energy):
                mutation_prompt = self.assemble_mutation_prompt(seed_data, feedback)
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

    def assemble_mutation_prompt(self, seed_data, feedback):
        with open(self.mutation_prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        with open('src/test/watertest/object_id.json', 'r', encoding='utf-8') as f:
            object_ids = f.read()

        current_case = {
            "mechanic": seed_data.get("mechanic", "Unknown"),
            "object_blocks": seed_data.get("object_blocks"),
            "object_mobs": seed_data.get("object_mobs"),
            "environment": seed_data.get("environment"),
            "action_sequence": seed_data.get("action_sequence")
        }

        fitness_data = seed_data.get("fitness", {})
        guidance = ""
        keys = ["interaction_complexity", "fluid_fitness", "object_fitness", "environment_fitness","buoyancy_inconsistency"]
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
        if os.path.exists("outputs/inconsistent_seeds/watertest/used_slugs.json"):
            with open("outputs/inconsistent_seeds/watertest/used_slugs.json", 'r', encoding='utf-8') as f:
                history = json.load(f)
        prompt = prompt.replace("{{used_slugs}}", str(history))

        if feedback:
            prompt += f"\n\n[GENETIC FEEDBACK FROM PREVIOUS GENERATION BEST SEED]\nSummary: {feedback['summary']}\nEvolution Direction: {feedback['direction']}"
        
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