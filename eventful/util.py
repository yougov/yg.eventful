def encodeNetstring(s):
	return '%d:%s' % (len(s), s.encode('utf-8'))

def encodeManyNetstrings(l):
	return ''.join(map(encodeNetstring, l))

class NetstringFormatError(Exception): pass

def decodeNetstrings(s):
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
