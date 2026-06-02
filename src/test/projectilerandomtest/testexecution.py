import time
import json
import os
import re
import math
import subprocess
from datetime import datetime

from src.rcon.mcrconclient import MCRconClient
from src.test.watertest.testcase import TestCase
from src.utils.logger import log_message

class TestExecution:

    def __init__(self, input_path=None, output_path=None, execute_tick_rate = 100):
        self.rcon = MCRconClient()
        self.bot_process = None
        self.execution_tick_rate = execute_tick_rate
        self.tick_rate = 20 #default 20, equal to real time
        self.time = 0
        self.log_records = [] 
        self.tracking_tags = []

        self.tracking_registry = {}  
        self.trajectory_history = {}
        self.final_positions = {}   
        self.mob_interval = 1     
        self.block_interval = 0.5
        self.projectile_interval = 0.1

        self.input_path = input_path
        self.output_path = output_path
        self.output_id = 1
        self.testcase = TestCase()
        self.gravity_block_ids = self.load_gravity_ids()

        self.object_catalog = self.load_object_catalog()
        self.mechanical_entities = self.object_catalog.get("interactive_physics_objects", {}).get("mechanical_entities", [])

        try:
            self.execution()
        finally:
            self.close()

    def close(self):
        self.rcon.execute_cmd("forceload remove all")
        self.rcon.execute_cmd("kick testbot")
        if hasattr(self, 'bot_process') and self.bot_process is not None:
            self.bot_process.kill()
            self.bot_process = None


        if hasattr(self.rcon, 'disconnect'):
            self.rcon.disconnect() 
        elif hasattr(self.rcon, 'close'):
            self.rcon.close()

    def load_object_catalog(self):
        try:
            path = "src/test/watertest/object_id.json"
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            log_message(f"[Execution] Error loading catalog: {e}")
            return {}
    def load_gravity_ids(self):
        try:
            with open("src/test/watertest/object_id.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
            raw_list = data.get("interactive_physics_objects", {}).get("gravity_blocks", [])
            return [item.split(';')[0].strip() for item in raw_list]
        except Exception as e:
            log_message(f"[Execution] Error loading gravity blocks: {e}")
            return []

    def load_testcase(self, input_data):
        try:
            object_blocks = input_data.get("object_blocks", None)
            object_mobs = input_data.get("object_mobs", None)
            environment = input_data.get("environment", None)
            action_sequence = input_data.get("action_sequence", None)
            mechanic = input_data.get("mechanic", "the water gravity related violation of physics rule")
            
            testcase = TestCase(object_blocks=object_blocks,
            object_mobs=object_mobs, environment=environment,
            action_sequence=action_sequence)
            
            testcase.mechanic = mechanic
            self.testcase = testcase
        except Exception as e:
            log_message(f"[Execution] Error loading testcase: {e}")
            return []
        
    def reset_init(self):
        info = ""
        info += self.rcon.execute_cmd("kill @e[type=!player,x=0,y=50,z=0,distance=..100]")
        for y_high in range(150, 9, -10):
            y_low = max(50, y_high - 9)
            self.rcon.execute_cmd(f"fill -20 {y_high} 20 20 {y_low} -20 air")
        info += self.rcon.execute_cmd("fill -10 150 -10 10 150 10 glass")

        self.tracking_tags = []
        self.tracking_registry = {}
        self.final_positions = {}
        self.trajectory_history = {}
        self.stuck_warnings = {}
        
        self.time = 0
        self.log_records = [] 
        # useless info += self.rcon.execute_cmd("kill @e[type=item,x=0,y=50,z=0,distance=..100]")
        # useless info += self.rcon.execute_cmd("kill @e[type=falling_block,x=0,y=50,z=0,distance=..100]")
        info += self.rcon.execute_cmd("kill @e[type=!player,x=0,y=50,z=0,distance=..100]")

        self.rcon.execute_cmd("forceload add -80 -80 80 80")
        self.rcon.execute_cmd("time set midnight")
        self.rcon.execute_cmd("gamerule doDaylightCycle false")
        self.rcon.execute_cmd("weather clear")

        if self.bot_process is None or self.bot_process.poll() is not None:

            bot_script_path = "src/utils/mineplayer_api/bot.js" 
            self.bot_process = subprocess.Popen(['node', bot_script_path])
        self.rcon.execute_cmd("gamemode spectator testbot")

        # useless self.rcon.execute_cmd("gamemode creative testbot")
        self.rcon.execute_cmd("tp testbot 0 70 0")

        self.change_tick_rate(self.execution_tick_rate)

    def execution(self):

        if not os.path.exists(self.input_path):
            log_message(f"[Execution] Error: directory {self.input_path} does not exist.")
            return

        json_files = [f for f in os.listdir(self.input_path) if f.endswith('.json')]

        self.reset_init()
        
        for file_name in json_files:

            file_path = os.path.join(self.input_path, file_name)
            input_data = None
            with open(file_path, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)
                    
            self.load_testcase(input_data)
            action_sequence = self.testcase.action_sequence

            # optional, for water
            if self.testcase.environment:
                env_len = len(self.testcase.environment)
                existing_env_indices = set(
                    action[2] for action in action_sequence if action[1] == "environment"
                )
                missing_indices = [i for i in range(env_len) if i not in existing_env_indices]
                if missing_indices:
                    for missing_idx in missing_indices:
                        action_sequence.append([0, "environment", missing_idx, None])
                    action_sequence.sort(key=lambda x: int(x[0]))

            status = 1
            trajectory_report = []
            try:
                for action in action_sequence:
                    # action format: [time, type, index, params]
                    target_time = int(action[0])
                    action_type = action[1]
                    action_index = action[2]
                    
                    info = None
                    if (self.time < target_time):
                        if target_time > 100:
                            status = -1
                            self.save_logs_to_json(output_path=self.output_path, file_name=file_name, status=status)
                            self.reset()
                            break
                        info = self.sleep(target_time - self.time)
                    
                    if action_type == "environment":
                        env = self.testcase.environment[action_index]
                        info = self.gen_env_blocks(env)
                        # log_message(info)
                    elif action_type == "object_blocks":
                        obj = self.testcase.object_blocks[action_index]
                        if obj[0] in self.gravity_block_ids:
                            info = self.gen_obj_falling_block(obj)
                        else:
                            info = self.gen_obj_blocks(obj)
                        # log_message(info)
                    elif action_type == "object_mobs":
                        obj = self.testcase.object_mobs[action_index]
                        info = self.gen_obj_mob(obj)
                        # log_message(info)
                    elif action_type == "projectile":            
                        obj = self.testcase.object_mobs[action_index]
                        motion = action[3]
                        info = self.gen_projectile(obj, motion)
                    elif action_type == "get_mob_pos":
                        obj = self.testcase.object_mobs[action_index]
                        info = self.get_mob_pos(obj)
                    elif action_type == "get_block_water_level":
                        pos = action[3]
                        x, y, z = pos
                        info = self.get_block_water_level(x, y, z)
                    elif action_type == "get_block_id":
                        x1, y1, z1 = action[3]
                        x2, y2, z2 = action[4]
                        info = self.get_block_id(x1, y1, z1, x2, y2, z2)
                    elif action_type == "sleep_till":
                        pass
                    # log_message("info:", info)
                    if info != None and isinstance(info, str) and "here" in info.lower(): # "here" means errors may happen
                        status = -1
                        self.save_logs_to_json(output_path=self.output_path, file_name=file_name, status=status)
                        self.reset()
                        break
                        # return status
                if status == 1:
                    trajectory_report = self.scan_trajectory_fluids()
                    log_message(f"[Execution] Success: {file_name}")
            except Exception as e:
                status = -1
                self._log(f"[Execution] ERROR Exception during execution of {file_name}: {str(e)}")
                log_message(f"[Execution] ERROR: {file_name}")
    
            self.save_logs_to_json(output_path=self.output_path, file_name=file_name, status=status,
                trajectory_report=trajectory_report)
            self.reset()
            

    # TODO 给所有rcon指令做异常处理 一旦出错丢弃
    def gen_env_blocks(self, env):
        try:
            pos1 = env[1]
            pos2 = env[2] if len(env) > 2 else env[1]
            cmd = f"fill {pos1[0]} {pos1[1]} {pos1[2]} {pos2[0]} {pos2[1]} {pos2[2]} {env[0]}"
            self._log(f"[{self.time}s] generate env blocks:", cmd)
            return self.rcon.execute_cmd(cmd)
        except:
            return "here error"

    def kill_env_blocks(self, env):
        try:
            pos1 = env[1]
            pos2 = env[2] if len(env) > 2 else env[1]
            cmd = f"fill {pos1[0]} {pos1[1]} {pos1[2]} {pos2[0]} {pos2[1]} {pos2[2]} air"
            self._log("kill env blocks:", cmd)
            return self.rcon.execute_cmd(cmd)
        except:
            return "here error"

    def gen_obj_blocks(self, obj):
        try:
            obj_id = obj[0]
            is_mechanical = any(item.split(';')[0] == obj_id for item in self.mechanical_entities)
            if is_mechanical:
                temp_mob_obj = [obj[0], obj[1], obj[2]] 
                return self.gen_obj_mob(temp_mob_obj)
            cmd = f"fill {obj[2][0]} {obj[2][1]} {obj[2][2]} {obj[3][0]} {obj[3][1]} {obj[3][2]} {obj[0]}"
            self._log(f"[{self.time}s] generate obj blocks:", cmd)
            return self.rcon.execute_cmd(cmd)
        except:
            return "here error"

    def kill_obj_block(self, obj):
        try:
            cmd = f"fill {obj[2][0]} {obj[2][1]} {obj[2][2]} {obj[2][0]} {obj[2][1]} {obj[2][2]} air"
            self._log("kill obj block:", cmd)
            return self.rcon.execute_cmd(cmd)
        except:
            return "here error"

    def gen_obj_mob(self, obj):
        try:
            tag = obj[1]
            pos = [int(obj[2][0]) + 0.5, int(obj[2][1]), int(obj[2][2]) + 0.5]
            cmd = f"summon {obj[0]} {pos[0]} {pos[1]} {pos[2]} {{Tags:[\"{tag}\"]}}"
            self._log(f"[{self.time}s] generate obj mob:", cmd)
            self.tracking_tags.append(tag)
            self.tracking_registry[tag] = {"type": "mob"}
            if not hasattr(self, 'trajectory_history'):
                self.trajectory_history = {}
            self.trajectory_history[tag] = [pos]
            return self.rcon.execute_cmd(cmd)
        except:
            return "here error"

    def kill_obj_mob(self, obj):
        try:
            cmd = f"kill @e[tag={obj[1]}]"
            self._log("kill obj mob:", cmd)
            return self.rcon.execute_cmd(cmd)
        except:
            return "here error"

    def gen_obj_falling_block(self, obj):
        block_id = obj[0]
        tag = obj[1]
        pos = [int(obj[2][0]), int(obj[2][1]), int(obj[2][2])]
        self.final_positions[tag] = pos

        cmd = f"summon falling_block {pos[0]} {pos[1]} {pos[2]} {{BlockState:{{Name:\"{block_id}\"}},Time:1,Tags:[\"{tag}\"]}}"
        self._log(f"[{self.time}s] generate falling block:", cmd)
        
        self.tracking_tags.append(tag) 
        self.tracking_registry[tag] = {"type": "block", "block_id": block_id}

        if not hasattr(self, 'trajectory_history'):
            self.trajectory_history = {}
        self.trajectory_history[tag] = [pos]
        
        info = self.rcon.execute_cmd(cmd)
        return info

    def gen_projectile(self, obj, motion):
        proj_id = obj[0]
        tag = obj[1]
        pos = [float(obj[2][0]) + 0.5, float(obj[2][1]), float(obj[2][2]) + 0.5]
        vx, vy, vz = float(motion[0]), float(motion[1]), float(motion[2])
        
        # 使用 Motion 标签注入初始速度
        cmd = f"summon {proj_id} {pos[0]} {pos[1]} {pos[2]} {{Tags:[\"{tag}\"], Motion:[{vx}d, {vy}d, {vz}d]}}"
        self._log(f"[{self.time}s] generate projectile:", cmd)
        
        self.tracking_tags.append(tag)
        self.tracking_registry[tag] = {"type": "projectile"}
        
        if not hasattr(self, 'trajectory_history'):
            self.trajectory_history = {}
        self.trajectory_history[tag] = [pos]
        
        info = self.rcon.execute_cmd(cmd)
        return info
    def get_block_water_level(self, x=None, y=None, z=None):
        if x is None:
            x, y, z = self.testcase.pos
            
        cmd = f"getwaterlevel {x} {y} {z}"
        info = self.rcon.execute_cmd(cmd)
        self._log(f"[{self.time}s] check water level of pos {x} {y} {z}:", info)
        
        if "water_level:" in info:
            try:
                level = info.split("water_level:")[1].strip()
                return level
            except:
                return "-1"
        return "1"
    
    def get_block_id(self, x1, y1, z1, x2=None, y2=None, z2=None):

        if x2 is None or y2 is None or z2 is None:
            x2, y2, z2 = x1, y1, z1
            
        cmd = f"getblockid {x1} {y1} {z1} {x2} {y2} {z2}"
        info = self.rcon.execute_cmd(cmd)
        self._log(f"[{self.time}s] check block id of range {x1} {y1} {z1} to {x2} {y2} {z2}:", info)
        
        if "in range" not in info and ":" not in info:
            return "-1"

        return info
    
    def get_mob_pos(self, obj):
        tag = obj[1]
        cmd = f"data get entity @e[tag={tag}, limit=1] Pos"
        self._log(f"[{self.time}s] get mob pos:", cmd)
        raw_info = self.rcon.execute_cmd(cmd)
        
        pattern = r"data:\s*\[(.*?)\]"
        match = re.search(pattern, str(raw_info))
        if match:
            raw_content = match.group(1)
            pos = [
                float(x.strip().replace('d', '')) 
                for x in raw_content.split(',')
            ]
            self.final_pos = pos
            self._log(f"[{self.time}s] mob {tag} pos is:", pos)
            return str(pos)
        return "1"


    
    def reset(self):
        for tag in self.tracking_tags:
            self.rcon.execute_cmd(f"kill @e[tag={tag}]")
        self.rcon.execute_cmd("/kill @e[type=!player,x=0,y=50,z=0,distance=..100]")
        self.tracking_tags = []
        self.tracking_registry = {}
        for object_mob in self.testcase.object_mobs:
            self.kill_obj_mob(object_mob)
        for object_block in self.testcase.object_blocks:
            self.kill_obj_block(object_block)
        for env in self.testcase.environment:
            self.kill_env_blocks(env)
        self.rcon.execute_cmd("/kill @e[type=!player,x=0,y=50,z=0,distance=..100]")

        self.tracking_tags = []
        self.tracking_registry = {}
        self.final_positions = {}      
        if hasattr(self, 'trajectory_history'):
            self.trajectory_history = {} 
        if hasattr(self, 'stuck_warnings'):
            self.stuck_warnings = {}

        self.time = 0
        self.log_records = [] 
        # self.change_tick_rate(20)

    def sleep(self, total_duration):
        target_time = round(self.time + total_duration, 2)

        while self.time < target_time:

            step = 1.0 
            if self.tracking_registry:
                has_projectile = any(info["type"] == "projectile" for info in self.tracking_registry.values())
                step = 0.1 if has_projectile else 0.5
            
            if round(self.time + step, 2) > target_time:
                step = round(target_time - self.time, 2)

            time.sleep(step * 20 / self.tick_rate)
            self.time = round(self.time + step, 2)

            if self.tracking_registry:
                for tag, registry_info in list(self.tracking_registry.items()):
                    obj_type = registry_info["type"]
                    if obj_type == "mob":
                        interval = self.mob_interval
                    elif obj_type == "block":
                        interval = self.block_interval
                    elif obj_type == "projectile":
                        interval = self.projectile_interval
                    else:
                        interval = 1.0

                    ticks_time = int(round(self.time * 10))
                    ticks_interval = int(round(interval * 10))
                    if ticks_time % ticks_interval == 0:
                        self.auto_get_pos_by_tag(tag, registry_info)

    def auto_get_pos_by_tag(self, tag, registry_info):
        obj_type = registry_info["type"]
        cmd = f"data get entity @e[tag={tag}, limit=1] Pos"
        raw_info = self.rcon.execute_cmd(cmd)
        pattern = r"data:\s*\[(.*?)\]"
        match = re.search(pattern, str(raw_info))
        
        if match:
            raw_content = match.group(1)
            pos = [float(f"{round(float(x.strip().replace('d', '')), 2):g}") for x in raw_content.split(',')]
            self.final_positions[tag] = pos 

            if tag not in self.trajectory_history:
                self.trajectory_history[tag] = []
            self.trajectory_history[tag].append(pos)

            self._log(f"[{self.time:.1f}s][{obj_type}] {tag} pos:", pos)
            
            # === 新增：针对弹射物获取实时速度，并监控是否停止 ===
            if obj_type == "projectile":
                vel_cmd = f"data get entity @e[tag={tag}, limit=1] Motion"
                vel_info = self.rcon.execute_cmd(vel_cmd)
                vel_match = re.search(pattern, str(vel_info))
                if vel_match:
                    vel_content = vel_match.group(1)
                    vel = [float(x.strip().replace('d', '')) for x in vel_content.split(',')]
                    self._log(f"[{self.time:.1f}s][{obj_type}] {tag} velocity: {vel}")
                    
                    # 当速度极度趋近于0，说明弹射物撞墙/落地停止了
                    if all(abs(v) < 0.01 for v in vel):
                        self._log(f"[{self.time:.1f}s][SETTLED] {tag} has stopped moving (velocity ~0).")
                        # 弹射物停止后，移出追踪队列以节约系统开销
                        del self.tracking_registry[tag]
                        
        else:
            if obj_type == "projectile":
                # 查不到该实体坐标，说明在撞击中粉碎销毁（如雪球）
                self._log(f"[{self.time:.1f}s][DESTROYED] {tag} vanished or shattered on impact.")
                if tag in self.tracking_registry:
                    del self.tracking_registry[tag]
                    
            elif obj_type == "block":
                last_pos = self.final_positions.get(tag)
                if last_pos:
                    x, y, z = int(last_pos[0]), int(last_pos[1]), int(last_pos[2])
                    
                    # get the needed block name
                    target_id = registry_info["block_id"].upper().replace("MINECRAFT:", "").split(';')[0].strip()
                    found_settled = False
                    
                    # scan 10 blocks under 
                    for y_offset in range(0, 11):
                        check_y = y - y_offset
                        block_info = self.get_block_id(x, check_y, z).upper().replace("MINECRAFT:", "")
                        
                        if target_id in block_info:
                            self._log(f"[{self.time:.1f}s][SETTLED] {tag} found at y={check_y}: {block_info}")
                            final_block_pos = [float(x), float(check_y), float(z)]
                            self.final_positions[tag] = final_block_pos

                            self.trajectory_history[tag].append(final_block_pos)

                            found_settled = True
                            break
                    
                    if not found_settled:
                        # find if it turns to item
                        search_cmd = f"data get entity @e[type=item, x={x}, y={y}, z={z}, distance=..10, limit=1] Item.id"
                        item_info = self.rcon.execute_cmd(search_cmd)
                        if "data:" in item_info.lower():
                            self._log(f"[{self.time:.1f}s][DROPPED] {tag} missing but found item: {item_info}, if the id is different, ignorn this.")
                        else:
                            self._log(f"[{self.time:.1f}s][LOST] {tag} disappeared completely.")
                
                if tag in self.tracking_registry:
                    del self.tracking_registry[tag]

    def sleep_get_state(self, sleep_time):
        for d_t in range(0, int(sleep_time)):
            state_info = self.get_state()
            pattern = r"data:\s*\[(.*?)\]"
            match = re.search(pattern, str(state_info))
            if match:
                raw_content = match.group(1)
                pos = tuple(
                    float(x.strip().replace('d', '')) 
                    for x in raw_content.split(',')
                )
                self.final_pos = pos

            self._log(f"[{self.time}s]", state_info)
            time.sleep(20 / self.tick_rate)
            self.time += 1

    def change_tick_rate(self, tick_rate):
        cmd = f"tick rate {tick_rate}"
        self.tick_rate = tick_rate
        info = self.rcon.execute_cmd(cmd)
        return info

    def get_state(self):
        object_mobs = self.testcase.object_mobs
        results = []
        for obj in object_mobs:
            tag = obj[1]
            cmd = f"data get entity @e[tag={tag}, limit=1] Pos"
            info = self.rcon.execute_cmd(cmd)
            results.append(info)
        return results
        

    def _log(self, *args):
        message = " ".join(map(str, args))

        self.log_records.append(message)


    def save_logs_to_json(self, output_path=None, file_name = None, status=None, **extra_params):
        self.output_id += 1

        file_path = os.path.join(output_path, file_name)

        output_data = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "logs": self.log_records,
            "mechanic": self.testcase.mechanic,
            "object_blocks": self.testcase.object_blocks,
            "object_mobs": self.testcase.object_mobs,
            "environment": self.testcase.environment,
            "action_sequence": self.testcase.action_sequence
        }

        output_data.update(extra_params)

        timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
        output_file_path = os.path.join(self.output_path, f"execution_{timestamp}.json")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            # log_message(f"Logs saved successfully to: {output_file_path}") 
        except Exception as e:
            log_message(f"[Execution Error] Failed to save logs: {e}")



    def _get_single_block_char(self, block_info):
        info_lower = block_info.lower()
        if "water" in info_lower:

            match = re.search(r"level:(\d+)", info_lower)
            if match:
                return match.group(1)
            return "0" 
        elif "bubble_column" in info_lower:
            return "b"
        elif "air" in info_lower or "in range" in info_lower or "-1" in info_lower:
            return "_"
        else:
            block_name = block_info.replace("minecraft:", "").split("[")[0].strip().lower()
            if not block_name:
                block_name = "solid"
            return f"[{block_name}]"

    def _get_block_desc(self, x, y, z):
        blocks_info = self.get_block_id(x, y-2, z, x, y+1, z)
        
        id_dict = {y+1: "air", y: "air", y-1: "air", y-2: "air"}
        
        
        for cy in [y+1, y, y-1, y-2]:
            match_id = re.search(fr"\[{x},{cy},{z}\]:(.*?)(?=\s*\[\d+,\d+,\d+\]:|$)", blocks_info)
            if match_id:
                id_dict[cy] = match_id.group(1).strip()
   
        main_block_info = id_dict[y].lower()
        if "water" in main_block_info:
            main_name = "water"
        elif "bubble_column" in main_block_info:
            main_name = "bubble_column"
        elif "air" in main_block_info:
            main_name = "air"
        else:
            main_name = main_block_info.replace("minecraft:", "").split("[")[0].strip()

        char_above = self._get_single_block_char(id_dict[y+1])
        char_current = self._get_single_block_char(id_dict[y])
        char_below1 = self._get_single_block_char(id_dict[y-1])
        char_below2 = self._get_single_block_char(id_dict[y-2])

        return f"{char_above}{char_current}{char_below1}{char_below2}"

    def scan_trajectory_fluids(self):
        report_logs = []
        report_logs.append("[Trajectory Fluid Profiling]")
        
        for tag, history in self.trajectory_history.items():
            if not history:
                continue
            
            start_pos = history[0]
            end_pos = history[-1]
            delta_y = round(end_pos[1] - start_pos[1], 2)
            
            report_logs.append(f"  - Entity '{tag}' actual movement: Start {start_pos} -> End {end_pos}. Delta_Y: {delta_y}")
            
            block_path = []
            for i in range(len(history)):
                bx, by, bz = int(history[i][0]), int(history[i][1]), int(history[i][2])
                if not block_path:
                    block_path.append((bx, by, bz))
                else:
                    last_bx, last_by, last_bz = block_path[-1]
                    if by != last_by:
                        step_y = -1 if by < last_by else 1
                        for y_fill in range(last_by + step_y, by + step_y, step_y):
                            block_path.append((last_bx, y_fill, last_bz))
                    if block_path[-1] != (bx, by, bz):
                        block_path.append((bx, by, bz))

            path_nodes = []
            for bx, by, bz in block_path:
                desc = self._get_block_desc(bx, by, bz)
                path_nodes.append({'pos': (bx, by, bz), 'desc': desc})

            merged_path = []
            if path_nodes:
                start_node = path_nodes[0]
                last_node = path_nodes[0]
                
                for node in path_nodes[1:]:
                    if node['desc'] == start_node['desc']:
                        last_node = node
                    else:
                        if start_node['pos'] == last_node['pos']:
                            merged_path.append(f"({start_node['pos'][0]},{start_node['pos'][1]},{start_node['pos'][2]}):{start_node['desc']}")
                        else:
                            merged_path.append(f"({start_node['pos'][0]},{start_node['pos'][1]},{start_node['pos'][2]}) to ({last_node['pos'][0]},{last_node['pos'][1]},{last_node['pos'][2]}):{start_node['desc']}")
                        
                        start_node = node
                        last_node = node
                
                if start_node['pos'] == last_node['pos']:
                    merged_path.append(f"({start_node['pos'][0]},{start_node['pos'][1]},{start_node['pos'][2]}):{start_node['desc']}")
                else:
                    merged_path.append(f"({start_node['pos'][0]},{start_node['pos'][1]},{start_node['pos'][2]}) to ({last_node['pos'][0]},{last_node['pos'][1]},{last_node['pos'][2]}):{start_node['desc']}")

            report_logs.append(f"Path: " + " -> ".join(merged_path))
            
        for line in report_logs:
            self._log(line)
            
        return report_logs
