import logging
import os
import time
from datetime import datetime
from typing import Optional

from config.config_class import LoggerConfig


def get_logger(name="unnamed", log_dir: str = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s::%(name)s::%(levelname)s] %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_dir is not None:
        file_handler = logging.FileHandler(os.path.join(log_dir, "log.txt"))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_and_create_new_log_dir(root="./logs", prefix="", suffix="", strftime_format="%Y_%m_%d__%H_%M_%S"):
    filename = time.strftime(strftime_format, time.localtime())
    if prefix != "":
        filename = prefix + "_" + filename
    if suffix != "":
        filename = filename + "_" + suffix
    log_dir = os.path.join(root, filename)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def log_command_execution(
    log_config: LoggerConfig,
    command: str,
    user: str,
    status: str,
    result: Optional[str] = None,
):
    """Log command execution"""
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | {user} | {command} | {status} \n"
    if result:
        # Limit result length to avoid large log files
        truncated_result = result[:200] + "..." if len(result) > 200 else result
        log_entry += f"\n | {truncated_result}"

    log_dir = get_and_create_new_log_dir(root=log_config.log_dir, prefix="", suffix="", strftime_format="%Y%m%d")
    logger = get_logger(name=__name__, log_dir=log_dir)
    logger.info(log_entry)

    # Write to dedicated command log file
    with open(f'{log_config.log_dir}/commands_{datetime.now().strftime("%Y%m%d")}.log', "a") as f:
        f.write(log_entry + "\n")


if __name__ == "__main__":
    log_dir = get_and_create_new_log_dir(root="./logs", prefix="test", suffix="")
    logger = get_logger(name="yyy", log_dir=log_dir)
    logger.info("archlinux")
    logger.debug("ubuntu")
