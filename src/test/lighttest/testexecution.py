import time
import json
import os
import re
import subprocess
from datetime import datetime

from src.rcon.mcrconclient import MCRconClient
from src.test.lighttest.testcase import TestCase
from src.utils.logger import log_message

class TestExecution:

    def __init__(self, input_path=None, output_path=None, execute_tick_rate = 100):
        self.rcon = MCRconClient()
        self.bot_process = None
        self.execution_tick_rate = execute_tick_rate
        self.tick_rate = 20 
        self.time = 0
        self.log_records = [] 
        self.tracking_tags = []

        self.input_path = input_path
        self.output_path = output_path
        self.output_id = 1
        self.testcase = TestCase()
        
        self.light_baselines = {}

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

    def load_testcase(self, input_data):
        try:
            object_blocks = input_data.get("object_blocks", None)
            object_mobs = input_data.get("object_mobs", None)
            environment = input_data.get("environment", None)
            action_sequence = input_data.get("action_sequence", None)
            mechanic = input_data.get("mechanic", "light physics testing")
            
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
        self.light_baselines = {}
        
        self.time = 0
        self.log_records = [] 
        info += self.rcon.execute_cmd("kill @e[type=!player,x=0,y=50,z=0,distance=..100]")

        self.rcon.execute_cmd("forceload add -80 -80 80 80")
        
        # 光照测试必须保证外界处于绝对暗态
        self.rcon.execute_cmd("time set midnight")
        self.rcon.execute_cmd("gamerule doDaylightCycle false")
        self.rcon.execute_cmd("weather clear")

        if self.bot_process is None or self.bot_process.poll() is not None:
            bot_script_path = "src/utils/mineplayer_api/bot.js" 
            self.bot_process = subprocess.Popen(['node', bot_script_path])
        self.rcon.execute_cmd("gamemode spectator testbot")
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
            try:
                for action in action_sequence:
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
                    elif action_type == "object_blocks":
                        obj = self.testcase.object_blocks[action_index]
                        info = self.gen_obj_blocks(obj)
                    elif action_type == "object_mobs":
                        obj = self.testcase.object_mobs[action_index]
                        info = self.gen_obj_mob(obj)
                    elif action_type == "get_light_level":
                        # 解析范围读取指令，并执行光照读取与对比逻辑
                        p1 = action[3] 
                        p2 = action[4] if len(action) > 4 else None
                        if p2:
                            info = self.get_light_level(p1[0], p1[1], p1[2], p2[0], p2[1], p2[2])
                        else:
                            info = self.get_light_level(p1[0], p1[1], p1[2])
                    elif action_type == "sleep_till":
                        pass

                    if info != None and isinstance(info, str) and "here" in info.lower(): 
                        status = -1
                        self.save_logs_to_json(output_path=self.output_path, file_name=file_name, status=status)
                        self.reset()
                        break
                if status == 1:
                    log_message(f"[Execution] Success: {file_name}")
            except Exception as e:
                status = -1
                self._log(f"[Execution] ERROR Exception during execution of {file_name}: {str(e)}")
                log_message(f"[Execution] ERROR: {file_name}")
    
            self.save_logs_to_json(output_path=self.output_path, file_name=file_name, status=status)
            self.reset()

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

    # ========================================================
    # 核心光学数据处理模块：实现 Baseline 记录与 Intervention 差分提取
    # ========================================================
    def get_light_level(self, x1, y1, z1, x2=None, y2=None, z2=None):
        if x2 is None or y2 is None or z2 is None:
            x2, y2, z2 = x1, y1, z1
            
        cmd = f"getlightrange {int(x1)} {int(y1)} {int(z1)} {int(x2)} {int(y2)} {int(z2)}"
        raw_info = self.rcon.execute_cmd(cmd)
        
        # 解析命令返回的原始字符串，形如 "[10, 70, 0]: 14"
        pattern = r"\[(-?\d+),\s*(-?\d+),\s*(-?\d+)\]:\s*(\d+)"
        matches = re.findall(pattern, str(raw_info))
        
        current_state = {}
        for match in matches:
            coords = f"({match[0]},{match[1]},{match[2]})"
            current_state[coords] = int(match[3])
            
        range_key = f"{x1},{y1},{z1}_{x2},{y2},{z2}"
        
        # 第一阶段：如果是首次读取该范围 (T=1 Baseline)
        if range_key not in self.light_baselines:
            self.light_baselines[range_key] = current_state
            formatted_log = f"[{self.time}s] Baseline Light Intensity:\n"
            for k, v in current_state.items():
                formatted_log += f"  Point {k}: {v}\n"
            self._log(formatted_log.strip())
            return formatted_log.strip()
            
        # 第二阶段：如果之前读取过该范围 (T=6 Intervention)
        else:
            baseline_state = self.light_baselines[range_key]
            changes = []
            unchanged_count = 0
            
            # 计算差异 (Diff)
            for k, current_val in current_state.items():
                baseline_val = baseline_state.get(k)
                if baseline_val is not None and current_val != baseline_val:
                    if current_val < baseline_val:
                        changes.append(f"  Point {k}: dropped from {baseline_val} -> {current_val}")
                    else:
                        changes.append(f"  Point {k}: increased from {baseline_val} -> {current_val}")
                elif baseline_val is not None:
                    unchanged_count += 1
            
            # 只输出改变的节点，过滤冗余信息，保护大模型的注意力
            formatted_log = f"[{self.time}s] Light Level Changes Observed:\n"
            if changes:
                formatted_log += "\n".join(changes) + "\n"
            if unchanged_count > 0:
                formatted_log += f"  ({unchanged_count} points remained unchanged)"
            
            if not changes and unchanged_count == 0:
                formatted_log += "  No valid data parsed."
                
            self._log(formatted_log.strip())
            return formatted_log.strip()
    
    def reset(self):
        for tag in self.tracking_tags:
            self.rcon.execute_cmd(f"kill @e[tag={tag}]")
        self.rcon.execute_cmd("/kill @e[type=!player,x=0,y=50,z=0,distance=..100]")
        
        for object_mob in self.testcase.object_mobs:
            self.kill_obj_mob(object_mob)
        for object_block in self.testcase.object_blocks:
            self.kill_obj_block(object_block)
        for env in self.testcase.environment:
            self.kill_env_blocks(env)
            
        self.rcon.execute_cmd("/kill @e[type=!player,x=0,y=50,z=0,distance=..100]")

        self.tracking_tags = []
        self.light_baselines = {}

        self.time = 0
        self.log_records = [] 

    def sleep(self, total_duration):
        target_time = round(self.time + total_duration, 2)

        while self.time < target_time:
            step = 1.0 
            if round(self.time + step, 2) > target_time:
                step = round(target_time - self.time, 2)

            time.sleep(step * 20 / self.tick_rate)
            self.time = round(self.time + step, 2)

    def change_tick_rate(self, tick_rate):
        cmd = f"tick rate {tick_rate}"
        self.tick_rate = tick_rate
        info = self.rcon.execute_cmd(cmd)
        return info

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
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log_message(f"[Execution Error] Failed to save logs: {e}")