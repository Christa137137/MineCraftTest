from pathlib import Path
import sys
path_base = Path(__file__).resolve()
while path_base.name != "MineCraftTest":
    path_base = path_base.parent
sys.path.append(str(path_base))

from mcrcon import MCRcon
import requests
import re


class MCRconClient:
    def __init__(self, ip="127.0.0.1", port=25576, password="123456", player="testbot"):
        self.ip = ip
        self.port = port
        self.password = password
        self.player = player
        self.connect()
  
    def connect(self):
        self.rcon = MCRcon(self.ip, self.password, self.port)
        self.rcon.connect()

    def disconnect(self):
        self.rcon.disconnect()

    def take_action(self, action):
        if (action == "forward"): 
            r = requests.post("http://localhost:3000/forward")
            return r.json()
            # return "forward"
        elif (action[0:4] == "mine"):
            r = requests.post("http://localhost:3000/mine/" + action[4:])
        else:
            return self.rcon.command(action)
    
    def execute_cmd(self, cmd):
        status = self.rcon.command(cmd)
        return status
        
    def collect_state(self, minX=-4, maxX=4, minZ=-4, maxZ=4, minY=-1, maxY=3, path=path_base.as_posix() + "/src/rcon/output/obs/obs.json"):
        cmd = f"state {self.player} {minX} {maxX} {minZ} {maxZ} {minY} {maxY} {path}"
        return self.rcon.command(cmd)
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()
        return False

if __name__ == "__main__":

    rcon = MCRconClient()
    rcon.connect()
    # print(rcon.rcon.command("state testuser -4 4 -4 4 -1 3 D:/about_computer/rl_mine/about_py_mc/output/state.json"))
    print(rcon.rcon.command("help"))
    # rcon.disconnect()s

    


