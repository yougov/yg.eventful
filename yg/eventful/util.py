import os
import fcntl

def encode_netstring(s):
	return '%d:%s' % (len(s), s.encode('utf-8'))

def encode_many_netstrings(l):
	return ''.join(map(encode_netstring, l))

class NetstringFormatError(Exception): pass

def decode_netstrings(s):
	out = []

	end = len(s)
	run = 0

	while run != end:
		ind = s.find(':', run)
		if ind == -1:
			raise NetstringFormatError, ("Cannot find ':' near byte %d" % run)
		try:
			segl = int(s[run:ind])
		except ValueError:
			raise NetstringFormatError, ("Length segment is not integer near byte %d" % run)

		run = ind + 1
		seg = s[run:run+segl]
		if len(seg) != segl:
			raise NetstringFormatError, \
			("Not enough bytes in netstring to satisfy length near byte %d" % run)
		
		try:
			out.append(seg.decode('utf-8'))
		except:
			raise NetstringFormatError, \
			("Segment body doesn't seem to be UTF-8 near byte %d" % run)
		run += segl
	return out

# from twisted
def set_nonblocking(fd):
	flags = fcntl.fcntl(fd, fcntl.F_GETFL)
	fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def until_concludes(f, *a, **kw):
	while True:
		try:
			return f(*a, **kw)
		except (IOError, OSError), e:
			if e.args[0] == errno.EINTR:
				continue
			raise
