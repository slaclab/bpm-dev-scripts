#!/usr/bin/python3 -i

#@ This file is part of BPM Simulator. It is subject to the license terms in
#@ the LICENSE.txt file found in the top-level directory of this distribution and
#@ at https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. No part of
#@ BPM Simulator, including this file, may be copied, modified, propagated, or
#@ distributed except according to the terms contained in the LICENSE.txt file.

import numpy             as np;
import scipy.signal      as sig;
import matplotlib.pyplot as plt;

# real or complex first-order system
class firstOrderSys:
  def __init__(self, rp, polyOrder = -1):
    self.r  = rp[0]
    self.p  = rp[1]
    p3      = self.p**3
    self.B1 = 2.0*np.real(p3)
    self.B0 = -np.abs(p3)**2
    # The zero-canceling polynomial has poles at 'p'
    # as well as p*exp(j 2pi/3), p*exp(-j 2pi/3)
    cc      = np.exp(2.0j*np.pi/3.0)
    Nc      = np.poly1d( [self.p*cc, self.p*np.conj(cc)], r=True )
    # residue * pole-canceling polynomial
    # coefficients of Numerator N are in 'poly1d' order,
    # i.e., highest power first.
    self.N  = Nc*self.r
    self.ord= polyOrder;
    self.dor= 4 # default order

  def getB1(self):
    return self.B1

  def getB0(self):
    return self.B0

  # Numerator * time-lag by 'to'
  def applyLag(self, to, polyn):
    # 'p' is already in the digital domain;
    return np.outer( self.p**to, polyn )

  # Real part
  #       N/2        conj(N)/2
  #  = --------  +  -----------
  #    z^3 - P      z^3 - conj(P)
  #
  # --> Real{ N * (z^3 - conj(P)) }
  def numer(self, to = 0.):
    return 2.*np.real( self.applyLag(to, np.polymul( self.N, [1.,0.,0.,-np.conj(self.p**3)] ) ))

  def denom(self):
    # 'signal/poly1d' coefficient layout (highest order first)
    return np.array([1.,0.,0.,-self.B1,0.,0.,-self.B0])

  # coefficients; polynomial approximation
  # of numerator N(to):
  #
  #  N(to) = e5(to) z^5 + e4(to) * z^4 .. + e0(to)
  #
  # with ei(to) = sum( cij t^(order-j), j=0..order )
  #
  # The coefficients are returned as a double array:
  #
  # - rows are approximation-polynomials for the numerator
  #
  #   [ [ a00 , a01, a02, ... ],
  #       a10 , a11, a12, ... ],
  #       ...
  #
  # Computes to
  #
  #  z^(M  )*( a00 x^N + a01 x^(N-1) + ... a0N )
  #  z^(M-1)*( a10 x^N + a11 x^(N-1) + ... a1N )
  #      ...
  #  1      *( aM0 x^N + aM1 x^(N-1) + ... aMN )
  #
  def polyCoeffs(self, order = -1):
    # use chebyshev approximation
    if ( self.ord >= 0 and (order < 0 or order == self.ord) ):
      return self.pc
    if (order < 0):
      order = self.dor;
    # simulator uses x = {-1..1} = 2*t - 1 (t=0..1)
    x     = np.linspace(-1.,1.,100)
    t     = (x+1)/2.
    tab   = self.numer( t )
    coefs = list()
    for col in tab.transpose():
      cheb = np.polynomial.Chebyshev.fit(x, col, order)
      # convert to 'normal' polynomial -- this is numerically
      # not optimal for evaluation but the firmware does it
      # this way (easier to implement horner than clenshaw).
      # And it's not a big deal for small order and well-behaved
      # functions.
      # convert to 'alternate' polynomial representation
      # which is used by numpy.signal :-(
      coefs.append( cheb.convert( kind = np.polynomial.Polynomial ).coef[::-1] )
    self.ord = order
    self.pc  = np.array(coefs)
    # coefficients are now in 'signal/poly1d' layout
    # (highest power first)
    return self.pc

  # approximation of numer() in same layout
  def numerApprox(self, to = 0.):
    coef = self.polyCoeffs()
    tab  = list()
    x    = 2.0*to - 1.;
    for coef in coef:
      tab.append( np.polyval(coef, x) )
    return np.array(tab).transpose()

  def dump(self):
    print("***************************")
    print("Complex first order system:")
    print("***************************")
    print("{}".format(self.r))
    print("-------------------------")
    print("z - {}".format(self.p))
    print()

class LinSys:
  # Input: **analog** transfer function b(s)/a(s) with s normalized
  #        to the sampling frequency fs!
  #
  def __init__(self, b, a, Ts=1.):
    # multiple roots are not supported
    if ( np.any( sig.unique_roots( np.roots(a) )[1] > 1 ) ):
      raise("Roots with multiplicity > 1 not supported")
    self.b = b;
    self.a = a;

    # Partial Fraction Decomposition
    (r, p, k) = sig.residue(b,a)
    if ( k != 0. ):
      raise("System with direct term not supported ATM")


    # roots in half-plane with imag-part >= 0
    posIP   = np.imag(p) >= 0.0
    r       = r[posIP]
    p       = p[posIP]
	# going into the discrete domain
    P       = np.exp(p*Ts)
    self.PS = list()
    for rp in zip(r,P):
      self.PS.append( firstOrderSys(rp) )

    # must make sure polynomial computation doesn't overflow
    # NOTE: if there are multiple channels then all must be normalized
    #       by the *same* number

    maxResp = self.maxPolyResponse()
    if self.maxPolyResponse() > 1.0:
      raise RuntimeError("Polynomial too large (would overflow); reduce numerator by", maxResp)

  def get(self):
    return self.PS

  def getBA(self):
    return (self.b.copy(), self.a.copy())

  def getImpulseResponse(self):
    return sig.impulse( self.getBA() )

  def dump(self):
    print("Parallel second order systems: {}".format(len(self.PS)))
    for ps in self.PS:
      ps.dump()

  # Downloadable poly coeffs (list of 18-bit integers)
  def polyCoeffsDL(self, order=-1):
    # simulator needs coefficients in a different layout:
    #     [ aMN     a(M-1)N   aM(N-1) a(M-1)(N-1) .. aM0 a(M-1)0,
    #       a(M-1)N a(M-2)N   ...                                ]
    #
    allCoeffs = []
    for scndOrderSys in self.get():
      coeffs = scndOrderSys.polyCoeffs(order)
      allCoeffs.append( coeffs )

    allCoeffs = np.concatenate(allCoeffs)

    # then we might have to pad with zeroes since the simulator
    # always computes pairs of approximations
    if len(allCoeffs) % 2 != 0:
      allCoeffs = np.append( allCoeffs, np.zeros( (1,len(allCoeffs[0])) ), 0 )

    # next we need to rearrange to interleave pairs:
    allCoeffs = [ allCoeffs[i:i+2].transpose().flatten() for i in range(0,len(allCoeffs),2) ]

    # concatenate this list together, round and convert...
    return np.array( np.round( 2**17 * np.concatenate(allCoeffs) ), 'int32' )

  # Downloadable filter coeffs (list of 18-bit integers)
  # (need to invert the ordering of the numerator; highest-lag
  # is at lowest address)
  # Note that the 'B1' coefficient is scaled differently in the
  # simulator; the valid range covers 0..2! and therefore B2
  # is normalized to 2^16 instead of 2^17.
  def filterCoeffsDL(self):
    allCoeffs = np.concatenate( [ np.append(c.numer()[0][::-1], [c.getB0(), c.getB1()/2]) for c in self.get() ] )
    allCoeffs = np.round( 2**17 * allCoeffs.flatten() )
    return np.array( allCoeffs, 'int32' )

  def maxPolyCoeff(self):
    return np.max( np.abs( [ c.polyCoeffs() for c in self.get() ] ) )

  # a bound for the value the polynomial approximation
  # can assume over x=-1..1. This is the sum of the absolute
  # value of the coefficients.
  def maxPolyResponse(self):
    # sum absolute value over all columns
    return np.max( [ np.sum( np.abs( c.polyCoeffs() ), 1 ) for c in self.get() ] )

  @staticmethod
  def create(N,fc,bw):
    [b,a]=sig.iirfilter(N,[fc-bw/2,fc+bw/2],analog=True)

    try:
      lsys=LinSys( b,a )
    except RuntimeError as e:
      print("Normalized numerator dividing by {}!".format(e.args[1]))
      b    = b/e.args[1]
      lsys = LinSys(b,a)
    return lsys

def mkResonator(fo,Q):
  wo = 2*np.pi*fo
  b  =    [wo/Q,     0]
  a  = [1, wo/Q, wo**2]
  return (b,a)

def mkCavitySystem(fo_r, Q_r, fo_f, bw_f, ord_f=4, nsys=4, tol_fo_f=0.0, tol_fo_r=0.01):
  return mkSystem(fo_r, Q_r, fo_f, bw_f, ord_f, nsys, tol_fo_f, tol_fo_r)

def mkStriplineSystem(fo_f, bw_f, ord_f=4, nsys=4, tol_fo_f=0.01):
  return mkSystem(0.0, 0.0, fo_f, bw_f, ord_f, nsys, tol_fo_f)


def mkSystem(fo_r, Q_r, fo_f, bw_f, ord_f=5, nsys = 4, tol_fo_f=0.0, tol_fo_r=0.0):

  if ( abs(tol_fo_f) > 0.05 ):
    raise RuntimeError("-.05 < tol_fo_f < +.05")
  if ( abs(tol_fo_r) > 0.05 ):
    raise RuntimeError("-.05 < tol_fo_r < +.05")

  if isinstance(fo_r,(tuple,list)):
    nsys = len(fo_r)
  else:
    fo_r = [fo_r for i in range(nsys)]
    Q_r  = [Q_r  for i in range(nsys)]

  lsys_list = []

  for i in range(nsys):
    fo_f_i = fo_f*(1.0 +  tol_fo_f*np.random.randn())
    fo_r_i = fo_r[i]*(1.0 +  tol_fo_r*np.random.randn())
    [bf,af] = sig.iirfilter(ord_f, 2*np.pi*np.array([fo_f_i-bw_f/2,fo_f_i+bw_f/2]), rp=0.5, ftype='cheby1', analog=True)
    if fo_r[i] > 0.0:
      [br,ar] = mkResonator(fo_r_i, Q_r[i])
      bsys = np.polymul(br,bf)
      asys = np.polymul(ar,af)
    else:
      bsys = bf
      asys = af
    try:
      lsys=LinSys( bsys,asys )
    except RuntimeError as e:
      norm = e.args[1]*1.001
      print("Normalized numerator dividing by {}!".format(norm))
      bsys = bsys/norm
      lsys = LinSys(bsys,asys)
    lsys_list.append(lsys)
  return lsys_list

# fc, bw are angular frequencies, i.e., 2*%pi*fc*Ts (Ts defaults to 1.0)
def sanityCheck(N=8, fc=2*np.pi*0.25, bw=2*np.pi*0.2):
  cc    = LinSys.create(N,fc,bw);
  (b,a) = cc.getBA()

  s  = np.zeros( 106, 'int32' )
  si = np.zeros( 106 )
  mx = 0
  pi = 0
  to = 0.5
  for pol in cc.get():
    n = pol.numer(to)[0,:]
    ni= pol.numerApprox(np.array(to))
    d = pol.denom()
    u = np.concatenate( (n, np.zeros(100)) )
    h = sig.dlsim((1,d,1), u)[1]
    h = np.array( np.round(h*2**17), 'int32' )
    thism = np.max(np.abs(h))
    if thism > mx:
      mx  = thism
      mi  = pi
    s = (s + h) % 65536
    s[s>32765]-=65536
    ui= np.concatenate( (ni, np.zeros(100)) )
    hi= sig.dlsim((1,d,1), ui)[1]
    si= si + hi
    pi= pi + 1
    plt.plot( h )
  h = sig.impulse((b,a))
  print("Max of superposition: {}".format(np.max(np.abs(s))))
  print("Max: {} for pole-pair {}".format(mx, mi))
  plt.plot( to+np.linspace(0,99,100), s [6:] )
  plt.plot( to+np.linspace(0,99,100), si[6:] )
  plt.plot( h[0], h[1] )
  plt.show()
  return cc

cc=sanityCheck()
cc.dump()
#sanityCheck().dump()
