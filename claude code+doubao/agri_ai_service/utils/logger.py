"""
统一日志系统配置
提供全局日志管理功能
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


class LoggerManager:
    """日志管理器 - 单例模式"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.loggers = {}

        # Windows GBK 控制台无法编码 emoji，设置为 replace 避免崩溃
        if sys.platform == "win32":
            try:
                sys.stdout.reconfigure(errors='replace')
            except Exception:
                pass
            try:
                sys.stderr.reconfigure(errors='replace')
            except Exception:
                pass

        self._setup_base_config()

    def _setup_base_config(self):
        """配置基础日志格式"""
        # 日志目录
        self.log_dir = Path(__file__).parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)

        # 标准格式
        self.standard_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 详细格式（用于文件）
        self.detailed_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def get_logger(
        self,
        name: str = "agri_ai",
        level: int = logging.INFO,
        log_to_file: bool = True,
        log_to_console: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> logging.Logger:
        """
        获取或创建日志记录器

        Args:
            name: 日志记录器名称
            level: 日志级别
            log_to_file: 是否记录到文件
            log_to_console: 是否输出到控制台
            max_bytes: 单个日志文件最大大小
            backup_count: 保留的备份文件数量

        Returns:
            配置好的Logger实例
        """
        if name in self.loggers:
            return self.loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 避免重复添加handler
        if logger.handlers:
            self.loggers[name] = logger
            return logger

        # 控制台处理器
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(self.standard_format)
            logger.addHandler(console_handler)

        # 文件处理器 - 按大小轮转
        if log_to_file:
            # 通用日志文件
            general_log = self.log_dir / f"{name}.log"
            file_handler = RotatingFileHandler(
                general_log,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(self.detailed_format)
            logger.addHandler(file_handler)

            # 错误日志文件（单独记录ERROR及以上）
            error_log = self.log_dir / f"{name}_error.log"
            error_handler = RotatingFileHandler(
                error_log,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(self.detailed_format)
            logger.addHandler(error_handler)

        # 防止日志传播到根logger
        logger.propagate = False

        self.loggers[name] = logger
        return logger

    def setup_application_logging(self, debug: bool = False):
        """
        设置应用级别的日志配置

        Args:
            debug: 是否启用调试模式
        """
        level = logging.DEBUG if debug else logging.INFO

        # 主应用日志
        app_logger = self.get_logger("agri_ai", level=level)

        # 各模块专用日志
        self.get_logger("agri_ai.api", level=level)
        self.get_logger("agri_ai.tools", level=level)
        self.get_logger("agri_ai.vector_db", level=level)
        self.get_logger("agri_ai.llm", level=level)
        self.get_logger("agri_ai.image_recognition", level=level)

        app_logger.info("=" * 60)
        app_logger.info("农业智能体日志系统初始化完成")
        app_logger.info(f"日志级别: {'DEBUG' if debug else 'INFO'}")
        app_logger.info(f"日志目录: {self.log_dir.absolute()}")
        app_logger.info("=" * 60)

        return app_logger


# 全局日志管理器实例
logger_manager = LoggerManager()


def get_logger(name: str = "agri_ai") -> logging.Logger:
    """
    便捷函数：获取日志记录器

    Usage:
        from utils.logger import get_logger
        logger = get_logger("my_module")
        logger.info("这是一条日志")
    """
    return logger_manager.get_logger(name)


def init_app_logging(debug: bool = False) -> logging.Logger:
    """
    初始化应用日志系统

    Usage:
        from utils.logger import init_app_logging
        logger = init_app_logging(debug=True)
    """
    return logger_manager.setup_application_logging(debug=debug)
