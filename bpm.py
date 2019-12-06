from bpmMiscUtils import (pgrep, SVL, sv, plog, logSval)
import numpy as np

class SIM():
  def __init__(self, bay=0):
    self.bpm  = SVL(pgrep("BpmSim[[]{:d}]$".format(bay))[0])
    try:
       self.fifo = SVL(pgrep("FifoRx$")[0])
    except:
       self.fifo = None
    self.nRx  = self.bpm.get("NumRx")
    self.ch0  = SVL(self.bpm.getPath().findByName("Channels[0]"))
    self.nPZ  = self.ch0.get("NumPolesAndZeros")
    self.nPO  = self.ch0.get("NumPolesOnly")
    self.nP   = self.nPO + self.nPZ
    self.pOrd = self.ch0.get("PolyOrder")

  def drain(self):
    if not self.fifo:
      raise RuntimeError("Implementation has no FIFO")
    return [ self.fifo.get("RxData") for i in range(0, self.fifo.get("SlotsFilled"))]

  def shot(self):
    self.bpm.set("Command","OneShot")
    y = np.array( self.drain(), 'int16' )
    return y

  def getBpm(self):
    return self.bpm

  def getFifo(self):
    return self.fifo

  def fc0(self):
    return self.fc(0);

  def fc(self,ch):
    return sv("Channels[{}]/FilterCoeffs[0-{}]".format(ch,8*self.nP-1),self.bpm.getPath())

  def pc0(self):
    return self.pc(0);

  def pc(self,ch):
    return sv("Channels[{}]/PolyCoeffs[0-{}]".format(ch,6*(self.pOrd+1)*self.nP-1),self.bpm.getPath())

  def setPadded(self, sclv, vals):
    dif = sclv.getNelms() - len(vals)
    if dif < 0:
      print("{}: [{}], length is {}".format(sclv, sclv.getNelms(), len(vals)))
      raise RuntimeError("Too many values for this ScalVal")
    if dif > 0:
      vals=np.concatenate( ( vals, np.zeros(dif, dtype='int32') ) )
    sclv.setVal(vals)
    logSval(sclv, vals)

  def fca(self,fvals,pvals):
    for ch in range(0,self.nRx):
      if not (fvals is None):
        self.setPadded(self.fc(ch), fvals)
      if not (pvals is None):
        self.setPadded(self.pc(ch), pvals)

  def stop(self):
    self.getBpm().set("Command","Halt")

  def start(self):
    self.getBpm().set("Command","Run")

  def fcal(self, linsim):
    ch      = 0
    b       = self.getBpm()
    prevVal = b.get("Command")
    self.stop()
    for chan in linsim:
      if ( ch >= self.nRx ):
        return
      self.setPadded(self.fc(ch), chan.filterCoeffsDL())
      self.setPadded(self.pc(ch), chan.polyCoeffsDL())
      ch = ch + 1
    b.set("Command",prevVal)

def gdaq(idx):
  d = tree.Stream._bufs[idx].copy()
  return d[0:128]

def gbpm(idx):
  d = tree.Stream._bufs[8].copy()
  d = np.reshape(d[4*8:4*8+512],(128,4))
  if idx < 0:
    return d
  else:
    return d[:,idx]
