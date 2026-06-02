import os
import json
import numpy as np
from datetime import datetime
from pymoo.util.ref_dirs import get_reference_directions

class SeedFilter:
    def __init__(self, input_path=None, output_path=None, is_init=False):
        self.input_path = input_path
        self.output_path = output_path
        self.max_pop = 20
        self.is_init = is_init

        self.ref_dirs = get_reference_directions("das-dennis", 4, n_partitions=2)
        
        if self.output_path and not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            
        self.current_reason = ""
        self.current_filename = ""
        self.last_saved_path = ""
        self.filter()

    def dominates(self, obj1, obj2):
        better = False
        for v1, v2 in zip(obj1, obj2):
            if v1 < v2: return False
            if v1 > v2: better = True
        return better

    def maintain_population(self):
        # nsga3 population maintenance logic
        files = [f for f in os.listdir(self.output_path) if f.endswith('.json')]
        if len(files) == 0: return

   
        def safe_float(val):
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        seeds_info = []
        for f_name in files:
            path = os.path.join(self.output_path, f_name)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    fit = data.get("fitness", {})
                
                    obj = np.array([
                        safe_float(fit.get("projectile_fitness", {}).get("fitness", 0)),
                        safe_float(fit.get("media_complexity", {}).get("fitness", 0)),
                        safe_float(fit.get("media_fitness", {}).get("fitness", 0)),
                        safe_float(fit.get("projectile_trajectory_inconsistency", {}).get("fitness", 0))
                    ])
                    seeds_info.append({"name": f_name, "obj": obj, "path": path, "full_data": data})
            except: continue

        # non dominated sorting
        fronts = [[]]
        for p in seeds_info:
            p['n'] = 0
            p['S'] = []
            for q in seeds_info:
                if self.dominates(p['obj'], q['obj']):
                    p['S'].append(q)
                elif self.dominates(q['obj'], p['obj']):
                    p['n'] += 1
            if p['n'] == 0:
                p['rank_val'] = 1
                fronts[0].append(p)

        i = 0
        while len(fronts[i]) > 0:
            next_front = []
            for p in fronts[i]:
                for q in p['S']:
                    q['n'] -= 1
                    if q['n'] == 0:
                        q['rank_val'] = i + 2
                        next_front.append(q)
            i += 1
            fronts.append(next_front)

        # associate each seed with nearest reference line
        for p in seeds_info:
            min_dist = float('inf')
            for w in self.ref_dirs:
                # perpendicular distance calculation
                w_norm = np.linalg.norm(w)
                proj = (np.dot(p['obj'], w) / (w_norm**2)) * w
                dist = np.linalg.norm(p['obj'] - proj)
                if dist < min_dist:
                    min_dist = dist
            p['ref_dist'] = dist

        # select survivors by rank then distance to reference line
        seeds_info.sort(key=lambda x: (x['rank_val'], x['ref_dist']))
        survivors = seeds_info[:self.max_pop]
        victims = seeds_info[self.max_pop:]

        # calculate energy based on rank and distance
        max_d = max([p['ref_dist'] for p in survivors]) if survivors else 1
        if max_d == 0: max_d = 1

        for p in survivors:
            rank_factor = 1.0 / p['rank_val']
            # closer to reference line means better diversity and convergence
            diversity_factor = 2.0 - (p['ref_dist'] / max_d)
            raw_energy = 1.5 * rank_factor * diversity_factor
            final_energy = int(round(min(3, max(1, raw_energy))))

            p['full_data']['current_rank'] = p['rank_val']
            p['full_data']['current_ref_dist'] = round(float(p['ref_dist']), 4)
            p['full_data']['current_energy'] = final_energy

            with open(p['path'], 'w', encoding='utf-8') as f:
                json.dump(p['full_data'], f, ensure_ascii=False, indent=4)

        for p in victims:
            if os.path.exists(p['path']): os.remove(p['path'])

    def filter(self):
        import random
        if not os.path.exists(self.input_path): return
        json_files = [f for f in os.listdir(self.input_path) if f.endswith('.json')]
        for i, file_name in enumerate(json_files):
            file_path = os.path.join(self.input_path, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get("status") == -1: continue
                
                
                raw_score = data.get("fitness", {}).get("projectile_trajectory_inconsistency", {}).get("fitness", 0)
                try:
                    inc_score = float(raw_score)
                except (ValueError, TypeError):
                    inc_score = 0.0
                
                timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
                rand_id = random.randint(1000, 9999)
                output_path = os.path.join(self.output_path, f"seed_{timestamp}_{i}_{rand_id}_{inc_score}.json")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                self.last_saved_path = output_path
            except: continue
           
        if not self.is_init:
            self.maintain_population()