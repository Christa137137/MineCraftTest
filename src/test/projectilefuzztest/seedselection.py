import os
import json
import random
from datetime import datetime

class SeedSelection:
    def __init__(self, input_path=None, output_path=None):
        self.input_path = input_path
        self.output_path = output_path
        self.max_pop = 20 
        if self.output_path and not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
        self.selection()

    def selection(self):
        if not os.path.exists(self.input_path): return
        json_files = [f for f in os.listdir(self.input_path) if f.endswith('.json')]
        if not json_files: return

        candidates = []
        for file_name in json_files:
            file_path = os.path.join(self.input_path, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    rank = data.get("current_rank", 10)
                    dist = data.get("current_ref_dist", 1.0)
                    candidates.append({"data": data, "rank": rank, "dist": dist})
            except: continue

        if not candidates: return
        num_rounds = min(len(candidates), self.max_pop)

        for i in range(num_rounds):
            if len(candidates) == 1:
                winner = candidates[0]
            else:
                participants = random.sample(candidates, 2)
                a, b = participants[0], participants[1]
                if a["rank"] < b["rank"]:
                    winner = a
                elif b["rank"] < a["rank"]:
                    winner = b
                else:
                    if a["dist"] < b["dist"]:
                        winner = a
                    elif b["dist"] < a["dist"]:
                        winner = b
                    else:
                        winner = random.choice([a, b])

            selected_data = winner["data"]
            timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
            rand_id = random.randint(1000, 9999)
            output_file_path = os.path.join(self.output_path, f"selection_{timestamp}_{i}_{rand_id}.json")
            try:
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(selected_data, f, ensure_ascii=False, indent=4)
            except: pass