#!/usr/bin/python3 -i

import pycpsw
import re

# Subclass the PathVisitor.
#
# The user user is supposed to use this
#
# grep      = PathGrep(root, [needle])
# found     = grep( needle )
# foundFrom = grep( start, needle )
#
# any argument can be omitted in which case
# the previous values are used.
class PathGrep(pycpsw.PathVisitor):
  """Recurse through CPSW hierarchy looking for RE pattern matches

     Starts recursion at 'path' and returns a list of RE matches.
  """
  def __init__(self, root = None, patt = None, asPath = False):
    pycpsw.PathVisitor.__init__(self)
    self.level   = 0
    self.result  = []
    self.root    = root
    self.setPatt_( patt )
    self.maxl    = -1
    self.asPath_ = asPath

  def setPatt_(self, patt):
    if patt == None:
      self.re_prog = None
    else:
      self.re_prog = re.compile( patt )

  # Visitor method we must implement for CPSW
  def visitPre(self, path):
    self.level = self.level + 1
    if self.re_prog == None:
      tl = path.tail()
      fr = path.getTailFrom()
      to = path.getTailTo()
      st = '{:<{}s}{}[{}'.format('',self.level,tl.getName(),fr)
      if fr == to:
        st+="]"
      else:
        st+="-{}]".format(to)
      print(st)
    elif self.re_prog.search( path.toString() ) != None:
      if self.asPath_:
        self.result.append(path.clone())
      else:
        self.result.append(path.toString())
    return self.maxl < 0 or self.level < self.maxl

  # Visitor method we must implement for CPSW
  def visitPost(self, path):
    self.level = self.level - 1
    pass

  def getRoot(self):
    return self.root

  def setRoot(self, root):
    self.root = root

  def __call__(self, patt = False, maxlevel = -1):
    if maxlevel >=0:
      self.maxl = maxlevel + 1
    else:
      self.maxl = -1
    if patt or patt == None:
      self.setPatt_( patt )
    if self.root    == None:
      raise Exception("No root set");
    if self.re_prog != None:
      self.result = []
    else:
      self.result = None
    self.root.explore(self)
    return self.result
