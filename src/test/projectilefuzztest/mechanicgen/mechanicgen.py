from pathlib import Path
import sys
path_base = Path(__file__).resolve()
while path_base.name != "MineCraftTest":
    path_base = path_base.parent
sys.path.append(str(path_base))


import json
import os
from src.llm.llm import LLM

class MechanicGen:
    def __init__(self):
        self.prompt_path = "src/test/projectiletest/mechanicgen/mechanicgen_prompt.json"
        self.llm = LLM()
        self.base_dir = "outputs/inconsistent_seeds/projectiletest"
        self.slug_file = os.path.join(self.base_dir, "used_slugs.json")
        self.mechanic_file = os.path.join(self.base_dir, "used_mechanics.json")

    def generate(self):
        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            prompt_data = f.read()

        slug_history = []
        if os.path.exists(self.slug_file):
            with open(self.slug_file, 'r', encoding='utf-8') as f:
                slug_history = json.load(f)

        mechanic_history = []
        if os.path.exists(self.mechanic_file):
            with open(self.mechanic_file, 'r', encoding='utf-8') as f:
                mechanic_history = json.load(f)

        prompt_data = prompt_data.replace("{{used_slugs}}", str(slug_history))
        prompt_data = prompt_data.replace("{{used_mechanics}}", str(mechanic_history))

        chat_result = self.llm.chat(prompt_data)
        if chat_result is None:
            raise TimeoutError("[Mechanic] error")
        desc = chat_result.strip()
        
        mechanic_history.append(desc)
        os.makedirs(self.base_dir, exist_ok=True)
        with open(self.mechanic_file, 'w', encoding='utf-8') as f:
            json.dump(mechanic_history, f, ensure_ascii=False, indent=4)
        
        return desc


if __name__ == "__main__":
    generator = MechanicGen()
    
    try:
        result = generator.generate()

        print("result: ")
        print(result)

    except Exception as e:
        print(f"error: {e}")