from logging import DEBUG

from attr import dataclass


@dataclass
class Config(object):
    log_level = DEBUG
    log_file=None
