import os
import json
import shutil
import random
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.llm.llm import LLM
from src.utils.logger import log_message

class SeedEvaluation:
    def __init__(self, input_path=None, output_path=None, inconsistency_path=None, max_workers=10, global_ic_dir=None, current_active_time=0.0):
        self.input_path = input_path
        self.output_path = output_path
        self.inconsistency_path = inconsistency_path  
        
        current_mode = "watertest"
        for mode in ["watertest", "lighttest", "projectiletest"]:
            if mode in __file__ or (self.input_path and mode in self.input_path): current_mode = mode
        self.prompt_template_path = f"src/test/{current_mode}/seedevaluation/seedevaluation_prompt.json"
        
        self.llm = LLM()
        self.threshold = 0.9
        self.max_workers = max_workers
        self.lock = threading.Lock() 
        self.break_ok = 0
        self.inconsistency_found = 0
        self.current_active_time = current_active_time
        
        if global_ic_dir:
            self.target_data_path = os.path.join(global_ic_dir, "data.json")
            self.trace_file_path = os.path.join(global_ic_dir, "eval_trace.jsonl")
        else:
            self.target_data_path = "data.json"
            self.trace_file_path = "eval_trace.jsonl"
            
        self.batch_fitness_results = []
        if self.output_path and not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            
        self.evaluation()

    def evaluate_single_file(self, file_name, prompt_template):
        file_path = os.path.join(self.input_path, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                temp_data = json.load(f)
            if temp_data.get("status") == -1:
                return f"[Evaluation] Skip: {file_name}"

            final_prompt = self.assemble_evaluation_prompt(prompt_template, temp_data)
            llm_response = self.llm.chat(final_prompt)

            try:
                start = llm_response.find('{')
                end = llm_response.rfind('}') + 1
                res_json = json.loads(llm_response[start:end])
                temp_data["fitness"] = res_json
            except Exception:
                temp_data["fitness"] = None
                return f"[Evaluation ERROR] {file_name}: fitness=None"

            with self.lock:
                if temp_data.get("fitness"):
                    extracted_fitness = {}
                    for k, v in temp_data["fitness"].items():
                        if isinstance(v, dict) and "fitness" in v:
                            try:
                                extracted_fitness[k] = float(v["fitness"])
                            except (ValueError, TypeError):
                                extracted_fitness[k] = 0.0
                    self.batch_fitness_results.append(extracted_fitness)

            inc_fit = temp_data["fitness"].get("buoyancy_inconsistency", {})
            inc_fit_score = 0.0
            try:
                inc_fit_score = float(inc_fit.get('fitness', 0))
            except (ValueError, TypeError):
                inc_fit_score = 0.0
            
            temp_data["tested_times"] = temp_data.get("tested_times", 0) + 1
            rand_id = random.randint(1000, 9999)
            timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
            output_file_path = os.path.join(self.output_path, f"evaluation_{timestamp}_{rand_id}_{inc_fit_score}.json")
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(temp_data, f, ensure_ascii=False, indent=4)

            if inc_fit_score >= self.threshold:
                self.inconsistency_found = 1 
                ic_path = os.path.join(self.inconsistency_path, f"evaluation_{timestamp}_{rand_id}_{inc_fit_score}.json")
                with open(ic_path, 'w', encoding='utf-8') as f:
                    json.dump(temp_data, f, ensure_ascii=False, indent=4)
                return f"[Inconsistency Captured] {file_name}"

            return f"[Evaluation] Success: {file_name}"

        except Exception as e:
            return f"[Evaluation ERROR] {file_name}: {str(e)}"

    def evaluation(self):
        if not os.path.exists(self.input_path):
            return

        json_files = [f for f in os.listdir(self.input_path) if f.endswith('.json')]
        prompt_template = self.load_template()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.evaluate_single_file, f, prompt_template) for f in json_files]
            for future in as_completed(futures):
                log_message(future.result())
                
        self.append_to_trace()

    def append_to_trace(self):
        if not self.batch_fitness_results:
            return
            
        target_dir = os.path.dirname(self.trace_file_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        
        with open(self.trace_file_path, 'a', encoding='utf-8') as f:
            for fit_record in self.batch_fitness_results:
                trace_entry = {
                    "time": self.current_active_time,
                    "fitness": fit_record
                }
                f.write(json.dumps(trace_entry, ensure_ascii=False) + "\n")

    def load_template(self):
        with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def assemble_evaluation_prompt(self, template, input_data):
        mechanic = input_data.get("mechanic", "Unknown")
        
        environment = input_data.get("environment", [])
        object_blocks = input_data.get("object_blocks", [])
        object_mobs = input_data.get("object_mobs", [])
        trajectory_report = input_data.get("trajectory_report", ["No trajectory data."])

        if isinstance(trajectory_report, list):
            trajectory_report_str = "\n".join(trajectory_report)
        else:
            trajectory_report_str = str(trajectory_report)

        with open('src\\test\\watertest\\seedevaluation\\object_id.json', 'r', encoding='utf-8') as f:
            object_ids = f.read()
            
        template = template.replace("{{object_id_list}}", object_ids)

        prompt = template + f"""
        DATA TO AUDIT:
        Physical Mechanic Description (Target):
        {mechanic}
        **Scenario**:
        1. Environment Blueprint (Container & Fluids):
        {json.dumps(environment, indent=2)}
        2. Objects Spawned:
        Blocks: {json.dumps(object_blocks, indent=2)}
        Mobs/Entities: {json.dumps(object_mobs, indent=2)}
        3. Trajectory & Fluid Profile (Actual Execution Evidence):
        {trajectory_report_str}
        """

        return prompt