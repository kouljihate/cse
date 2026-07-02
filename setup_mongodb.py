#!/usr/bin/env python3
"""
Download and set up MongoDB server for testing.
Installs under tests/mongodb/ if not already available.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TESTS_DIR = BASE_DIR / "tests"
MONGODB_DIR = TESTS_DIR / "mongodb"
DATA_DIR = MONGODB_DIR / "data"
LOG_DIR = MONGODB_DIR / "log"
BIN_DIR = MONGODB_DIR / "bin"
CONFIG_PATH = MONGODB_DIR / "mongod.conf"

MONGO_DL_BASE = "https://fastdl.mongodb.org/windows"
VERSIONS_URL = "https://www.mongodb.com/versions.json"


def info(msg):
    print(f"[INFO] {msg}")


def warn(msg):
    print(f"[WARN] {msg}")


def fail(msg):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def check_mongod_in_path():
    return shutil.which("mongod") is not None


def check_local_binaries():
    return (BIN_DIR / "mongod.exe").exists()


def get_latest_version():
    info("Fetching latest MongoDB version ...")
    try:
        req = urllib.request.Request(VERSIONS_URL, headers={"User-Agent": "setup-mongodb/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            versions = json.loads(resp.read().decode())
        current = [v for v in versions if v.get("current") and v.get("production")]
        if current:
            ver = current[0]["version"]
            info(f"Latest production version: {ver}")
            return ver
        versions.sort(key=lambda v: [int(x) for x in v.get("version", "0").split(".")], reverse=True)
        return versions[0]["version"]
    except Exception as e:
        warn(f"Failed to fetch latest version: {e}")
        return "8.0.0"


def download_and_extract(version):
    filename = f"mongodb-windows-x86_64-{version}.zip"
    url = f"{MONGO_DL_BASE}/{filename}"
    dest = MONGODB_DIR / filename

    MONGODB_DIR.mkdir(parents=True, exist_ok=True)

    info(f"Downloading MongoDB {version} ...")
    info(f"  {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "setup-mongodb/1.0"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 8192
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        print(f"\r  Progress: {pct}% ({downloaded // 1048576}MB / {total // 1048576}MB)", end="")
                    else:
                        print(f"\r  Downloaded: {downloaded // 1048576}MB", end="")
                print()
    except urllib.error.HTTPError as e:
        fail(f"Download failed (HTTP {e.code}): {e.reason}")

    info(f"Extracting {filename} ...")
    with zipfile.ZipFile(dest, "r") as zf:
        zf.extractall(MONGODB_DIR)

    extracted = [d for d in MONGODB_DIR.iterdir() if d.is_dir() and d.name.startswith("mongodb-")]
    if extracted:
        src = extracted[0] / "bin"
        if src.exists():
            shutil.copytree(src, BIN_DIR, dirs_exist_ok=True)
        shutil.rmtree(extracted[0])
        info(f"MongoDB binaries extracted to {BIN_DIR}")
    else:
        fail("Could not locate extracted MongoDB binaries")

    dest.unlink()


def create_config():
    config = f"""# MongoDB test configuration
storage:
  dbPath: "{DATA_DIR}"
systemLog:
  destination: file
  path: "{LOG_DIR / 'mongod.log'}"
net:
  bindIp: 127.0.0.1
  port: 27017
"""
    CONFIG_PATH.write_text(config, encoding="utf-8")
    info(f"Config file created: {CONFIG_PATH}")

    start_script = MONGODB_DIR / "start.cmd"
    start_script.write_text(
        f'@echo off\n"{BIN_DIR / "mongod.exe"}" --config "{CONFIG_PATH}"\n',
        encoding="utf-8",
    )
    info(f"Start script created: {start_script}")


def setup_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    info(f"Data directory: {DATA_DIR}")
    info(f"Log directory:  {LOG_DIR}")


def main():
    info(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")

    if check_mongod_in_path():
        mongod_path = shutil.which("mongod")
        info(f"MongoDB already available in PATH: {mongod_path}")
        setup_dirs()
        create_config()
        info("Setup complete!")
        return

    if check_local_binaries():
        info(f"MongoDB binaries found at {BIN_DIR}")
    else:
        info("MongoDB not found — downloading ...")
        version = get_latest_version()
        download_and_extract(version)

    setup_dirs()
    create_config()

    info(f"\n MongoDB setup complete!")
    info(f"   Binary:  {BIN_DIR / 'mongod.exe'}")
    info(f"   Data:    {DATA_DIR}")
    info(f"   Config:  {CONFIG_PATH}")
    info(f"   Start:   {MONGODB_DIR / 'start.cmd'}")
    info("")
    info("Start MongoDB manually:")
    info(f"   {BIN_DIR / 'mongod.exe'} --config \"{CONFIG_PATH}\"")
    info("")
    info("Or run tests/start.cmd")
    info("")
    info("Connect with:  mongosh (or pymongo MongoClient('mongodb://localhost:27017'))")
    info("")


if __name__ == "__main__":
    main()
