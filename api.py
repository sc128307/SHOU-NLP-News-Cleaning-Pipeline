import sys
import json
import os
import threading
import traceback
import io
import urllib.request

# ==========================================================
# 1. 配置区域：单模型架构 (DeBERTa All-in-One)
# ==========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = CURRENT_DIR
sys.path.append(CURRENT_DIR)
CorpusPipelineClass = None
MODEL_CONFIGS = {
    "NOISE_CAPTION": os.path.join(
        PROJECT_ROOT, "models", "noise-cleaner-deberta-v2", "final"
    ),
    "SEMANTIC_MODEL": os.path.join(PROJECT_ROOT, "models", "all-MiniLM-L6-v2"),
}

# 你的 HF 仓库 ID (如果未来需要更新检查，否则可忽略)
HF_REPO_ID = "gysgzyh/noise-cleaner-deberta-v2"

# === 2. 系统输出重定向 (保持不变) ===
REAL_STDOUT = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class JSONStdout:
    def __init__(self):
        self.buffer = ""

    def write(self, text):
        if not text:
            return
        self.buffer += text
        if "\n" in self.buffer:
            lines = self.buffer.split("\n")
            for line in lines[:-1]:
                self._send_log(line)
            self.buffer = lines[-1]

    def flush(self):
        if self.buffer:
            self._send_log(self.buffer)
            self.buffer = ""

    def _send_log(self, msg):
        if not msg.strip():
            return
        try:
            if msg.strip().startswith("{") and msg.strip().endswith("}"):
                json.loads(msg)
                REAL_STDOUT.write(msg + "\n")
                REAL_STDOUT.flush()
                return
        except:
            pass
        payload = json.dumps({"type": "info", "msg": msg}, ensure_ascii=False)
        REAL_STDOUT.write(payload + "\n")
        REAL_STDOUT.flush()


sys.stdout = JSONStdout()
sys.stderr = JSONStdout()


def send_system_json(data):
    REAL_STDOUT.write(json.dumps(data, ensure_ascii=False) + "\n")
    REAL_STDOUT.flush()


def check_all_models_exist():
    missing = []
    for name, path in MODEL_CONFIGS.items():
        if not os.path.exists(path):
            missing.append(f"{name}")
    return (len(missing) == 0), missing


# [简化] 检查 HF 更新逻辑 (适配单模型)
def check_update_from_hf(manual_check=False):
    try:
        model_path = MODEL_CONFIGS["NOISE_CAPTION"]
        version_file = os.path.join(model_path, "version.txt")
        local_sha = "unknown"

        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                local_sha = f.read().strip()

        api_url = f"https://huggingface.co/api/models/{HF_REPO_ID}"
        with urllib.request.urlopen(api_url, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                remote_sha = data.get("sha")

                if remote_sha and local_sha != remote_sha:
                    send_system_json(
                        {
                            "type": "update-available",
                            "current": local_sha[:7],
                            "latest": remote_sha[:7],
                            "url": f"https://huggingface.co/{HF_REPO_ID}",
                        }
                    )
                elif manual_check:
                    send_system_json(
                        {"type": "update-not-found", "msg": "Model is up to date."}
                    )
    except Exception as e:
        if manual_check:
            send_system_json({"type": "update-not-found", "msg": f"Check failed: {e}"})


def main():
    # 1. 启动检查
    all_exist, missing = check_all_models_exist()
    init_msg = f"Python Bridge Attached. PID: {os.getpid()}"

    if all_exist:
        send_system_json({"type": "success", "msg": f"{init_msg} | Models Found"})
        # 自动静默检查更新
        threading.Thread(
            target=check_update_from_hf, args=(False,), daemon=True
        ).start()
    else:
        send_system_json(
            {
                "type": "warn",
                "msg": f"{init_msg} | Models NOT FOUND. Missing: {missing}",
            }
        )

    # 2. 监听循环
    for line in sys.stdin:
        try:
            if not line.strip():
                continue
            request = json.loads(line)
            action = request.get("action")

            if action == "check-model":
                all_exist, missing = check_all_models_exist()
                if all_exist:
                    send_system_json(
                        {
                            "type": "success",
                            "msg": "Model Found: DeBERTa & MiniLM Ready",
                        }
                    )
                else:
                    send_system_json(
                        {"type": "err", "msg": f"Models Missing: {missing}"}
                    )

            elif action == "check-update":
                threading.Thread(
                    target=check_update_from_hf, args=(True,), daemon=True
                ).start()

            elif action == "start":
                from pipeline_modules import DeviceManager

                global CorpusPipelineClass
                if CorpusPipelineClass is None:
                    send_system_json({"type": "info", "msg": "Loading AI Core..."})
                    try:
                        from pipeline_modules import CorpusPipeline

                        CorpusPipelineClass = CorpusPipeline
                    except ImportError as e:
                        send_system_json(
                            {
                                "type": "err",
                                "msg": f"Import Error:\n{traceback.format_exc()}",
                            }
                        )
                        send_system_json({"type": "sys", "status": "done"})
                        continue

                all_exist, missing = check_all_models_exist()
                if not all_exist:
                    send_system_json({"type": "err", "msg": f"Missing: {missing}"})
                    send_system_json({"type": "sys", "status": "done"})
                    continue

                in_dir = request.get("inputPath")
                out_dir = request.get("outputPath")

                # 从前端请求中获取 recursive 参数 (默认为 False)
                is_recursive = request.get("recursive", False)

                try:
                    send_system_json(
                        {
                            "type": "info",
                            "msg": f"Initializing Pipeline with configs: {MODEL_CONFIGS}",
                        }
                    )
                    pipeline = CorpusPipelineClass(MODEL_CONFIGS)

                    def electron_callback(current, total, message):
                        try:
                            progress = int((current / total) * 100) if total > 0 else 0
                            send_system_json(
                                {"type": "info", "msg": message, "progress": progress}
                            )
                        except:
                            pass

                    send_system_json(
                        {
                            "type": "info",
                            "msg": f"Pipeline Started... (Recursive: {is_recursive})",
                        }
                    )
                    pipeline.process_folder(
                        in_dir,
                        out_dir,
                        recursive=is_recursive,
                        progress_callback=electron_callback,
                    )

                    send_system_json(
                        {
                            "type": "success",
                            "msg": "Task Completed.",
                            "status": "done",
                            "progress": 100,
                            "resultPath": out_dir,
                        }
                    )

                except Exception as e:
                    send_system_json(
                        {
                            "type": "err",
                            "msg": f"Runtime Error:\n{traceback.format_exc()}",
                        }
                    )
                    send_system_json({"type": "sys", "status": "done"})
                finally:
                    if "pipeline" in locals() and pipeline:
                        try:
                            pipeline.dispose()
                            del pipeline
                        except:
                            pass
                    import gc

                    gc.collect()

            elif action == "get-semantic-config":
                try:
                    # 1. 定义默认配置 (作为兜底，防止文件不存在时界面空白)
                    # 必须在这里也写一份，因为 api.py 无法直接读取 pipeline_modules 里的局部变量
                    default_config = {
                        "positive": [
                            "Diplomacy and bilateral relations between countries",
                            "Government official visits and high-level meetings",
                            "Belt and Road Initiative and infrastructure projects",
                            "South China Sea disputes and maritime security",
                            "International trade agreements and economic cooperation",
                            "Chinese state-owned enterprises investment",
                            "Foreign ministry statements and embassies",
                            "Political ideology and party congress",
                        ],
                        "negative": [
                            "Commercial banking awards and financial performance reports",
                            "Retail promotions, shopping, and restaurant food reviews",
                            "Travel holiday packages and tourism advertisements",
                            "Sports match results and athlete news",
                            "Entertainment, celebrity gossip, and movies",
                            "Routine crime reports and local accidents",
                            "Stock market fluctuations and corporate shareholders meeting",
                            "Art exhibitions and cultural performances tickets",
                            "Newspaper publisher notes, editorial disclaimers, and advertising supplements",
                        ],
                    }

                    # 2. 定位文件路径
                    base_dir = CURRENT_DIR

                    possible_paths = [
                        os.path.join(base_dir, "css-interface", "semantic_config.json"),
                        os.path.join(base_dir, "semantic_config.json"),
                    ]

                    target_path = None
                    for p in possible_paths:
                        if os.path.exists(p):
                            target_path = p
                            break

                    # 3. 读取逻辑
                    final_data = default_config  # 先设为默认值

                    if target_path:
                        try:
                            with open(target_path, "r", encoding="utf-8") as f:
                                loaded_data = json.load(f)
                                if loaded_data:  # 确保文件不是空的
                                    final_data = loaded_data
                        except Exception as e:
                            send_system_json(
                                {"type": "err", "msg": f"Config Corrupted: {e}"}
                            )
                    else:
                        # 如果文件完全不存在，自动创建一个 (默认放在 css-interface 下)
                        # 尝试找到存在的文件夹路径
                        folder_path = os.path.join(base_dir, "css-interface")
                        if not os.path.exists(folder_path):
                            folder_path = (
                                base_dir  # 如果 css-interface 文件夹不存在，就存根目录
                            )

                        save_path = os.path.join(folder_path, "semantic_config.json")
                        try:
                            with open(save_path, "w", encoding="utf-8") as f:
                                json.dump(
                                    default_config, f, indent=2, ensure_ascii=False
                                )
                        except:
                            pass

                    # 4. 发送数据给前端
                    send_system_json({"type": "config-data", "data": final_data})

                except Exception as e:
                    send_system_json(
                        {"type": "err", "msg": f"Failed to get config: {e}"}
                    )

            elif action == "save-semantic-config":
                # 保存配置
                try:
                    new_config = request.get("config")

                    base_dir = os.path.dirname(os.path.abspath(__file__))

                    # 优先保存到 css-interface
                    # 如果该文件夹存在，就保存进去；否则保存到当前目录
                    if os.path.exists(os.path.join(base_dir, "css-interface")):
                        save_path = os.path.join(
                            base_dir, "css-interface", "semantic_config.json"
                        )
                    elif os.path.exists(os.path.join(base_dir, "css_interface")):
                        save_path = os.path.join(
                            base_dir, "css_interface", "semantic_config.json"
                        )
                    else:
                        save_path = os.path.join(base_dir, "semantic_config.json")

                    with open(save_path, "w", encoding="utf-8") as f:
                        json.dump(new_config, f, indent=2, ensure_ascii=False)

                    send_system_json(
                        {"type": "success", "msg": "Semantic Rules Saved!"}
                    )
                except Exception as e:
                    send_system_json(
                        {"type": "err", "msg": f"Failed to save config: {e}"}
                    )
            elif action == "get-system-info":
                try:
                    from pipeline_modules import DeviceManager

                    device_str, info = DeviceManager.get_optimal_device()
                    full_path = MODEL_CONFIGS.get("NOISE_CAPTION", "")
                    model_display_name = "Unknown Model"
                    if full_path:
                        try:
                            model_display_name = os.path.relpath(
                                full_path, PROJECT_ROOT
                            )
                        except ValueError:
                            model_display_name = os.path.basename(full_path)

                    send_system_json(
                        {
                            "type": "system-info",
                            "data": {
                                "device": device_str,
                                "details": info,
                                "active_model": model_display_name,
                            },
                        }
                    )
                except Exception as e:
                    send_system_json({"type": "err", "msg": f"SysInfo Error: {e}"})

        except json.JSONDecodeError:
            pass
        except Exception as e:
            send_system_json({"type": "err", "msg": f"Bridge Error: {str(e)}"})


if __name__ == "__main__":
    main()
