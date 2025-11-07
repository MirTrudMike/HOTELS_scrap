from loguru import logger
import os
from functions.file_functions import BASE_DIR


def setup_loguru():
    # Основной логгер (INFO и выше)
    logger.add(
        f"{os.path.join(BASE_DIR, '..', 'logging', 'logs.log')}",
        rotation="3 MB",
        level="INFO",
        compression="zip",
        retention="90 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name: <35} | {message}",
        backtrace=False,  # Отключает показ полного traceback
        diagnose=False,  # Убирает избыточную диагностику
    )

    # Дополнительный логгер для ошибок (ERROR и выше)
    logger.add(
        f"{os.path.join(BASE_DIR, '..', 'logging', 'errors.log')}",
        rotation="2 MB",  # Ротация раз в месяц
        level="ERROR",  # Только ошибки и выше
        compression="zip",  # Сжатие старых файлов
        retention="6 months",  # Храним логи ошибок 6 месяцев
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name: <35} | {message}",
        backtrace=False,  # Отключает показ полного traceback
        diagnose=False,  # Убирает избыточную диагностику
    )

    # # Перехват стандартных логов (например, от aiogram)
    # class InterceptHandler(logging.Handler):
    #     def emit(self, record):
    #         # Получаем логгер Loguru
    #         loguru_logger = logger.bind(request_id=None)
    #         loguru_logger.opt(
    #             depth=6, exception=record.exc_info
    #         ).log(record.levelname, record.getMessage())
    #
    # # Настраиваем стандартный логгер для перенаправления в Loguru
    # logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)
    # logging.getLogger("aiogram").setLevel(logging.INFO)

    return logger
