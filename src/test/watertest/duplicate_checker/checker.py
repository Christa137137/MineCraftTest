import os
import json
import shutil
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.llm.llm import LLM
from src.utils.logger import log_message

class DuplicateChecker:
    def __init__(self, inconsistency_path=None, max_workers=10, global_ic_dir=None, current_active_time=0.0):
        self.inconsistency_path = inconsistency_path
        self.global_ic_dir = global_ic_dir
        self.current_active_time = current_active_time

        current_mode = "watertest"
        self.prompt_path = f"src/test/{current_mode}/duplicate_checker/checker_prompt.json"
        
        self.llm = LLM()
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self.total_count = 0
        self.new_count = 0
        
        if global_ic_dir:
            self.target_data_path = os.path.join(global_ic_dir, "data.json")
        else:
            self.target_data_path = "data.json"

        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_config = json.load(f)

        if self.inconsistency_path:
            self.total_count, self.new_count = self.check_all(self.inconsistency_path)
            self.update_inconsistency_data()

    def update_inconsistency_data(self):
        if self.new_count == 0:
            return
            
        target_dir = os.path.dirname(self.target_data_path)
        os.makedirs(target_dir, exist_ok=True)
        
        with self.lock:
            data = {}
            if os.path.exists(self.target_data_path):
                try:
                    with open(self.target_data_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    pass
                    
            data["new_inconsistency_count"] = data.get("new_inconsistency_count", 0) + self.new_count
            
            history = data.get("discovery_history", [])
            history.append({
                "time": self.current_active_time,
                "new_found_this_batch": self.new_count,
                "cumulative_total": data["new_inconsistency_count"]
            })
            data["discovery_history"] = history
            
            with open(self.target_data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

    def check_all(self, ic_dir):
        target_dir = self.global_ic_dir if self.global_ic_dir else ic_dir
        history_file = os.path.join(target_dir, "used_slugs.json") 
        os.makedirs(target_dir, exist_ok=True)
        
        files = [f for f in os.listdir(ic_dir) if f.endswith('.json')]
        total = len(files)
        new_found = 0

        if total == 0: 
            return 0, 0
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(self.process_single_ic, f, ic_dir, target_dir, history_file) for f in files]
            for future in as_completed(futures): 
                new_found += future.result() 
        
        return total, new_found

    def process_single_ic(self, file_name, ic_dir, target_dir, history_file):
        path = os.path.join(ic_dir, file_name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            reason = data.get("fitness", {}).get("buoyancy_inconsistency", {}).get("reason", "")
            if not reason:
                return 0

            with self.lock:
                history_slugs = []
                if os.path.exists(history_file):
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history_slugs = json.load(f)

            results_list = self.check_redundancy(reason, history_slugs)
            
         
            if results_list:
                results_list = results_list[:1]
            else:
                return 0
            
            data["duplicate_checker_output"] = results_list

            with self.lock:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            
            new_bugs_in_this_file = 0

            with self.lock:
                history_slugs = []
                if os.path.exists(history_file):
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history_slugs = json.load(f)

                for res in results_list:
                    s_reason = res.get("simplified_reason")
                    if s_reason and isinstance(s_reason, str): s_reason = s_reason.strip()
                    
                    r_dir = res.get("redundant_dir")
                    if r_dir and isinstance(r_dir, str): r_dir = r_dir.strip()

                    is_not_red = res.get("not_redundant", True)

                    final_slug = s_reason if is_not_red else r_dir
                    if not final_slug: 
                        final_slug = "Unknown_Anomaly"

                    final_slug = final_slug.replace("\n", "").replace("\r", "").strip()

                    if final_slug not in history_slugs:
                        history_slugs.append(final_slug)
                        new_bugs_in_this_file += 1
                        is_not_red = True 

                    final_target_dir = os.path.join(target_dir, final_slug)
                    os.makedirs(final_target_dir, exist_ok=True)
                    
                    shutil.copy(path, os.path.join(final_target_dir, file_name))

                    status_str = "New Unique" if is_not_red else "Redundant"
                    log_message(f"[Duplicate Checker] {status_str}: {final_slug} ({file_name})")

                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(history_slugs, f, ensure_ascii=False, indent=4)

            return new_bugs_in_this_file
            
        except Exception as e:
            log_message(f"[Checker Error] {file_name}: {e}")
            return 0

    def check_redundancy(self, reason, history_slugs):
        input_data = {
            "new_reason": reason,
            "history_slugs": history_slugs
        }
        
        full_prompt = f"{json.dumps(self.prompt_config, ensure_ascii=False)}\n\nInput: {json.dumps(input_data, ensure_ascii=False)}"
        
        response = self.llm.chat(full_prompt)
        try:
            clean_res = response.replace("```json", "").replace("```", "").strip()
            res_data = json.loads(clean_res)
            return res_data.get("results", [])
        except Exception as e:
            log_message(f"[Checker error] Parse error: {e}")
            return []