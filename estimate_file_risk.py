"""
Based on the estimated unique knowledge per dev / group of devs, and
the probabilities supplied that each will be hit by a bus, calculate
the risk associated with each file.

Note that for joint probabilities we assume that probs are independent
that any pair or more of devs will all be hit by a bus, so these
calculations are extra iffy for friends, lovers, conjoined twins, or
carpoolers.
"""

import sys
import optparse

from common import FileData

def get_bus_risk(dev, bus_risks, def_risk):
    if dev not in bus_risks:
        return def_risk
    else:
        return bus_risks[dev]

def estimate_file_risks(lines, bus_risks, def_bus_risk):
    """
    Estimate the risk in the file as:

    sum(knowledge unique to a group of 1 or more devs * the
    probability that all devs in the group will be hit by a bus)

    We use a simple joint probability and assume that all bus killings
    are independently likely.
    """
    for line in lines:
        fd = FileData(line)
        dev_risk = []
        for devs, shared in fd.dev_uniq:
            risk = shared
            for dev in devs:
                risk = float(risk) * get_bus_risk(dev, bus_risks, def_bus_risk)
            dev_risk.append((devs, risk))
        fd.dev_risk = dev_risk
        yield fd.as_line()

def parse_risk_file(risk_file, bus_risks):
    risk_f = open(risk_file, 'r')
    for line in risk_f:
        line = line.strip()
        if not line:
            continue
        dev, risk = line.split('=')
        bus_risks[dev] = float(risk)
    risk_f.close()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-b', '--bus-risk', dest='bus_risk', metavar='FLOAT', default=0.1,
                      help='The estimated probability that a dev will be hit by a bus in your analysis timeframe')
    parser.add_option('-r', '--risk-file', dest='risk_file', metavar='FILE',
                      help='File of dev=float lines (e.g. ejorgensen=0.4) with dev bus likelihoods')
    options, args = parser.parse_args()

    bus_risks = {}
    if options.risk_file:
        parse_risk_file(options.risk_file, bus_risks)
    
    for line in estimate_file_risks(sys.stdin, bus_risks, float(options.bus_risk)):
        print line
