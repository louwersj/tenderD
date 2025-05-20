import os
import time
import json
import signal
import logging
import shutil
import uuid
import requests
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# === Default Configuration Values ===
defaultConfig = {
    "watchDirectory": "/tmp/",
    "doneDirectory": "/tmp/done",
    "downloadDirectory": "/tmp/downloads",
    "scanIntervalSeconds": 5,
    "parallelProcMax": 4
}

# === Globals for Config + Runtime ===
config = defaultConfig.copy()
executor = None
running = True


# === Utility: Print + Log ===
def printAndLog(message):
    timestampedMessage = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}"
    print(timestampedMessage)
    logging.info(message)


# === Config Loading ===
def loadConfig():
    global config
    configPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../conf/config.json"))
    printAndLog(f"[tederD] Attempting to read config from {configPath}")

    if not os.path.exists(configPath):
        printAndLog("[tederD] Config file not found, using defaults.")
        return

    try:
        with open(configPath, "r") as f:
            userConfig = json.load(f)
        if not isinstance(userConfig, dict):
            raise ValueError("Configuration file does not contain a valid JSON object")

        config.update({k: userConfig[k] for k in defaultConfig if k in userConfig})
        printAndLog("[tederD] Configuration loaded successfully.")
    except Exception as e:
        printAndLog(f"[tederD] Failed to load configuration, using defaults: {e}")


# === Signal Handler ===
def shutdownHandler(signum, frame):
    global running
    printAndLog(f"Received signal {signum}, shutting down gracefully...")
    running = False
    if executor:
        printAndLog("[tederD] Shutting down executor")
        executor.shutdown(wait=True, cancel_futures=True)
        printAndLog("[tederD] Executor shut down")


# === Handlers ===
def instructionHandler(filePath):
    try:
        with open(filePath, "r") as f:
            data = json.load(f)

        fileId = data.get("id", "unknown")
        printAndLog(f"[tederD] Handling instruction file: {filePath}")
        printAndLog(f"[tederD] Extracted data: {data}")

        task = data.get("task")
        if not task:
            data["status"] = "error"
        elif task == "download":
            downloadHandler(data)
        elif task == "analyze":
            analyzeHandler(data)
        else:
            data["status"] = "error"
    except Exception as e:
        printAndLog(f"[tederD] Error handling file {filePath}: {e}")
    finally:
        # After handling, move file to doneDirectory with .json extension
        originalName = Path(filePath).name.replace(".json.lock", ".json")
        destPath = os.path.join(config["doneDirectory"], originalName)
        shutil.move(filePath, destPath)
        printAndLog(f"[tederD] Moved processed file to {destPath}")


def downloadHandler(data):
    try:
        url = data.get("url")
        if not url:
            raise ValueError("Missing 'url' in data")

        provided_id = data.get("id")
        if not provided_id:
            raise ValueError("Missing 'id' in data")

        # Determine extension and full download path
        extension = os.path.splitext(url)[1] or ".bin"
        download_file_name = f"{uuid.uuid4()}{extension}"
        full_download_path = os.path.join(config["downloadDirectory"], download_file_name)

        printAndLog(f"[tederD] Downloading from {url} to {full_download_path}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(full_download_path, "wb") as f:
            f.write(response.content)

        # Prepare new instruction for analysis
        newData = {
            "id": provided_id,
            "task": "analyze",
            "url": url,
            "downloadedFile": full_download_path
        }

        new_instruction_filename = f"{uuid.uuid4()}.json"
        new_instruction_path = os.path.join(config["watchDirectory"], new_instruction_filename)

        with open(new_instruction_path, "w") as f:
            json.dump(newData, f)

        printAndLog(f"[tederD] Download successful, new task queued: {new_instruction_path}")
    except Exception as e:
        printAndLog(f"[tederD] Error in downloadHandler: {e}")
        

def analyzeHandler(data):
    downloadedFile = data.get("downloadedFile", "unknown")
    printAndLog(f"[tederD] Analyzing file: {downloadedFile}")
    # Placeholder for analysis logic
    time.sleep(2)
    printAndLog(f"[tederD] Analysis complete for: {downloadedFile}")


# === Logging Setup (after config load for flexibility) ===
def setupLogging():
    logFilePath = "/tmp/daemon_log.txt"  # This could be made configurable too
    logging.basicConfig(filename=logFilePath, level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")


# === Main Function ===
def main():
    global executor
    loadConfig()
    setupLogging()
    printAndLog("[tederD] Starting tederD daemon...")

    os.makedirs(config["doneDirectory"], exist_ok=True)
    os.makedirs(config["downloadDirectory"], exist_ok=True)

    signal.signal(signal.SIGINT, shutdownHandler)
    signal.signal(signal.SIGTERM, shutdownHandler)

    executor = ProcessPoolExecutor(max_workers=config["parallelProcMax"])

    try:
        while running:
            jsonFiles = sorted(
                [f for f in os.listdir(config["watchDirectory"]) if f.endswith(".json")],
                key=lambda f: os.path.getctime(os.path.join(config["watchDirectory"], f))
            )

            for fileName in jsonFiles:
                jsonPath = os.path.join(config["watchDirectory"], fileName)
                lockedPath = jsonPath + ".lock"

                # Skip if file is already locked
                if os.path.exists(lockedPath):
                    continue

                try:
                    os.rename(jsonPath, lockedPath)
                    printAndLog(f"[tederD] Picked up file {jsonPath}")
                    executor.submit(instructionHandler, lockedPath)
                except Exception as e:
                    printAndLog(f"[tederD] Could not lock file {jsonPath}: {e}")

            time.sleep(config["scanIntervalSeconds"])
    finally:
        printAndLog("[tederD] Shutting down executor.")
        executor.shutdown(wait=False, cancel_futures=True)
        printAndLog("[tederD] Shutdown complete.")


if __name__ == "__main__":
    main()
