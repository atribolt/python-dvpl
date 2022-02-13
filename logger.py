import logging
import logging.handlers as lhandlers
from datetime import datetime


_log = logging.getLogger('default')

# for release
_log.setLevel(logging.ERROR)
_log.addHandler(lhandlers.RotatingFileHandler(filename='log',
                                              maxBytes=10*1024*1024,
                                              encoding='utf-8',
                                              backupCount=5))
# for debugging
# _log.setLevel(logging.DEBUG)
# _log.addHandler(logging.StreamHandler(stream=sys.stdout))


class Logger:
  def __init__(self, name):
    self.name = name
    
  def __message(self, function, msg):
    time = datetime.now()
    time = time.strftime('%Y.%m.%d $H:%M:%S.%f')
    message = f"{time} [{self.name}] {msg}"
    function(message)
    
  def error(self, msg):
    self.__message(_log.error, msg)
    
  def debug(self, msg):
    self.__message(_log.debug, msg)
    
  def critical(self, msg):
    self.__message(_log.critical, msg)
  
  def info(self, msg):
    self.__message(_log.info, msg)
