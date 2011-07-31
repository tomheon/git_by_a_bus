import os

class SummaryModel(object):

    GIT_BY_A_BUS_BELOW_THRESHOLD = "Git by a Bus Safe Author"

    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()
        self._create_tables()

    def summarize(self, condensed_analysis):
        # condensed analysis is of the form:
        # (project, repo_root, project_root, fname, [(line, [([author], knowledge, risk, orphaned)])])
        repo_root, project_root, fname, line_summaries = condensed_analysis

        fname = self._adjust_fname(repo_root, project_root, fname)

        project_id = self._find_or_create_project(project_root)

        parent_dir_id = 0
        for dirname in self._split_all_dirs(os.path.split(fname)[0]):
            parent_dir_id = self._find_or_create_dir(dirname, project_id, parent_dir_id)
        
        file_id = self._create_file(os.path.split(fname)[1], parent_dir_id)

        for i, line_summary in enumerate(line_summaries):
            line_num = i + 1
            line, allocations = line_summary
            line_id = self._create_line(line.decode('utf-8'), line_num, file_id)
            for authors, knowledge, risk, orphaned in allocations:
                authors = [self._safe_author_name(author) for author in authors]
                author_group_id = self._find_or_create_author_group(authors)
                self._create_allocation(knowledge, risk, orphaned, author_group_id, line_id)
        self.conn.commit()

    def total_knowledge(self):
        select = "SELECT SUM(knowledge) FROM allocations;"
        self.cursor.execute(select, ())
        return self.cursor.fetchall()[0][0]

    def total_risk(self):
        select = "SELECT SUM(risk) FROM allocations;"
        self.cursor.execute(select, ())
        return self.cursor.fetchall()[0][0]

    def total_orphaned(self):
        select = "SELECT SUM(orphaned) FROM allocations;"
        self.cursor.execute(select, ())
        return self.cursor.fetchall()[0][0]

    def count_files(self):
        select = "SELECT COUNT(*) FROM files;"
        self.cursor.execute(select, ())
        return self.cursor.fetchall()[0][0]
        
    def authorgroups_with_risk(self, top=None):
        limit = ''
        if top:
            limit = "LIMIT %d" % top
        select = "SELECT authorsstr, SUM(risk) AS sum_risk FROM allocations, authorgroups WHERE allocations.authorgroupid " + \
            "= authorgroups.authorgroupid GROUP BY authorsstr ORDER BY sum_risk DESC %s;" % limit
        self.cursor.execute(select, ())
        ags_with_risk = []
        for row in self.cursor.fetchall():
            ags_with_risk.append((row[0], row[1] if row[1] else 0))
        return ags_with_risk

    def fileids_with_risk(self, top=None):
        limit = ''
        if top:
            limit = "LIMIT %d" % top
        select = "SELECT files.fileid, SUM(risk) AS sum_risk " + \
            "FROM files LEFT JOIN lines ON files.fileid = lines.fileid " + \
            "LEFT JOIN allocations on allocations.lineid = lines.lineid " + \
            "GROUP BY files.fileid ORDER BY sum_risk DESC %s;" % limit
        self.cursor.execute(select, ())
        fnames_with_risk = []
        for row in self.cursor.fetchall():
            fnames_with_risk.append((row[0], row[1] if row[1] else 0))
        return fnames_with_risk

    def fpath(self, fileid):
        select = "SELECT fname, dirid FROM files WHERE fileid = ?;"
        self.cursor.execute(select, (fileid,))
        fname, dirid = self.cursor.fetchall()[0]
        dirs = self._recons_dirs(dirid)
        dirs.append(fname)
        return os.path.join(*dirs)

    def project_files(self, project):
        project_id = self._find_or_create_project(project)
        select = "SELECT files.fileid, files.fname, files.dirid FROM files, dirs WHERE files.dirid = dirs.dirid AND dirs.projectid = ?;"
        self.cursor.execute(select, (project_id,))
        _fnames = []
        results = []
        for row in self.cursor.fetchall():
            _fnames.append((row[2], row[1], row[0]))
        for dir_id, fname, file_id in _fnames:
            results.append((file_id, os.path.join(self._recons_dir(dir_id), fname)))

        return results

    def file_lines(self, file_id):
        select = "SELECT SUM(knowledge), SUM(risk), SUM(orphaned), line, lines.lineid FROM " + \
                 "lines LEFT OUTER JOIN allocations ON lines.lineid = allocations.lineid " + \
                 "WHERE lines.fileid = ? GROUP BY lines.lineid ORDER BY linenum;"
        self.cursor.execute(select, (file_id,))
        return [(self._zero_if_none(row[0]),
                 self._zero_if_none(row[1]),
                 self._zero_if_none(row[2]), row[3].encode('utf-8')) for row in self.cursor.fetchall()]
             
    # implementation

    def _zero_if_none(self, val):
        if val is None:
            return 0.0
        else:
            return val

    def _recons_dir(self, dir_id):
        segs = []
        select = "SELECT dir, parentdirid FROM dirs WHERE dirid = ?;"
        while dir_id:
            self.cursor.execute(select, (dir_id,))
            dirname, dir_id = self.cursor.fetchone()
            segs.append(dirname)
        segs.reverse()
        return os.path.join(*segs)

    def _safe_author_name(self, author):
        if not author:
            return self.GIT_BY_A_BUS_BELOW_THRESHOLD
        else:
            return author

    def _create_allocation(self, knowledge, risk, orphaned, author_group_id, line_id):
        insert = "INSERT INTO allocations (knowledge, risk, orphaned, authorgroupid, lineid) VALUES (?, ?, ?, ?, ?);"
        self.cursor.execute(insert, (knowledge, risk, orphaned, author_group_id, line_id))

    def _find_or_create_author_group(self, authors):
        authorsstr = authors
        authorsstr.sort()
        authorsstr = '\n'.join(authorsstr)
        select = "SELECT authorgroupid FROM authorgroups WHERE authorsstr = ?;"
        self.cursor.execute(select, (authorsstr,))
        author_group_id = None
        row = self.cursor.fetchone()
        if row and row[0]:
            author_group_id = row[0]
        if not author_group_id:
            # we have to create it with the entries in the join table
            insert = "INSERT INTO authorgroups (authorsstr) VALUES (?);"
            self.cursor.execute(insert, (authorsstr,))
            author_ids = [self._find_or_create_author(author) for author in authors]
            self.cursor.execute(select, (authorsstr,))
            author_group_id = self.cursor.fetchone()[0]
            insert_join = "INSERT INTO authors_authorgroups (authorid, authorgroupid) VALUES (?, ?);"
            for author_id in author_ids:
                self.cursor.execute(insert_join, (author_id, author_group_id))
        return author_group_id
        
    def _find_or_create_author(self, author):
        insert = "INSERT OR IGNORE INTO authors (author) VALUES (?);"
        self.cursor.execute(insert, (author,))
        select = "SELECT authorid FROM authors WHERE author = ?;"
        self.cursor.execute(select, (author,))
        return self.cursor.fetchone()[0]

    def _create_line(self, line, line_num, file_id):
        try:
            insert = "INSERT INTO lines (line, linenum, fileid) VALUES (?, ?, ?);"
            self.cursor.execute(insert, (line, line_num, file_id))
            select = "SELECT lineid FROM lines WHERE linenum = ? AND fileid = ?;"
            self.cursor.execute(select, (line_num, file_id))
        except:
            import sys
            print >> sys.stderr, repr(line), repr(line_num), repr(file_id)
        return self.cursor.fetchone()[0]

    def _create_file(self, fname, parent_dir_id):
        insert = "INSERT INTO files (fname, dirid) VALUES (?, ?);"
        self.cursor.execute(insert, (fname, parent_dir_id))
        select = "SELECT fileid FROM files WHERE fname = ? and dirid = ?;"
        self.cursor.execute(select, (fname, parent_dir_id))
        return self.cursor.fetchone()[0]

    def _find_or_create_project(self, project):
        insert = "INSERT OR IGNORE INTO projects (project) VALUES (?);"
        self.cursor.execute(insert, (project,))
        select = "SELECT projectid FROM projects WHERE project = ?;"
        self.cursor.execute(select, (project,))
        return self.cursor.fetchone()[0]

    def _find_or_create_dir(self, dirname, project_id, parent_dir_id):
        insert = "INSERT OR IGNORE INTO dirs (dir, parentdirid, projectid) VALUES (?, ?, ?);"
        self.cursor.execute(insert, (dirname, parent_dir_id, project_id))
        select = "SELECT dirid FROM dirs WHERE dir = ? AND parentdirid = ? and projectid = ?;"
        self.cursor.execute(select, (dirname, parent_dir_id, project_id))
        return self.cursor.fetchone()[0]

    def _split_all_dirs(self, dirname):
        all_dirs = []
        
        last_split = None
        while True:
            while dirname.endswith(os.path.sep):
                dirname = dirname.rstrip(os.path.sep)
            split = os.path.split(dirname)
            if split == last_split:
                break
            dirname = split[0]
            all_dirs.append(split[1])
            last_split = split

        all_dirs.reverse()
        return all_dirs

    def _adjust_fname(self, repo_root, project_root, fname):
        root_diff = project_root[len(repo_root):]
        if root_diff.startswith(os.path.sep):
            root_diff = root_diff[1:]

        if root_diff:
            fname = fname[len(root_diff):]
        if fname.startswith(os.path.sep):
            fname = fname[1:]
        return fname

    def _recons_dirs(self, dirid):
        dirs = []
        parentdirid = None
        while parentdirid != 0:
            select = "SELECT dir, parentdirid FROM dirs WHERE dirid = ?;"
            self.cursor.execute(select, (dirid,))
            dirname, parentdirid = self.cursor.fetchall()[0]
            dirs.append(dirname)
            dirid = parentdirid
        dirs.reverse()
        return dirs

    def _create_tables(self):
        sql = ["CREATE TABLE IF NOT EXISTS projects (projectid INTEGER PRIMARY KEY ASC, project TEXT);",
               "CREATE UNIQUE INDEX IF NOT EXISTS project_idx ON projects (project);",
               "CREATE TABLE IF NOT EXISTS dirs (dirid INTEGER PRIMARY KEY ASC, dir TEXT, parentdirid INTEGER, projectid INTEGER);",
               "CREATE UNIQUE INDEX IF NOT EXISTS dirsproj_idx ON dirs (dir, parentdirid, projectid)",
               "CREATE TABLE IF NOT EXISTS files (fileid INTEGER PRIMARY KEY ASC, fname TEXT, dirid INTEGER);",
               "CREATE INDEX IF NOT EXISTS filesdir_idx ON files(dirid);",
               "CREATE TABLE IF NOT EXISTS lines (lineid INTEGER PRIMARY KEY ASC, line TEXT, fileid INTEGER, linenum INTEGER);",
               "CREATE UNIQUE INDEX IF NOT EXISTS linesnumfile_idx ON lines (fileid, linenum);",
               "CREATE INDEX IF NOT EXISTS linesfile_idx ON lines (fileid);",
               "CREATE TABLE IF NOT EXISTS authors (authorid INTEGER PRIMARY KEY ASC, author TEXT);",
               "CREATE UNIQUE INDEX IF NOT EXISTS authors_idx ON authors (author);",
               "CREATE TABLE IF NOT EXISTS authorgroups (authorgroupid INTEGER PRIMARY KEY ASC, authorsstr TEXT);",
               "CREATE UNIQUE INDEX IF NOT EXISTS authorgroupsstrs_idx ON authorgroups (authorsstr);",
               "CREATE TABLE IF NOT EXISTS authors_authorgroups (authorid INTEGER, authorgroupid INTEGER, PRIMARY KEY(authorid, authorgroupid));",
               "CREATE TABLE IF NOT EXISTS allocations (allocationid INTEGER PRIMARY KEY ASC, knowledge REAL, risk REAL, orphaned REAL, lineid INTEGER, authorgroupid INTEGER)",
               "CREATE INDEX IF NOT EXISTS linealloc_idx ON allocations (lineid);"]
        for s in sql:
            self.conn.execute(s)
    
    
