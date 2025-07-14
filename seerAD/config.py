from pathlib import Path
import os
import platform

def get_user_data_dir(appname="seerAD") -> Path:
    if platform.system() == "Windows":
        base = os.getenv('APPDATA', Path.home() / "AppData" / "Roaming")
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.getenv('XDG_DATA_HOME', Path.home() / ".local" / "share")
    return Path(base) / appname

ROOT_DIR = Path(__file__).resolve().parent.parent  # package root for code/resources

USER_DATA_DIR = get_user_data_dir()

DATA_DIR = USER_DATA_DIR
LOOT_DIR = USER_DATA_DIR / "loot"
LOGS_DIR = USER_DATA_DIR / "logs"

# Make sure directories exist
for d in [DATA_DIR, LOOT_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

VERSION = "0.1.0"
