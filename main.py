import logging
import os

from bot import bot

log_level = logging.getLevelNamesMapping().get(os.getenv("log_level", "INFO"))
if not log_level:
    log_level = logging.INFO
logging.basicConfig(level=log_level)

logger = logging.getLogger(__name__)

try:
    # Create a cgroup for the bot, if one doesn't already exist
    CGROUP_DIR = "/sys/fs/cgroup/diplomacy_gm"
    os.makedirs(CGROUP_DIR, exist_ok=True)

    # Set the cgroup's memory limit to 1GB (arbitrary choice)
    with open(f"{CGROUP_DIR}/memory.max", "w") as f:
        f.write("1G")

    # Add this process to the cgroup so it's limited by the memory limit
    with open(f"{CGROUP_DIR}/cgroup.procs", "w") as f:
        f.write(str(os.getpid()))
except Exception as e:
    # No big deal if we can't create a cgroup for the bot; swallow the exception
    # Also, cgroups don't exist on macos/windows, so this will fail there deterministically
    logger.warning(f"Failed to add the bot to a cgroup with limited memory use, got exception {e}")

bot.run()
