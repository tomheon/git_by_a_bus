class RiskModel(object):

    def __init__(self, risk_threshold, default_bus_risk, bus_risks_fname, departed_fname):
        self.risk_threshold = risk_threshold
        self.default_bus_risk = default_bus_risk
        self.departed = set()
        self.bus_risks = {}
        self._parse_bus_risks(bus_risks_fname)
        self._parse_departed(departed_fname)

    def get_bus_risk(self, author):
        if not author or not author.strip():
            return self.risk_threshold
        if author not in self.bus_risks:
            self.bus_risks[author] = self.default_bus_risk
        return self.bus_risks[author]

    def is_departed(self, author):
        return author in self.departed

    def joint_bus_prob(self, authors):
        return reduce(lambda x, y: x * y,
                      [self.get_bus_risk(author) for author in authors])
        
    def joint_bus_prob_below_threshold(self, authors):
        return self.joint_bus_prob(authors) <= self.risk_threshold

    # implementation

    def _parse_bus_risks(self, bus_risks_fname):
        if bus_risks_fname:
            with open(bus_risks_fname, 'r') as risk_fil:
                for line in risk_fil:
                    line = line.strip()
                    if not line:
                        continue
                    # just in case someone has = in the author's name
                    segs = line.split('=')
                    risk = segs[-1]
                    author = '='.join(segs[:-1])
                    self.bus_risks[author] = float(risk)

    def _parse_departed(self, departed_fname):
        if departed_fname:
            with open(departed_fname, 'r') as departed_fil:
                for line in departed_fil:
                    line = line.strip()
                    if not line:
                        continue
                    author = line
                    # there's one bus risk for a departed dude
                    self.bus_risks[author] = 1.0
                    self.departed.add(author)
