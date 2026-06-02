import os
import json
import random
import math
from datetime import datetime
from src.llm.llm import LLM
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import log_message

class SeedMutation:

    def __init__(self, input_path=None, output_path=None, max_workers=10):
        pass