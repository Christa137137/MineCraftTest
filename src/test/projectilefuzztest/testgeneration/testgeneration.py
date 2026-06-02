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
from src.llm.llm import LLM
from src.test.projectiletest.mechanicgen.mechanicgen import MechanicGen
from src.utils.logger import log_message

class TestGeneration():

    def __init__(self, output_path=None, initial_seed_num=1, max_workers=10):
        self.output_path = output_path
        self.testgeneration_prompt_path = "src/test/projectiletest/testgeneration/testgeneration_prompt.json"
        self.llm = LLM()
        self.mechanic_gen = MechanicGen()
        self.initial_seed_num = initial_seed_num
        self.max_workers = max_workers # Thread pool size
        self.testgeneration()

    def generate_single_seed(self, index, mechanic_desc, object_ids, history_str):
        """single seed generation task for threading"""
        try:
            with open(self.testgeneration_prompt_path, 'r', encoding='utf-8') as f:
                template = f.read()

            final_prompt = template.replace("{{mechanic_description}}", mechanic_desc)
            final_prompt = final_prompt.replace("{{object_id_list}}", object_ids)
            final_prompt = final_prompt.replace("{{used_slugs}}", history_str)
        
            llm_answer = self.llm.chat(final_prompt)
            
            start = llm_answer.find('{')
            end = llm_answer.rfind('}') + 1
            json_data = json.loads(llm_answer[start:end])
            json_data["mechanic"] = mechanic_desc
    
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

        mechanic_desc = self.mechanic_gen.generate()
        
        with open('src/test/projectiletest/object_id.json', 'r', encoding='utf-8') as f:
            object_ids = f.read()
        
        history = []
        if os.path.exists("outputs/inconsistent_seeds/projectiletest/used_slugs.json"):
            with open("outputs/inconsistent_seeds/projectiletest/used_slugs.json", 'r', encoding='utf-8') as f:
                history = json.load(f)
        history_str = str(history)

        # print(f"Starting parallel generation with {self.max_workers} workers...")

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.generate_single_seed, i, mechanic_desc, object_ids, history_str) 
                for i in range(self.initial_seed_num)
            ]
            
            for future in as_completed(futures):
                res = future.result()
                results.append(res)
                log_message(res)
        
        return results

if __name__ == "__main__":
    TestGeneration(output_path="outputs/testcase", initial_seed_num=3, max_workers=10)