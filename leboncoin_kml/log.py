from easylogger import LoggingClass as _LoggingClass
from leboncoin_kml.config import Config


class LoggingClass(_LoggingClass):
    def __init__(self, config=Config()):
        super(LoggingClass, self).__init__(self.__class__.__name__,
                                           log_file=config.log_file,
                                           log_level_file=config.log_level,
                                           log_level_console=config.log_level,
                                           color_file=False,
                                           color_console=True)
