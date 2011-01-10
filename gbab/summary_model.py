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
        project, repo_root, project_root, fname, line_summaries = condensed_analysis

        fname = self._adjust_fname(repo_root, project_root, fname)

        project_id = self._find_or_create_project(project)

        parent_dir_id = 0
        for dirname in self._split_all_dirs(os.path.split(fname)[0]):
            parent_dir_id = self._find_or_create_dir(dirname, project_id, parent_dir_id)
        
        file_id = self._create_file(os.path.split(fname)[1], parent_dir_id)

        for i, line_summary in enumerate(line_summaries):
            line_num = i + 1
            line, allocations = line_summary
            line_id = self._create_line(line, line_num, file_id)
            for authors, knowledge, risk, orphaned in allocations:
                authors = [self._safe_author_name(author) for author in authors]
                author_group_id = self._find_or_create_author_group(authors)
                self._create_allocation(knowledge, risk, orphaned, author_group_id, line_id)
        self.conn.commit()
        
    # implementation

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
        insert = "INSERT INTO lines (line, linenum, fileid) VALUES (?, ?, ?);"
        self.cursor.execute(insert, (line, line_num, file_id))
        select = "SELECT lineid FROM lines WHERE linenum = ? AND fileid = ?;"
        self.cursor.execute(select, (line_num, file_id))
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
        self.cursor.execute(insert, (dirname, project_id, parent_dir_id))
        select = "SELECT dirid FROM dirs WHERE dir = ? AND parentdirid = ? and projectid = ?;"
        self.cursor.execute(select, (dirname, project_id, parent_dir_id))
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
               "CREATE TABLE IF NOT EXISTS authorgroups (authorgroupid INTEGER PRIMARY KEY ASC, authorsstr TEXT);",
               "CREATE UNIQUE INDEX IF NOT EXISTS authorgroupsstrs_idx ON authorgroups (authorsstr);",
               "CREATE TABLE IF NOT EXISTS authors_authorgroups (authorid INTEGER, authorgroupid INTEGER, PRIMARY KEY(authorid, authorgroupid));",
               "CREATE TABLE IF NOT EXISTS allocations (allocationid INTEGER PRIMARY KEY ASC, knowledge REAL, risk REAL, orphaned REAL, lineid INTEGER, authorgroupid INTEGER)",
               "CREATE INDEX IF NOT EXISTS linealloc_idx ON allocations (lineid);"]
        for s in sql:
            self.conn.execute(s)
    
    
