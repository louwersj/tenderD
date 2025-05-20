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

# === Configuration ===
watchDirectory = "/tmp/"
doneDirectory = "/tmp/done"
downloadDirectory = "/tmp/downloads"
scanIntervalSeconds = 5
parallelProcMax = 4  # Max number of parallel processes

# === Logging Setup ===
logFilePath = "/tmp/daemon_log.txt"
logging.basicConfig(filename=logFilePath, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

# === Globals ===
executor = None
running = True


# === Utility: Print + Log ===
def printAndLog(message):
    timestampedMessage = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}"
    print(timestampedMessage)
    logging.info(message)


# === Signal Handler ===
def shutdownHandler(signum, frame):
    global running
    printAndLog(f"Received signal {signum}, shutting down gracefully...")
    running = False
    if executor:
        executor.shutdown(wait=True)


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
        destPath = os.path.join(doneDirectory, originalName)
        shutil.move(filePath, destPath)
        printAndLog(f"[tederD] Moved processed file to {destPath}")


def downloadHandler(data):
    try:
        url = data.get("url")
        if not url:
            raise ValueError("Missing 'url' in data")

        extension = os.path.splitext(url)[1] or ".bin"
        fileName = f"{uuid.uuid4()}{extension}"
        fullPath = os.path.join(downloadDirectory, fileName)

        printAndLog(f"[tederD] Downloading from {url} to {fullPath}")
        response = requests.get(url)
        response.raise_for_status()

        with open(fullPath, "wb") as f:
            f.write(response.content)

        # Create new instruction for analysis
        newData = {
            "id": str(uuid.uuid4()),
            "task": "analyze",
            "downloadedFile": fullPath
        }
        newFilePath = os.path.join(watchDirectory, f"{newData['id']}.json")
        with open(newFilePath, "w") as f:
            json.dump(newData, f)

        printAndLog(f"[tederD] Download successful, new task queued: {newFilePath}")
    except Exception as e:
        printAndLog(f"[tederD] Error in downloadHandler: {e}")


def analyzeHandler(data):
    downloadedFile = data.get("downloadedFile", "unknown")
    printAndLog(f"[tederD] Analyzing file: {downloadedFile}")
    # Placeholder for analysis logic
    time.sleep(2)
    printAndLog(f"[tederD] Analysis complete for: {downloadedFile}")


# === Main Function ===
def main():
    global executor
    printAndLog("[tederD] Starting tederD daemon...")

    os.makedirs(doneDirectory, exist_ok=True)
    os.makedirs(downloadDirectory, exist_ok=True)

    signal.signal(signal.SIGINT, shutdownHandler)
    signal.signal(signal.SIGTERM, shutdownHandler)

    executor = ProcessPoolExecutor(max_workers=parallelProcMax)

    try:
        while running:
            jsonFiles = sorted(
                [f for f in os.listdir(watchDirectory) if f.endswith(".json")],
                key=lambda f: os.path.getctime(os.path.join(watchDirectory, f))
            )

            for fileName in jsonFiles:
                jsonPath = os.path.join(watchDirectory, fileName)
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

            time.sleep(scanIntervalSeconds)
    finally:
        executor.shutdown(wait=True)
        printAndLog("[tederD] Shutdown complete.")


if __name__ == "__main__":
    main()
