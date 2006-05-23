import sys
import time

currentApplication = [None]
(
LOGLVL_DEBUG,
LOGLVL_INFO,
LOGLVL_WARN,
LOGLVL_ERR,
LOGLVL_CRITICAL,
) = range(1,6)

lvlText = {
	LOGLVL_DEBUG : 'debug',
	LOGLVL_INFO : 'info',
	LOGLVL_WARN : 'warn',
	LOGLVL_ERR : 'error',
	LOGLVL_CRITICAL : 'critical',
}
	

class Logger:
	def __init__(self, fd=sys.stdout, verbosity=LOGLVL_WARN):
		self.fdlist = [fd]
		self.level = verbosity
		self.component = None

	def addLog(self, fd):
		self.fdlist.append(fd)

	def _writelogline(self, lvl, message):
		if lvl >= self.level:
			for fd in self.fdlist:
				fd.write('[%s] {%s%s} %s\n' % (time.asctime(), 
										self.component and ('%s:' % self.component) or '',
										lvlText[lvl],
										message))

	debug = lambda s, m: s._writelogline(LOGLVL_DEBUG, m)
	info = lambda s, m: s._writelogline(LOGLVL_INFO, m)
	warn = lambda s, m: s._writelogline(LOGLVL_WARN, m)
	error = lambda s, m: s._writelogline(LOGLVL_ERR, m)
	critical = lambda s, m: s._writelogline(LOGLVL_CRITICAL, m)

	def getSublogger(self, component, verbosity=None):
		copy = Logger(verbosity=verbosity or self.level)
		copy.fdlist = self.fdlist
		copy.component = component
		return copy

def setCurrentApplication(app):
	currentApplication[0] = app

class _currentLogger:
	def __getattr__(self, n):
		return getattr(currentApplication[0].logger, n)

log = _currentLogger()
