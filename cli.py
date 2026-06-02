import shutil
import time
import os
import sys
import json
import importlib
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib.ticker import MaxNLocator
from datetime import datetime
from src.llm.llm import LLM
from src.rcon.mcrconclient import MCRconClient
from src.test.watertest.testcase import TestCase
# from src.test.watertest.testexecution import TestExecution
# from src.test.watertest.seedevaluation.seedevaluation import SeedEvaluation
# from src.test.watertest.seedmutation.seedmutation import SeedMutation
# from src.test.watertest.seedselection import SeedSelection
# from src.test.watertest.seedfilter import SeedFilter
# from src.test.watertest.testgeneration.testgeneration import TestGeneration
# from src.test.watertest.duplicate_checker.checker import DuplicateChecker
from src.utils.logger import log_message, set_log_file


def load_test_suite(mode):
    base_map = {
        "watertest": "src.test.watertest",
        "waterrandomtest": "src.test.waterrandomtest",
        "waterfuzztest": "src.test.waterfuzztest",
        "lighttest": "src.test.lighttest",
        "projectiletest": "src.test.projectiletest"
    }
    
    pkg = base_map[mode]

    suite = {
        "Execution":  importlib.import_module(f"{pkg}.testexecution").TestExecution,
        "Evaluation": importlib.import_module("src.test.watertest.seedevaluation.seedevaluation").SeedEvaluation if "random" in mode else importlib.import_module(f"{pkg}.seedevaluation.seedevaluation").SeedEvaluation,
        "Mutation":   importlib.import_module(f"{pkg}.seedmutation.seedmutation").SeedMutation if "random" not in mode else None,
        "Generation": importlib.import_module(f"{pkg}.testgeneration.testgeneration").TestGeneration,
        "Checker":    importlib.import_module("src.test.watertest.duplicate_checker.checker").DuplicateChecker if "random" in mode else importlib.import_module(f"{pkg}.duplicate_checker.checker").DuplicateChecker,
        "Selection":  importlib.import_module(f"{pkg}.seedselection").SeedSelection if "random" not in mode else None,
        "Filter":     importlib.import_module(f"{pkg}.seedfilter").SeedFilter if "random" not in mode else None,
    }
    return suite

def get_init_path(mode, method):
    timestamp = datetime.now().strftime("%m%d_%H%M%S")
    session_root = os.path.join("outputs", mode, f"{method}_{timestamp}")
    
    population_path = os.path.join(session_root, "population")
    task_path = os.path.join(session_root, "tasks")
    ic_path = os.path.join(session_root, "inconsistent_seeds")
    
    os.makedirs(task_path, exist_ok=True)
    os.makedirs(population_path, exist_ok=True)
    os.makedirs(ic_path, exist_ok=True)
    
    return population_path, task_path, task_path, task_path, task_path, task_path, ic_path

def get_path(population_path, selection_path, execution_path, mutation_path, testcase_path, evaluation_path, inconsistency_path, is_init=False):
    timestamp = datetime.now().strftime("%m%d_%H%M%S%f")
    new_selection_path = selection_path + f"\\task{timestamp}\\selection"
    os.makedirs(new_selection_path)
    new_execution_path = execution_path + f"\\task{timestamp}\\execution"
    os.makedirs(new_execution_path)
    new_mutation_path = mutation_path + f"\\task{timestamp}\\mutation"
    os.makedirs(new_mutation_path)
    new_evaluation_path = evaluation_path + f"\\task{timestamp}\\evaluation"
    os.makedirs(new_evaluation_path)

    new_testcase_path = testcase_path + f"\\task{timestamp}\\testcase"
    if is_init:
        os.makedirs(new_testcase_path)

    new_inconsistency_path = evaluation_path + f"\\task{timestamp}\\inconsistency"
    os.makedirs(new_inconsistency_path)

    return population_path, new_selection_path, new_execution_path, new_mutation_path, new_testcase_path, new_evaluation_path, new_inconsistency_path
def run_loop(Suite, paths, method, global_start_time, max_worker_num=10, step_confirm=0, time_limit_minutes=120, batch_size=20, do_eval=True):
    stagnant_rounds = 0
    step_confirm_count = step_confirm
    pop_dir = paths[0]
    time_file = os.path.join(pop_dir, "time_stats.json")
    ttl_limit = time_limit_minutes * 60
    global_ic = paths[6]
    
    accumulated_eval_time = 0.0

    last_check_time = time.time()  # [change]

    try:
        while True:

            current_time = time.time()  # [change]
            time_jump = current_time - last_check_time  # [change]
            if time_jump > 600:  # [change]
                log_message(f"[System] Warning: time jump {time_jump/60:.1f} m, compensating.")  # [change]
                global_start_time += time_jump  # [change]
            last_check_time = time.time()  # [change]

            current_active_time = (time.time() - global_start_time) - accumulated_eval_time

            if current_active_time >= ttl_limit:
                log_message(f"[Timeout] limit={time_limit_minutes}m, active_time={current_active_time/60:.2f}m.")
                with open(time_file, 'w') as f:
                    json.dump({"elapsed_time": (time.time() - global_start_time), "active_time": current_active_time}, f)
                break

            if step_confirm > 0:
                if step_confirm_count <= 0:
                    user_input = input(f"\n[Interactive] already executed {step_confirm} rounds, input y to continue: ")
                    if user_input.strip().lower() != 'y':
                        return False 
                    step_confirm_count = step_confirm
                step_confirm_count -= 1

            p, s, e, m, tc, ev, ic = get_path(paths[0], paths[1], paths[2], paths[3], paths[4], paths[5], paths[6])

            if method == "random":
                Suite["Generation"](output_path=tc, batch_size=batch_size)
                Suite["Execution"](input_path=tc, output_path=e)
            else:
                Suite["Selection"](input_path=p, output_path=s)
                Suite["Mutation"](input_path=s, output_path=m, max_workers=max_worker_num)
                Suite["Execution"](input_path=m, output_path=e)

            current_active_time = (time.time() - global_start_time) - accumulated_eval_time
            new_ic = 0

            if do_eval:
                eval_start = time.time()
                
                Suite["Evaluation"](input_path=e, output_path=ev, inconsistency_path=ic, max_workers=max_worker_num, global_ic_dir=global_ic, current_active_time=current_active_time)
                checker = Suite["Checker"](inconsistency_path=ic, max_workers=max_worker_num, global_ic_dir=global_ic, current_active_time=current_active_time)
                new_ic = checker.new_count

                if method != "proposed":
                    accumulated_eval_time += (time.time() - eval_start)

            if method != "random":
                Suite["Filter"](input_path=ev, output_path=p)

                if new_ic == 0:
                    stagnant_rounds += 1
                    log_message(f"[System] stagnant rounds {stagnant_rounds}/5")
                else:
                    stagnant_rounds = 0 

                if stagnant_rounds >= 5:
                    log_message(f"[System] stagnant rounds {stagnant_rounds}/5 drop seeds")
                    pop_files = [f for f in os.listdir(p) if f.endswith('.json')]
                    seeds_data = []
                    for f in pop_files:
                        f_path = os.path.join(p, f)
                        try:
                            with open(f_path, 'r', encoding='utf-8') as file:
                                d = json.load(file)
                                rank = d.get("current_rank", 10)
                                dist = d.get("current_ref_dist", 0.0)
                                seeds_data.append({"path": f_path, "rank": rank, "dist": dist})
                        except: pass

                    seeds_data.sort(key=lambda x: (x['rank'], x['dist']), reverse=True)
                    drop_count = min(15, len(seeds_data) - 1)
                    if drop_count < 0: drop_count = 0

                    for i in range(drop_count):
                        if os.path.exists(seeds_data[i]["path"]):
                            os.remove(seeds_data[i]["path"])

                    for d in [tc, e, ev]:
                        if os.path.exists(d):
                            for f in os.listdir(d):
                                if f.endswith('.json'):
                                    os.remove(os.path.join(d, f))
                    
                    if drop_count > 0:
                        Suite["Generation"](output_path=tc, initial_seed_num=drop_count, max_workers=max_worker_num)
                        Suite["Execution"](input_path=tc, output_path=e)
                        
                        refresh_active_time = (time.time() - global_start_time) - accumulated_eval_time
                        
                        if do_eval:
                            eval_start = time.time()
                            Suite["Evaluation"](input_path=e, output_path=ev, inconsistency_path=ic, max_workers=max_worker_num, global_ic_dir=global_ic, current_active_time=refresh_active_time)
                            Suite["Checker"](inconsistency_path=ic, max_workers=max_worker_num, global_ic_dir=global_ic, current_active_time=refresh_active_time)
                            
                            if method != "proposed":
                                accumulated_eval_time += (time.time() - eval_start)

                        Suite["Filter"](input_path=ev, output_path=p)
                    stagnant_rounds = 0

            with open(time_file, 'w') as f:
                json.dump({"elapsed_time": (time.time() - global_start_time), "active_time": ((time.time() - global_start_time) - accumulated_eval_time)}, f)
                
        return True

    except KeyboardInterrupt:
        log_message("[System] KeyboardInterrupt caught in Fuzz Loop. Forcing hard exit.")
        sys.exit(0)

def run(mode="watertest", method="proposed", initial_seed_num=20, max_worker_num=10, time_limit_minutes=120, batch_size_for_random=20, step_confirm=False, do_eval=True, session_num=1):
    """main entry

    Args:
        mode (str): test mode. Select from "watertest",  "lighttest" and "projectiletest".
        method (str): test method. Select from "proposed", "random", "fuzz".
        initial_seed_num (int): initial seed number only for proposed and mutation methods.
        max_worker_num (int): max worker number for parallelization.
        time_limit_minutes (int): time limit for each session in minutes.
        batch_size_for_random (int): batch size for each round only for random method.
        step_confirm (bool): whether to confirm each step.
        do_eval (bool): whether to do evaluation for all methods.
        session_num (int): number of sessions to run.
    """

    Suite = load_test_suite(mode)
    
    for i in range(session_num):
        
        paths = get_init_path(mode, method)
        population_dir = paths[0]
        os.makedirs(population_dir, exist_ok=True)
        set_log_file(os.path.join(paths[0], "..", "test_log.txt"))
        
        log_message(f"\n{'='*20} Starting Session {i+1} ({mode} - {method}) {'='*20}")

        with open(os.path.join(population_dir, "session_config.json"), "w") as f:
            json.dump(paths, f)

        global_start_time = time.time()
        global_ic = paths[6]

        if method != "random":
            p, s, e, m, tc, ev, ic = get_path(paths[0], paths[1], paths[2], paths[3], paths[4], paths[5], paths[6], is_init=True)
            
            Suite["Generation"](output_path=tc, initial_seed_num=initial_seed_num, max_workers=max_worker_num)
            Suite["Execution"](input_path=tc, output_path=e)
            
            if do_eval:
                eval_start = time.time()
                Suite["Evaluation"](input_path=e, output_path=ev, inconsistency_path=ic, max_workers=max_worker_num, global_ic_dir=global_ic, current_active_time=0.0)
                Suite["Checker"](inconsistency_path=ic, max_workers=max_worker_num, global_ic_dir=global_ic, current_active_time=0.0)
                
                if method != "proposed":
                    global_start_time += (time.time() - eval_start)

            Suite["Filter"](input_path=ev, output_path=p, is_init=True)

        should_continue = run_loop(
            Suite=Suite, 
            paths=paths, 
            method=method,
            global_start_time=global_start_time, 
            max_worker_num=max_worker_num, 
            step_confirm=step_confirm,
            time_limit_minutes=time_limit_minutes,
            batch_size=batch_size_for_random,
            do_eval=do_eval
        )
        
        if not should_continue:
            log_message("[System] Finished.")
            break

def run_resume(session_dir, time_limit_minutes=120, max_worker_num=10, batch_size_for_random=20, step_confirm=False, do_eval=True):
    """
    Resume an interrupted fuzzing session.
    
    Args:
        session_dir (str): The path to the session directory (e.g., "outputs/watertest/proposed_0507_232316")
        time_limit_minutes (int): Expected time limit for the resumed session in minutes(e.g., expected run duration is 10h, but interrupted at 3h, but still want total time 10h, then just set time_limit_minutes = 10h).
    """

    
    # 1. 解析 mode 和 method (从路径名称中提取，例如 outputs/watertest/proposed_0507_232316)
    parts = os.path.normpath(session_dir).split(os.sep)
    mode = parts[-2]
    method_str = parts[-1]
    method = method_str.split("_")[0]  # 提取 "proposed", "random" 或 "fuzz"

    Suite = load_test_suite(mode)

    # 2. 恢复各种文件夹路径
    config_path = os.path.join(session_dir, "population", "session_config.json")
    if not os.path.exists(config_path):
        log_message(f"[Error] Cannot find session config at {config_path}. Resume failed.")
        return
        
    with open(config_path, "r", encoding='utf-8') as f:
        paths = json.load(f)

    set_log_file(os.path.join(paths[0], "..", "test_log.txt"))

    global_ic = paths[6]
    eval_trace_path = os.path.join(global_ic, "eval_trace.jsonl")

    # 3. 读取 eval_trace.jsonl 最后一次记录的有效运行时间
    last_active_time = 0.0
    if os.path.exists(eval_trace_path):
        try:
            with open(eval_trace_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 倒序查找非空行
                for line in reversed(lines):
                    if line.strip():
                        record = json.loads(line)
                        last_active_time = record.get("time", 0.0)
                        break
        except Exception as e:
            log_message(f"[Warning] Failed to parse last active time from trace: {e}")

    # 如果没找到 trace 文件，作为备用去查 time_stats.json
    if last_active_time <= 0:
        time_file = os.path.join(paths[0], "time_stats.json")
        if os.path.exists(time_file):
            try:
                with open(time_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    last_active_time = stats.get("active_time", 0.0)
            except:
                pass

    log_message(f"\n{'='*20} Resuming Session ({mode} - {method}) {'='*20}")
    log_message(f"[Resume] Recovered from: {session_dir}")
    log_message(f"[Resume] Last recorded active time: {last_active_time / 60:.2f} minutes")
    
    if (last_active_time / 60) >= time_limit_minutes:
        log_message("[System] Session has already reached or exceeded the time limit. Exit.")
        return

    # 4. 时间魔法：欺骗系统，让它以为已经跑了这么久
    # run_loop 内部有 accumulated_eval_time = 0.0，
    # 所以 current_active_time = (time.time() - global_start_time) - 0.0 = last_active_time
    global_start_time = time.time() - last_active_time

    should_continue = run_loop(
        Suite=Suite, 
        paths=paths, 
        method=method,
        global_start_time=global_start_time, 
        max_worker_num=max_worker_num, 
        step_confirm=step_confirm,
        time_limit_minutes=time_limit_minutes,
        batch_size=batch_size_for_random,
        do_eval=do_eval
    )
    
    if not should_continue:
        log_message("[System] Resume Finished.")
 

# def run_water_randomtest(batch_size_for_random=20, eval=False, time_limit_minutes=120):
#     timestamp = datetime.now().strftime("%m%d_%H%M%S")
#     base_dir = f"outputs/tasks/waterrandomtest/random_exp_{timestamp}"
    
#     task_base = os.path.join(base_dir, "rounds")
#     all_exe_dir = os.path.join(base_dir, "all_executions")
#     all_eva_dir = os.path.join(base_dir, "all_evaluations")
#     ic_dir = os.path.join(base_dir, "inconsistent_seeds")
    
#     for d in [task_base, all_exe_dir, all_eva_dir, ic_dir]:
#         os.makedirs(d, exist_ok=True)

#     RandomSuite = load_test_suite("waterrandomtest")

#     # [change] 
#     global_start_time = time.time()
#     ttl_limit = time_limit_minutes * 60

#     def check_timeout(step_name=""):
#         elapsed = time.time() - global_start_time
#         if elapsed >= ttl_limit:
#             log_message(f"[Timeout] limit={time_limit_minutes}, elapsed={elapsed/60:.2f}, step={step_name}")
#             return True
#         return False

#     # [change] 
#     r = 1
#     while True:
#         if check_timeout(f"Round {r} Start"):
#             break

#         log_message(f"\n{'='*20} Round {r} {'='*20}")
        
#         round_path = os.path.join(task_base, f"round_{r}")
#         gen_path = os.path.join(round_path, "generation")
#         exe_path = os.path.join(round_path, "execution")
        
#         for p in [gen_path, exe_path]: 
#             os.makedirs(p, exist_ok=True)

#         # [change] 
#         if check_timeout(f"Round {r} Generation"): break
#         RandomSuite["Generation"](output_path=gen_path, batch_size=batch_size_for_random)
        
#         if check_timeout(f"Round {r} Execution"): break
#         RandomSuite["Execution"](input_path=gen_path, output_path=exe_path)

#         for f in os.listdir(exe_path):
#             if f.endswith(".json"):
#                 shutil.copy(os.path.join(exe_path, f), os.path.join(all_exe_dir, f))
        
#         r += 1

#     # [change] 
#     if eval:
#         log_message(f"[Evaluation] Batch Evaluation")
#         RandomSuite["Evaluation"](input_path=all_exe_dir, output_path=all_eva_dir, inconsistency_path=ic_dir)
#         RandomSuite["Checker"](inconsistency_path=ic_dir)

def run_temp(mode="watertest", gen_num=0, do_eval=False, max_worker_num=1, execute_tick_rate=40):   
    Suite = load_test_suite(mode)
   
    base_dir = os.path.join("outputs", "run_temp")
    set_log_file(os.path.join(base_dir, "log.txt"))
    gen_dir = os.path.join(base_dir, "generation")
    exe_dir = os.path.join(base_dir, "execution")
    eval_dir = os.path.join(base_dir, "evaluation")
    ic_dir = os.path.join(base_dir, "inconsistency")

    for d in [gen_dir, exe_dir, eval_dir, ic_dir]:
        os.makedirs(d, exist_ok=True)

    if gen_num > 0:
        Suite["Generation"](output_path=gen_dir, initial_seed_num=gen_num, max_workers=max_worker_num)

    Suite["Execution"](input_path=gen_dir, output_path=exe_dir, execute_tick_rate=execute_tick_rate)

    if do_eval:
        current_active_time = time.time()
        Suite["Evaluation"](
            input_path=exe_dir, 
            output_path=eval_dir, 
            inconsistency_path=ic_dir, 
            max_workers=max_worker_num, 
            global_ic_dir=ic_dir, 
            current_active_time=current_active_time
        )
        Suite["Checker"](
            inconsistency_path=ic_dir, 
            max_workers=max_worker_num, 
            global_ic_dir=ic_dir, 
            current_active_time=current_active_time
        )


def generate_metrics_plots(session_dir):
    set_log_file(os.path.join(session_dir, "run.log"))  # [change]
    
    ic_dir = os.path.join(session_dir, "inconsistent_seeds")
    config_path = os.path.join(session_dir, "population", "session_config.json")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                paths = json.load(f)
                ic_dir = paths[6] 
        except Exception:
            pass

    eval_file = os.path.join(ic_dir, "eval_trace.jsonl")
    data_file = os.path.join(ic_dir, "data.json")

    output_dir = os.path.join(session_dir, "metrics")
    os.makedirs(output_dir, exist_ok=True)
    log_message(f"[Metrics] 开始为 {session_dir} 生成可视化报告...")

    if os.path.exists(eval_file):
        data = defaultdict(lambda: defaultdict(list))
        with open(eval_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    record = json.loads(line)
                    time_val = record.get("time")
                    fitness_dict = record.get("fitness", {})
                    for key, val in fitness_dict.items():
                        try:
                            data[key][time_val].append(float(val))
                        except (ValueError, TypeError):
                            pass
                except json.JSONDecodeError:
                    pass

        for fit_key, time_dict in data.items():
            if not time_dict: continue
            sorted_times = sorted(time_dict.keys())
            averages = [sum(time_dict[t]) / len(time_dict[t]) for t in sorted_times]

            plt.figure(figsize=(10, 6))
            plt.plot(sorted_times, averages, marker='o', linestyle='-', linewidth=2, markersize=5)
            
            plt.ylim(0, 1) 
            plt.title(f"{fit_key} over Time", fontsize=14, pad=15)
            plt.xlabel("Time (s)", fontsize=12)
            plt.ylabel(f"Average {fit_key}", fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.7)
            
            output_file_path = os.path.join(output_dir, f"{fit_key}.png")
            plt.savefig(output_file_path, bbox_inches='tight')
            plt.close()
        log_message(f"[Metrics] 成功生成 Fitness 演化图至 {output_dir}")
    else:
        log_message(f"[Metrics 警告] 找不到 {eval_file}，跳过 Fitness 绘图。")

    if os.path.exists(data_file):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                target_data = json.load(f)
            
            history = target_data.get("discovery_history", [])
            if history:
                times = []
                cumulative_counts = []

                for entry in history:
                    time_val = entry.get("time")
                    cumulative_total = entry.get("cumulative_total")
                    
                    if time_val is not None and cumulative_total is not None:
                        times.append(float(time_val))
                        cumulative_counts.append(int(cumulative_total))

                if times and cumulative_counts:
                    if times[0] > 0:
                        times.insert(0, 0.0)
                        cumulative_counts.insert(0, 0)

                    plt.figure(figsize=(10, 6))
                    plt.step(times, cumulative_counts, where='post', color='red', linewidth=2, marker='o', markersize=4)
                    
                    plt.title("Cumulative New Inconsistencies Discovered", fontsize=14, pad=15)
                    plt.xlabel("Time (s)", fontsize=12)
                    plt.ylabel("Total Unique Bugs Found", fontsize=12)
                    plt.grid(True, linestyle='--', alpha=0.7)
                    
                    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
                    
                    output_file_path = os.path.join(output_dir, "new_inconsistencies_count.png")
                    plt.savefig(output_file_path, bbox_inches='tight')
                    plt.close()
                    log_message(f"[Metrics] 成功生成累积漏洞图至 {output_dir}")
            else:
                log_message(f"[Metrics 提示] {data_file} 中没有 discovery_history 数据。")
        except Exception as e:
            log_message(f"[Metrics 错误] 处理 data.json 时发生错误: {e}")
    else:
        log_message(f"[Metrics 警告] 找不到 {data_file}，跳过 Inconsistencies 数量绘图。")




VERIFY_PROMPT_TEMPLATE = """
{
    "role": "You are a Minecraft Physics Bug Triage Expert specializing in precise deduplication.",
    "background": "Our testing pipeline fuzzes Minecraft to find anomalies where the game's simplified fluid mechanics violate real-world physics. You will read the 'buoyancy_inconsistency' reason and the 'trajectory_report' to extract the core physical violations, standardize them into highly precise slugs, and check for redundancy against a historical database.",
    "task": "Analyze the input reason and trajectory. Extract EACH distinct anomaly. Format each into a strict 4-part slug. Compare with 'history_slugs' to determine if it is redundant. Output ONLY a JSON object.",
    "domain_knowledge": [
        "Focus ONLY on 'INCONSISTENT' entities.",
        "1. StaticWater: Heavy objects sink, low/medium-density float.",
        "2. UpwardBubbles: Lifts low/medium-density, high-density sinks.",
        "3. DownwardBubbles: Pulls medium/high-density down.",
        "4. HorizontalFlow: Carries low/medium-density laterally.",
        "5. Waterfall: ALL objects plummet downward due to gravity."
    ],
    "history_slugs": {history_slugs},
    "slug_naming_convention": {
        "rule": "Strict 4-part PascalCase slug separated by underscores: [Object(Property)]_[WaterShape(Context)]_[IngameInconsistentAction]_[RealWorldExpectation].",
        "Part_1_Object": "ObjectName(KeyProperty). Example: IronGolem(HeavyMob), Boat(HollowVessel), Cod(SwimmingMob), Sand(GravityBlock).",
        "Part_2_WaterShape": "Shape(Context). Example: Waterfall(WithSolidGroundBelow), Waterfall(WithAWideGroundOnTheBottom), StaticWater(DeepPool).",
        "Part_3_IngameInconsistentAction": "What wrongly happened. Example: RiseUpward, SuspendMidWater, Stationary.",
        "Part_4_RealWorldExpectation": "What SHOULD have happened. Example: SinkToBottom, PlummetDownward, DriftLaterally."
    },
    "deduplication_logic": "Anomalies are redundant if the KeyProperty, Shape(Context), IngameAction, and RealWorldExpectation match. For example, OakBoat(HollowVessel)_StaticWater(DeepPool)_SinkToBottom_FloatOnSurface is highly redundant with MangroveBoat(HollowVessel)_StaticWater(DeepPool)_SinkToBottom_FloatOnSurface. Minor coordinate differences do not make it unique.",
    "input_data": {
        "reason": "{reason}",
        "trajectory_report": {trajectory}
    },
    "output_format": {
        "results": [
            {
                "not_redundant": true,
                "simplified_reason": "string (The newly generated 4-part slug. Null if redundant)",
                "redundant_dir": "string (Exact copy from history_slugs. Null if not_redundant is true)"
            }
        ]
    }
}
"""

def verify_and_deduplicate(session_dir, limit_per_dir=3, do_execute=False):
    import random
    llm_client = LLM()
    inc_dir = os.path.join(session_dir, "inconsistent_seeds")
    verify_out_dir = os.path.join(session_dir, "verified_unique_seeds")
    
    if not os.path.exists(inc_dir):
        return

    os.makedirs(verify_out_dir, exist_ok=True)
    
    files = [f for f in os.listdir(inc_dir) if f.endswith('.json')]
    random.shuffle(files)
    files_to_process = files[:limit_per_dir]
    
    history_slugs = []

    if do_execute:
        from src.test.watertest.testexecution import TestExecution

    for f_name in files_to_process:
        f_path = os.path.join(inc_dir, f_name)
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if do_execute:
                temp_input_dir = os.path.join(session_dir, "temp_verify_in")
                temp_output_dir = os.path.join(session_dir, "temp_verify_out")
                os.makedirs(temp_input_dir, exist_ok=True)
                os.makedirs(temp_output_dir, exist_ok=True)
                
                temp_file_path = os.path.join(temp_input_dir, f_name)
                with open(temp_file_path, 'w', encoding='utf-8') as tf:
                    json.dump(data, tf, ensure_ascii=False)
                    
                exe = TestExecution(input_path=temp_input_dir, output_path=temp_output_dir)
                
                out_files = [f for f in os.listdir(temp_output_dir) if f.endswith('.json')]
                if out_files:
                    with open(os.path.join(temp_output_dir, out_files[0]), 'r', encoding='utf-8') as rf:
                        data = json.load(rf)

            reason = data.get("fitness", {}).get("buoyancy_inconsistency", {}).get("reason", "")
            trajectory = json.dumps(data.get("trajectory_report", []))
            
            prompt = VERIFY_PROMPT_TEMPLATE.replace("{history_slugs}", json.dumps(history_slugs))
            prompt = prompt.replace("{reason}", reason.replace('"', '\\"'))
            prompt = prompt.replace("{trajectory}", trajectory)
            
            response = llm_client.chat(prompt)
            
            start = response.find('{')
            end = response.rfind('}') + 1
            res_json = json.loads(response[start:end])
            
            results = res_json.get("results", [])
            for res in results:
                if res.get("not_redundant"):
                    new_slug = res.get("simplified_reason")
                    if new_slug and new_slug not in history_slugs:
                        history_slugs.append(new_slug)
                        
                        data["verification_slug"] = new_slug
                        out_path = os.path.join(verify_out_dir, f"verified_{new_slug}_{f_name}")
                        with open(out_path, 'w', encoding='utf-8') as out_f:
                            json.dump(data, out_f, ensure_ascii=False, indent=4)
                            
        except Exception:
            continue


if __name__ == "__main__":

    # run(mode="waterrandomtest", method="random", time_limit_minutes=600, batch_size_for_random=20, do_eval=True, session_num=1, max_worker_num=20)

    # run(mode="waterfuzztest", method="fuzz", time_limit_minutes=300, do_eval=True, session_num=1, max_worker_num=20)

    run(mode="watertest", method="proposed", time_limit_minutes=300, do_eval=True, session_num=1, max_worker_num=20)

    # run_resume(session_dir="outputs\watertest\proposed_0510_013259", time_limit_minutes=600, max_worker_num=20, step_confirm=False, do_eval=True)

    # run_resume(session_dir="outputs\waterrandomtest\\random_0512_220351", time_limit_minutes=600, max_worker_num=20, step_confirm=False, do_eval=True)

    # run_resume(session_dir="outputs\waterfuzztest\\fuzz_0510_234911", time_limit_minutes=600, max_worker_num=20, step_confirm=False, do_eval=True)

    # generate_metrics_plots(r"outputs\waterfuzztest\fuzz_0523_044411")

    # run_temp(execute_tick_rate=100, do_eval=True)






# /fill ~-10 ~-10 ~-10 ~10 ~10 ~10 air
# /kill @e[type=!player,x=0,y=50,z=0,distance=..100]