import json
import re
import math  # 新增：引入 math 库用于向上取整
from mcrcon import MCRcon

RCON_IP = "127.0.0.1"
RCON_PASS = "123456"
RCON_PORT = 25576
FILE_PATH = "src/test/watertest/object_id.json"

def clean_rcon_response(response):
    match = re.search(r"(\d+\.\d+,\d+\.\d+)", response)
    return match.group(1) if match else None

def format_num(n):
    # 修改点：将浮点数向上取整为最近的整数 (e.g., 1.4 -> 2, 2.7 -> 3)
    return str(math.ceil(float(n)))

def get_formatted_hitbox(entity_id, w, h):
    wf = format_num(w)
    hf = format_num(h)
    return f"{entity_id};{wf}*{hf}*{wf}"

def update_hitboxes():
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    try:
        with MCRcon(RCON_IP, RCON_PASS, port=RCON_PORT) as mcr:
            if "interactive_physics_objects" in data:
                obj_root = data["interactive_physics_objects"]
                for sub_key in obj_root:
                    new_sub_list = []
                    is_block_cat = sub_key in ["gravity_blocks", "fluid_interactive_blocks"]
                    
                    for entry in obj_root[sub_key]:
                        item_id = entry.split(';')[0].strip()
                        raw_id = item_id.split(':')[-1]
                        
                        if is_block_cat:
                            new_sub_list.append(raw_id)
                        else:
                            res = mcr.command(f"gethitboxbyid {raw_id}")
                            size = clean_rcon_response(res)
                            if size:
                                w, h = size.split(',')
                                new_sub_list.append(get_formatted_hitbox(raw_id, w, h))
                            else:
                                new_sub_list.append(raw_id)
                    obj_root[sub_key] = new_sub_list

            for cat in ["swimming_mobs", "non_swimming_mobs", "projectile_entities"]:
                if cat in data:
                    new_mob_list = []
                    for entry in data[cat]:
                        item_id = entry.split(';')[0].strip()
                        raw_id = item_id.split(':')[-1]
                        
                        res = mcr.command(f"gethitboxbyid {raw_id}")
                        size = clean_rcon_response(res)
                        if size:
                            w, h = size.split(',')
                            new_mob_list.append(get_formatted_hitbox(raw_id, w, h))
                        else:
                            new_mob_list.append(raw_id)
                    data[cat] = new_mob_list

        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Successfully updated object_id.json with new format.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_hitboxes()