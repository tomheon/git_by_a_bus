class Line(object):

    def __init__(self, row):
        if row:
            self.line_id = row[0]
            self.project = row[1]
            self.fname = row[2]
            self.line_num = row[3]
            self.line = row[4]
                           

class SqliteLineModel(object):
    """
    Model for lines (and related projects and files) stored in an
    sqlite database.
    """

    def __init__(self, conn):
        self.conn = conn
        self.curs = conn.cursor()
        self._create_tables()

    def lookup_line_id(self, project, fname, line_num):
        if line_num is None:
            return None
        sql = "SELECT lineid FROM linesview WHERE projectname = ? AND filename = ? AND linenum = ?;"
        return self._get_id(sql, (project, fname, line_num))

    def add_line(self, project, fname, line_num, line):
        proj_id, file_id = self._project_and_file_ids(project, fname)
        
        bump_existing_lines_sql = "UPDATE LINES SET linenum = linenum + 1 WHERE fileid = ? AND linenum >= ?;"
        insert_sql = "INSERT INTO lines (fileid, linenum, line) VALUES (?, ?, ?);"
        
        self.curs.execute(bump_existing_lines_sql, (file_id, line_num))
        self.curs.execute(insert_sql, (file_id, line_num, line))
        self.conn.commit()

    def remove_line(self, line_id):
        select_sql = "SELECT fileid, linenum FROM lines WHERE lineid = ?"
        self.curs.execute(select_sql, (line_id,))
        row = self.curs.fetchone()
        if row:
            file_id, line_num = row
            soft_delete_sql = "UPDATE lines SET linenum = NULL, line = NULL WHERE lineid = ?;"
            decrement_sql = "UPDATE lines SET linenum = linenum - 1 WHERE fileid = ? AND linenum > ?"
            self.curs.execute(soft_delete_sql, (line_id,))
            self.curs.execute(decrement_sql, (file_id, line_num))
            self.conn.commit()

    def change_line(self, line_id, line):
        sql = "UPDATE lines SET line = ? WHERE lineid = ?;"
        self.curs.execute(sql, (line, line_id))

    def get_line(self, line_id):
        sql = "SELECT lineid, projectname, filename, linenum, line FROM linesview WHERE lineid = ?"
        self.curs.execute(sql, (line_id,))
        row = self.curs.fetchone()
        if not row:
            return None
        return Line(row)

    def file_lines(self, project, fname):
        proj_id, file_id = self._project_and_file_ids(project, fname)
        sql = "SELECT lineid, line FROM lines WHERE fileid = ? AND linenum IS NOT NULL ORDER BY linenum;"
        self.curs.execute(sql, (file_id,))
        return self.curs.fetchall()

    # implementation

    def _project_and_file_ids(self, project, fname):
        proj_id = self._create_or_lookup_project_id(project)
        file_id = self._create_or_lookup_file_id(proj_id, fname)
        return proj_id, file_id

    def _create_or_lookup_project_id(self, project):
        sql = "INSERT OR IGNORE INTO projects (projectname) VALUES (?)"
        self.curs.execute(sql, (project,))
        return self._get_id("SELECT projectid FROM projects WHERE projectname = ?", (project,))

    def _create_or_lookup_file_id(self, proj_id, fname):
        sql = "INSERT OR IGNORE INTO files (projectid, filename) VALUES (?, ?)"
        self.curs.execute(sql, (proj_id, fname))
        return self._get_id("SELECT fileid FROM files WHERE projectid = ? AND filename = ?", (proj_id, fname))

    def _get_id(self, sql, dbparams):
        self.curs.execute(sql, dbparams)
        row = self.curs.fetchone()
        if not row:
            return None
        return row[0]

    def _create_tables(self):
        sqls = ["CREATE TABLE IF NOT EXISTS projects (projectid INTEGER PRIMARY KEY ASC, projectname TEXT);",
                "CREATE UNIQUE INDEX IF NOT EXISTS projectname_idx ON projects (projectname);",
                "CREATE TABLE IF NOT EXISTS files (fileid INTEGER PRIMARY KEY ASC, filename TEXT, projectid INTEGER);",
                "CREATE UNIQUE INDEX IF NOT EXISTS filename_idx ON files (filename);",
                "CREATE INDEX IF NOT EXISTS projectid_idx ON files (projectid);",                                
                "CREATE TABLE IF NOT EXISTS lines (lineid INTEGER PRIMARY KEY ASC, fileid INTEGER, linenum INTEGER, line TEXT);",
                "CREATE INDEX IF NOT EXISTS fileid_idx ON lines (fileid);",
                "CREATE VIEW IF NOT EXISTS linesview AS SELECT lines.lineid, lines.linenum, lines.line, " + \
                "files.fileid, files.filename, projects.projectid, projects.projectname FROM files, projects, lines " + \
                "WHERE files.projectid = projects.projectid AND lines.fileid = files.fileid;"]
        for s in sqls:
            self.conn.execute(s)
