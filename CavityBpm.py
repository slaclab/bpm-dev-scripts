from   bpmMiscUtils import (pgrep, SVL, sv)
import numpy as np
from   loadYaml import LoadYaml
import pathGrep

def myOpts():
  return ""

def init():
  l = LoadYaml( myOpts() )
  return l.load()

class CavityBpm:
  def __init__(self, path):
    self._path  = path
    self._uCplx = sv("ComplexU", path)
    self._vCplx = sv("ComplexV", path)

  def trunc(self, v):
    if ( v >= 2**17 ):
        return 2**17 - 1
    return v

  def flt2i17(self, v):
    return self.trunc( int( np.round( v * 2.0**17 ) ))

  def setDFT(self, fi, ch):
    ch = self._path.findByName("DFTChannels[{:d}]".format(ch))
    sv("Coeff2C1", ch).setVal(self.flt2i17(np.cos(1*fi)))
    sv("Coeff2S1", ch).setVal(self.flt2i17(np.sin(1*fi)))
    sv("Coeff2C2", ch).setVal(self.flt2i17(np.cos(2*fi)))
    sv("Coeff2C4", ch).setVal(self.flt2i17(np.cos(4*fi)))

  def clearDFT(self, ch):
    sv("Coeff2C1", ch).setVal( 0 )
    sv("Coeff2S1", ch).setVal( 0 )
    sv("Coeff2C2", ch).setVal( 0 )
    sv("Coeff2C4", ch).setVal( 0 )

  def setWeightReal(self, ch, val=1.0):
    ch = self._path.findByName("DFTChannels[{:d}]".format(ch))
    sv("CoeffHU_Im", ch).setVal( 0 )
    sv("CoeffHU_Re", ch).setVal( self.flt2i17( val ) )
    sv("CoeffHV_Im", ch).setVal( 0 )
    sv("CoeffHV_Re", ch).setVal( self.flt2i17( val ) )

  def csgn(self, x):
    x = x & 0xffff;
    if x >= 0x8000:
        return x - 0x10000
    else:
        return x

  def cplx(self,x):
    return self.csgn(x>>16) + 1j*self.csgn(x)

  def cabs(self, x):
    return abs(self.cplx(x))

  def getCplxU(self):
    return self.cplx( self._uCplx.getVal() )

  def getCplxV(self):
    return self.cplx( self._vCplx.getVal() )


  def scanDFT(self, ch=0):
    nsmpls = sv("NumSamples", self._path).getVal() + 1;
    resr   = sv("DFTDiagChannels[{:d}]/DFT_R".format(ch), self._path)
    resu   = sv("DFTDiagChannels[{:d}]/DFT_U".format(ch), self._path)
    resv   = sv("DFTDiagChannels[{:d}]/DFT_V".format(ch), self._path)
    R = list()
    U = list()
    V = list()
    raw = list()
    self.setWeightReal(ch)
    sv("DFTScaleR", self._path).setVal(32768)
    sv("DFTScaleU", self._path).setVal(32768)
    sv("DFTScaleV", self._path).setVal(32768)
    for i in range(0,nsmpls):
      self.setDFT(2*np.pi*i/nsmpls, ch)
      raw.append( self.cplx( resr.getVal() ) )
      R.append( self.cabs( resr.getVal() ) )
      U.append( self.cabs( resu.getVal() ) )
      V.append( self.cabs( resv.getVal() ) )
    return (U,V,R,raw)

defnam="/mmio/AppTop/AppCore/AmcBay1/Bpm"

if __name__ == "__main__":
  r = init();
  pg = pathGrep.PathGrep( r, asPath=True )
  cav = CavityBpm( pg("AmcBay1/Bpm$")[0] )
