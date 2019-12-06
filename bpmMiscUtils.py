#!/usr/bin/python3 -i
import pycpsw
import yaml_cpp
import glob
import math
import pathGrep
import numpy    as np
import matplotlib
from   loadYaml import LoadYaml

matplotlib.use("Qt4Agg")

import matplotlib.pyplot as plt;

plt.ion()

_logFile = None

def logOn(fnam):
  global _logFile
  _logFile = open(fnam,"w")

def logOff():
  global _logFile
  _logFile.close()
  _logFile = None

def logIsOn():
  return None != _logFile


def plog(*args):
  if None != _logFile:
    print(*args,file=_logFile)

def logSval(sv, vals, fromIdx = None, toIdx = None):
  if not logIsOn():
    return
  p       = sv.getPath()
  if np.isscalar(vals):
    vals = [ vals ]
  tailFrom = p.getTailFrom()
  tailTo   = p.getTailTo()

  if None == fromIdx:
    fromIdx = 0
  if None == toIdx:
    toIdx   = tailTo

  fromIdx   = tailFrom + fromIdx
  toIdx     = tailFrom + toIdx

  if fromIdx == tailFrom and (toIdx == tailTo or toIdx == fromIdx):
    #use unmodified path (can handle higher-dimensional arrays)
    if 1 == len(vals):
      plog("- {}: !<value> {}".format(p, vals[0]))
    else:
      plog("- {}:".format(p))
      for val in vals:
        plog("  - {}".format(val))
  else:
    tail    = p.up()
    if fromIdx == toIdx:
      plog("- {}/{}[{:d}]: !<value>{}".format(p,tail.getName(),fromIdx,val))
    else:
      if np.isscalar(vals):
        plog("- {}/{}[{:d}-{:d}]: !<value>{}".format(p,tail.getName(), fromIdx, toIdx, vals))
      else:
        plog("- {}/{}[{:d}-{:d}]:".format(p,tail.getName(),fromIdx,toIdx))
        for val in vals:
          plog("  - {}".format(val))


def pgrep(patt):
  return pg(patt)

def root():
  return r

# find leaf (matches <patt>$ or patt[...]$ )
def pgrepl(patt):
  return pg(patt+"([[][^]]+]){0,1}$")

class SVCOM(pycpsw.ScalVal):
  def __init__(self, comm):
    self.comm_ = comm

  def getName(self):
    return self.comm_.getName()

  def getDescription(self):
    return self.comm_.getDescription()

  def getVal(self):
    print("This is a command -- cannot GetVal")
    return None

  def setVal(self, val):
    self.comm_.execute()
    plog("- {}: !<value> exec", self.comm_.getPath())

def sv(p,n):
  if p != None:
    p = n.findByName(p)
  else:
    p = n
  try:
    return pycpsw.ScalVal.create(p)
  except pycpsw.InterfaceNotImplementedError:
    try:
      return pycpsw.ScalVal_RO.create(p)
    except pycpsw.InterfaceNotImplementedError:
      try:
        comm = pycpsw.Command.create(p)
        print("Found a command: {} -- creating fake ScalVal".format( comm.getName()) )
        return SVCOM( comm )
      except pycpsw.InterfaceNotImplementedError:
        print( "No interface for {} -- skipping".format(p) )

# expand all array elements in a path
def pexpand(p,l=['']):
  if p.empty():
    return [ p.findByName(n) for n in l ]
  els = p.getNelms()
  fro = p.getTailFrom()
  to  = p.getTailTo()
  ch = p.up()
  nl = []
  for i in range(fro, to+1):
    pre = '{}[{}]/'.format(ch.getName(),i)
    for k in l:
      nl.append( pre + k )
  return pexpand(p, nl)

def svp(patt,n):
  l = list()
  for el in pathGrep.PathGrep(n)(patt):
    l.append(sv(el,n))
  return l

def lconf(cf):
  r.findByName("mmio").loadConfigFromYamlFile(cf)

class SVL:
  def __init__(self, path):
    try:
      path.tail()
    except AttributeError:
      path = r.findByName(path)
    self.svcont_ = svc(path)
    self.path_   = path
    self.maxl_   = 0
    for (k,i) in self.svcont_.items():
      l = len( k )
      if l > self.maxl_:
        self.maxl_ = l

  def dump(self):
    for (k,i) in self.svcont_.items():
      v = i.getVal()
      if None == v:
        continue
      print( "{:{w}}: ".format( k, w=self.maxl_ ), end='' )
      if isinstance(v, str):
        print( " {}".format( v ) )
        continue
      try:
        it = iter(v)
        el = next( it )
        if isinstance(el, str):
          fmt="{}"
        else:
          fmt="{:8x}"
        print("[", end='')
        print(fmt.format( el ), end='')
        for el in it:
          print(", ", end='')
          print(fmt.format( el ), end='')
        print("]")
      except TypeError:
        fmt = " {:8x}"
        print( fmt.format( v ) )
      except StopIteration: #empty list
        pass

  def dumpn(self):
    for (k,i) in self.svcont_.items():
      print( k )

  def elm(self, name):
    return self.svcont_[name]

  def get(self, name):
    return self.svcont_[name].getVal()

  def set(self, name, val):
    sv = self.svcont_[name]
    if np.isscalar(val):
      sv.setVal(val)
      logSval(sv, val)
    else:
      # don't slice if we have an exact fit --
      # (might be a multi-dimensional array which
      # we wouldn't want to slice)
      if ( len(val) == sv.getNelms() ):
        sv.setVal(val)
        logSval(sv, val)
      else:
        sv.setVal(val,fromIdx=0,toIdx=len(val)-1)
        logSval(sv, val, 0, len(val)-1)

  def getPath(self):
    return self.path_

def svc(path):
  chldn = path.tail().isHub().getChildren()
  svs   = dict()
  for ch in chldn:
    svs[ch.getName()] = sv( ch.getName(), path )
  return svs

def bsadump():
  bsa = pg("BsaWaveformEngine")

def genExp(ns):
  return [ math.exp(-float(x)*6.5/ns)*math.cos(math.pi*25.6/ns*x) for x in range(0,ns)]

def setDepth(ns):
  nw = (ns + 1)/2
  if daq.get("PacketHeaderEn") == 'Enabled':
    nw = nw + 14
  daq.set("DataBufferSize", nw)
  bsa.set("EndAddr", [sa + nw*4 for sa in bsa.get("StartAddr")])

def readStream(p):
  b = np.empty(16384,'int16')
  b.fill(0)
  s = pycpsw.Stream.create(p)
  with s as f:
    n = f.read(b)
  return (b, n)

def bpmMiscUtilsInit(otherOpts=""):
  global r
  global pg
  r  = LoadYaml(otherOpts).load()
  pg = pathGrep.PathGrep( r )

if __name__ == "__main__":
  bpmMiscUtilsInit()
  daq=[ SVL( p ) for p in pg( "DaqMuxV2[^/]*$")              ]
  bsa=[ SVL( p ) for p in pg( "WaveformEngineBuffers[^/]*$") ]
  #tim=[ SVL( p ) for p in pexpand(r + "/mmio/DigFpga/ApplicationCore/LclsMrTimingTriggerPulse") ]
  print( bytearray(svp("BuildStamp",r)[0].getVal()).decode("ascii") )
