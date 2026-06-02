from pathlib import Path
import sys
path_base = Path(__file__).resolve()
while path_base.name != "MineCraftTest":
    path_base = path_base.parent
sys.path.append(str(path_base))

import json
import math

from rcon.mcrconclient import MCRconClient
from src.llm.llm import LLMClient

class Agent:
    def __init__(self):
        self.mc_rcon_client = MCRconClient()
        self.mc_rcon_client.connect()
        self.llm_client = LLMClient()
        self.last_pos = None
        self.player = "testbot"
    def __del__(self):
        self.mc_rcon_client.disconnect()
    def step(self, action):
        info = self.take_action(action)
        obs = self.get_obs()
        return info
    
    def take_action(self, action):
        info = self.mc_rcon_client.take_action(action)
        return info
    def get_obs(self, minX=-4, maxX=4, minZ=-4, maxZ=4, minY=-1, maxY=3, path=path_base.as_posix() + "/src/rcon/output/obs/obs.json"):
        obs = self.mc_rcon_client.collect_state(minX, maxX, minZ, maxZ, minY, maxY, path)
        return None
    
    def gen_action(self):
        obs = json.load(open(path_base.as_posix() + "/src/rcon/output/obs/obs.json"))
        
        entities = obs["nearby_entities"]
        blocks = obs["nearby_blocks"]
        usage = obs["usage"]
        cmd = obs["cmd"]
        center = obs["center"]

        player_x = center["x"]
        player_z = center["z"]
        player_y = center["y"]
        pos = [player_x, player_z, player_y]

        user_input = ""
        user_input += str(center) + usage + cmd + str(entities)

        refresh_dist = 4
        if (self.last_pos != None and math.dist(pos, self.last_pos) < refresh_dist):
            pass
        else:
            user_input += str(blocks) 
        self.last_pos = pos

        action = self.llm_client.chat(user_input)
        return action
    


    