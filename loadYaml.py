import glob
import pycpsw
import sys
from   getopt import getopt

def usage(nm):
  print("Usage: {} -Y yaml_file [-r root_node] [-a ipAddr] [-h]".format( nm ))
  print("       note: 'yaml_file' may be a 'glob' pattern")

class IpFixup(pycpsw.YamlFixup):
  def __init__(self, ipAddr):
    super(pycpsw.YamlFixup, self).__init__()
    self.ipAddr = ipAddr

  def __call__(self, node, top):
    ip = node["ipAddr"]
    if None != ip and ip.IsDefined() and not ip.IsNull():
      ip.set( self.ipAddr )

class LoadYaml():

  @staticmethod
  def usedOpts():
    return "Y:a:r:h"

  def __init__(self, otherOpts="", globPatt=None, rootName="NetIODev", ipAddr=None):
    self.otherOpts = otherOpts
    self.globPatt  = globPatt
    self.rootName  = rootName
    self.ipAddr    = ipAddr

  def allOpts(self):
    return self.usedOpts() + self.otherOpts

  def load(self):
    opts, args = getopt(sys.argv[1:], self.allOpts())
    for opt,arg in opts:
      if    opt == "-Y":
        self.globPatt = arg
      elif  opt == "-a":
        self.ipAddr   = arg
      elif  opt == "-r":
        self.rootName = arg
      elif  opt == "-h":
        usage(sys.argv[0])
        sys.exit(0)
    if None == self.globPatt:
      usage(sys.argv[0])
      print("  MISSING: -Y yaml_file")
      sys.exit(1)
    if None != self.ipAddr:
      fixIp = IpFixup( self.ipAddr )
    else:
      fixIp = None
    return pycpsw.Path.loadYamlFile(glob.glob(self.globPatt)[0], self.rootName, yamlFixup=fixIp)
