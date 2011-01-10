class LineModel(object):
    """
    Model for lines in a single file.
    """

    def __init__(self, conn):
        self.conn = conn
        self.curs = conn.cursor()
        self._create_tables()

    def apply_change(self, changetype, line_num, line):
        todo = {'add': self.add_line,
                'remove': self.remove_line,
                'change': self.change_line}
        todo[changetype](line_num, line)
        
    def add_line(self, line_num, line):
        bump_existing_lines_sql = "UPDATE LINES SET linenum = linenum + 1 WHERE linenum >= ?;"
        insert_sql = "INSERT INTO lines (linenum, line) VALUES (?, ?);"
        
        self.curs.execute(bump_existing_lines_sql, (line_num,))
        self.curs.execute(insert_sql, (line_num, line))
        self.conn.commit()

    def remove_line(self, line_num, line=None):
        delete_sql = "DELETE FROM lines WHERE linenum = ?;"
        decrement_sql = "UPDATE lines SET linenum = linenum - 1 WHERE linenum > ?"
        self.curs.execute(delete_sql, (line_num,))
        self.curs.execute(decrement_sql, (line_num,))
        self.conn.commit()

    def change_line(self, line_num, line):
        sql = "UPDATE lines SET line = ? WHERE linenum = ?;"
        self.curs.execute(sql, (line, line_num))

    def get_lines(self):
        sql = "SELECT line FROM lines ORDER BY linenum ASC;"
        self.curs.execute(sql)
        return [row[0] for row in self.curs.fetchall()]

    # implementation

    def _create_tables(self):
        sqls = ["CREATE TABLE IF NOT EXISTS lines (lineid INTEGER PRIMARY KEY ASC, linenum INTEGER, line TEXT);"]
        for s in sqls:
            self.conn.execute(s)
