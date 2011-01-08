class SqliteRiskModel(object):

    def __init__(self, conn, default_bus_risk, bus_risks_fname, departed_fname):
        self.conn = conn
        self.cursor = conn.cursor()
        self.default_bus_risk = default_bus_risk
        self._create_tables()
        self._parse_bus_risks(bus_risks_fname)
        self._parse_departed(departed_fname)

    def get_bus_risk(self, author):
        sql = "SELECT busrisk FROM authorbusrisks WHERE author = ?;"
        self.cursor.execute(sql, (author,))
        row = self.cursor.fetchone()
        if not row or not row[0]:
            return self.default_bus_risk
        else:
            return row[0]

    def is_departed(self, author):
        sql = "SELECT 1 FROM departedauthors WHERE author = ?;"
        self.cursor.execute(sql, (author,))
        row = self.cursor.fetchone()
        return not not row

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
                    self._set_bus_risk(author, float(risk))

    def _parse_departed(self, departed_fname):
        if departed_fname:
            with open(departed_fname, 'r') as departed_fil:
                for line in departed_fil:
                    line = line.strip()
                    if not line:
                        continue
                    author = line
                    # there's no bus risk for a departed dude
                    self._set_bus_risk(author, 0.0)
                    self._mark_departed(author)

    def _set_bus_risk(self, author, risk):
        sql = "INSERT INTO authorbusrisks (author, busrisk) VALUES (?, ?);"
        self.cursor.execute(sql, (author, risk))

    def _mark_departed(self, author):
        sql = "INSERT INTO departedauthors (author) VALUES (?);"
        self.cursor.execute(sql, (author,))

    def _create_tables(self):
        sqls = ["CREATE TABLE IF NOT EXISTS authorbusrisks (author TEXT, busrisk REAL, PRIMARY KEY (author))",
                "CREATE TABLE IF NOT EXISTS departedauthors (author TEXT, PRIMARY KEY (author))"]
        for s in sqls:
            self.conn.execute(s)

                

