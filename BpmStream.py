import pycpsw
import numpy as np
from   loadYaml import LoadYaml

def myOpts():
  return ""

def init():
  l = LoadYaml( myOpts() )
  return l.load()

class BpmStream:
  def __init__(self, streamPath):
    self.strm_ = pycpsw.Stream.create( streamPath )

  @staticmethod
  def bufAlloc(n = 1):
    if 0 >= n:
      n = 1
    buf = np.ndarray( (n,1500), 'int16' )
    buf.fill(0)
    return buf

  def read(self, buf = None, n=0):
    if isinstance( buf, type(None) ):
      buf = bufAlloc(n)
    if n <= 0 or n > len(buf):
      n = len(buf)
    with self.strm_ as f:
      for v in buf[0:n]:
        l = f.read(v)
    return int( l/2 ) # number of int16

  @staticmethod
  def r32(m,o):
    return (m[o+1] << 16) + (m[o] & 0xffff)

  @staticmethod
  def r64(m,o):
    return (BpmStream.r32(m,o+2) << 32) + (BpmStream.r32(m,o) & 0xffffffff)

  @staticmethod
  def parseMsg(msg):
    tmit = BpmStream.r32( msg, 2  )   # tmit computed by firmware
    stat = msg[1] & 0xffff  # status word
    x    = BpmStream.r32( msg, 4  )   # X computed by firmware
    y    = BpmStream.r32( msg, 6  )   # Y computed by firmware
    pid  = BpmStream.r64( msg, 12 )   # pulse ID
    hoff = (((msg[0]>>4) & 0xf) + 1)*4 # Offset where waveform starts
    return pid, stat, tmit, x, y, hoff


  def readWaveform(self):
    buf   = self.bufAlloc()
    nelms = self.read(buf)
    pid, stat, tmit, x, y, hoff = self.parseMsg( buf[0] )
    print("reshaping nelms {}, hoff{}".format(nelms,hoff))
    return np.reshape( buf[0][hoff:nelms], (128, 4) )

  def scn(self):
    buf = self.bufAlloc()
    print("{:>20s} {:>4s} {:>6s} {:>6s} {:>6s}".format("PulseID", "STAT", "TMIT", "X", "Y"))
    with self.strm_ as f:
      while True:
        l     = f.read(buf[0])
        nelms = int(l/2)
        pid, stat, tmit, x, y, hoff = self.parseMsg( buf[0] )
        print("{:20d} {:04x} {:6d} {:6d} {:6d}".format(pid, stat, tmit, x, y))

if __name__ == "__main__":
  r = init()
  s = BpmStream( r.findByName("BPM_A_Stream") )
  s.scn()
