from   bpmMiscUtils import bpmMiscUtilsInit, sv, pgrep, root, logOn, logOff, SVL
import bpm
import LinSim
import sys
import getopt
from   loadYaml import LoadYaml

def myOpts():
  return "CS"

opts, args = getopt.getopt( sys.argv[1:], myOpts() + LoadYaml.usedOpts() )

patt    = "Kcu*Bpm*/000TopLevel.yaml"

if len(args) > 0:
  patt = args[0]

hasMode = False

for opt,arg in opts:
  if   opt == "-C":
    modeCav = True
    hasMode = True
  elif opt == "-S":
    modeCav = False
    hasMode = True

bpmMiscUtilsInit(myOpts())

logOn("logf.yaml")

# silence the Fan
sv( pgrep(".*FanController/Bypass")[0], root() ).setVal( 0 )

for bay in [0,1]:

  if not hasMode:
    fwMode = sv( pgrep(".*AmcBay{:d}/Bpm/FirmwareConfiguration".format(bay))[0], root() ).getVal()
    print("FW Mode: ", fwMode)
    modeCav = (fwMode != "StriplineBpm")
  
  print("Cavity Mode: ", modeCav)
  
  
  s = bpm.SIM( bay )
  s.getBpm().set("Command", "Halt")
  # U: Fo 30    , Bw: 1.25
  # V: Fo 38    , Bw: 2
  # R: Fo 37    , Bw: 3
  #
  # Channels are mapped to spare, V, U, Ref
  fs   = 370.
  Fcav = [0, 38.2/fs , 30.3/fs  , 37.2/fs ]
  Qcav = [0, 38.2/2.1, 30.3/1.25, 37.2/3.3]
  #Fcav = [0, 38.2/fs , 36.7/fs  , 37.3/fs ]
  #Qcav = [0, 38.2/2.2, 36.7/1.25, 37.3/3.1]
  Ffil = (49.2+22.3)/2/fs 
  Bfil = (49.2-22.3)/fs 
  if modeCav:
    modl = LinSim.mkCavitySystem( Fcav, Qcav, Ffil, Bfil )
  else:
    modl = LinSim.mkStriplineSystem( Ffil, Bfil )
  s.fcal( modl )
  # Full beam rate is timing-clk/200 (= 1300/7/200)
  # If the JESD clock runs at 370MHz then
  # one beam cycle takes 370 * 1400/1300 = 398.46153846153845
  # .46153846153845 * 2**17 = 60495
  
  #NOTE: the simulator was designed to 'drive/simulate'
  #      the period at which beam pulses are generated.
  #      This can be a non-integer multiple of simulator
  #      clock cycles.
  #
  #      In the context of the BPM firmware, however,
  #      we want to drive the simulator with an external
  #      trigger (from the timing system).
  #      
  #      A special firmware module is wrapped around the
  #      simulator which 'freezes' it after it completed
  #      one beam cycle (by means of freezing TREADY on
  #      the output stream).
  #      Simulation is then resumed by the next EVR trigger.
  #
  #      This means that the simulator period MUST be
  #      less than 200 timing clock cycles ('1MHz' period).
  #      
  #      We choose an arbitrary value of 320 -- the filter
  #      response should have rung out by this time.
  s.getBpm().set("PeriodInt",   320)
  s.getBpm().set("PeriodFract", 60495)
  s.getBpm().set("Command", "Run")

try:
  evrp = pgrep("EvrV2$")[0]
except IndexError:
  evrp = pgrep("EvrV2CoreTriggers$")[0]

evrChnl  = SVL( evrp + "/EvrV2ChannelReg[0-1]"  )
evrTrigS = SVL( evrp + "/EvrV2TriggerReg[0-1]"  )
evrTrigF = SVL( evrp + "/EvrV2TriggerReg[4-5]"  )
msgTrig  = SVL( evrp + "/EvrV2TriggerReg[11-12]")

evrChnl.set("DestSel", 0x20000)
evrChnl.set("Enable",       1)
evrChnl.set("RateSel",   [0,6])
evrTrigF.set("Source",   [0,0])
evrTrigF.set("Enable",   [1,1])
evrTrigF.set("Width",    [1,1])
evrTrigS.set("Source",   [1,1])
evrTrigS.set("Enable",   [1,1])
evrTrigS.set("Width",    [1,1])
msgTrig.set("Source",   [0,1])
# decimator trigger #12 must be active
# one clock after posting trigger #11
#
# If backplane message decimation is enabled
# then backplane messages are only posted
# if trigger #12 is asserted (for debugging; software
# may receive and look at messages without being
# swamped) 
msgTrig.set("Width",   [1,2])
msgTrig.set("Enable",       1)
msgTrig.set("Delay",     180)
print("Initialization DONE")

logOff()
