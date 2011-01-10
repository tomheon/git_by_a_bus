class KnowledgeAcct(object):

    def __init__(self, knowledge_acct_id, authors, authors_str):
        self.knowledge_acct_id = knowledge_acct_id
        self.authors_str = authors_str
        self.authors = authors


class KnowledgeModel(object):

    SAFE_KNOWLEDGE_ACCT_ID = 1
    SAFE_AUTHOR_ID = 1
    # scale by 1000 to make the numbers larger and less likely to
    # underflow on large numbers of changes
    KNOWLEDGE_PER_LINE_ADDED = 1000.0

    def __init__(self, conn, change_knowledge_constant, risk_model):
        self.change_knowledge_constant = change_knowledge_constant
        self.risk_model = risk_model
        self.conn = conn
        self.cursor = conn.cursor()
        self._create_tables()

    def apply_change(self, changetype, author, line_num):
        todo = {'change': self.line_changed,
                'remove': self.line_removed,
                'add': self.line_added}
        todo[changetype](author, line_num)

    def line_changed(self, author, line_num):
        author_id = self._lookup_or_create_author(author)
        knowledge_created = self.change_knowledge_constant * self.KNOWLEDGE_PER_LINE_ADDED
        knowledge_acquired = (1.0 - self.change_knowledge_constant) * self.KNOWLEDGE_PER_LINE_ADDED
        tot_line_knowledge = float(self._tot_line_knowledge(line_num))
        knowledge_acquired_pct = 0.0
        if tot_line_knowledge:
            knowledge_acquired_pct = knowledge_acquired / tot_line_knowledge
        self._redistribute_knowledge(author, author_id, line_num, knowledge_acquired_pct, self.risk_model)
        knowledge_acct_id = self._lookup_or_create_knowledge_acct([author])
        self._adjust_knowledge(knowledge_acct_id, line_num, knowledge_created)
        self.conn.commit()        

    def line_removed(self, author, line_num):
        knowledge_acct_ids = self._non_safe_accts_with_knowledge_of(line_num)
        for knowledge_acct_id in knowledge_acct_ids:
            self._destroy_line_knowledge(knowledge_acct_id, line_num)
        self.conn.commit()

    def line_added(self, author, line_num):
        knowledge_acct_id = self._lookup_or_create_knowledge_acct([author])
        self._adjust_knowledge(knowledge_acct_id, line_num, self.KNOWLEDGE_PER_LINE_ADDED)
        self.conn.commit()

    def knowledge_summary(self, line_num):
        sql = "SELECT knowledgeacctid, knowledge FROM lineknowledge WHERE linenum = ?"
        self.cursor.execute(sql, (line_num,))
        summary = [(self._get_knowledge_acct(row[0]).authors, row[1]) for row in self.cursor.fetchall()]
        summary.sort()
        return summary

    # implementation

    def _get_knowledge_acct(self, knowledge_acct_id):
        select = "SELECT knowledgeacctid, authors FROM knowledgeaccts WHERE knowledgeacctid = ?"
        self.cursor.execute(select, (knowledge_acct_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        else:
            return KnowledgeAcct(row[0], (row[1] or '').split('\n'), row[1])

    def _destroy_line_knowledge(self, knowledge_acct_id, line_num):
        delete = "DELETE FROM lineknowledge WHERE knowledgeacctid = ? and linenum = ?;"
        self.cursor.execute(delete, (knowledge_acct_id, line_num))
        self.conn.commit()

    def _redistribute_knowledge(self, author, author_id, line_num, redist_pct, risk_model):
        if risk_model.is_departed(author):
            # we don't redistribute any shared knowledge for departed authors
            return
        knowledge_acct_ids = self._non_safe_accts_with_knowledge_of(line_num)
        for knowledge_acct_id in knowledge_acct_ids:
            knowledge_acct = self._get_knowledge_acct(knowledge_acct_id)
            if author not in knowledge_acct.authors:
                old_acct_knowledge = self._knowledge_in_acct(knowledge_acct_id, line_num)
                
                new_authors = list(knowledge_acct.authors)
                if all([risk_model.is_departed(a) for a in new_authors]):
                    # don't create shared accounts for knowledge from
                    # departed authors, just move it into this
                    # author's acct
                    new_authors = [author]
                else:
                    new_authors.append(author)
                new_authors.sort()
                if self.risk_model.joint_bus_prob_below_threshold(new_authors):
                    new_knowledge_acct_id = self.SAFE_KNOWLEDGE_ACCT_ID
                else:
                    new_knowledge_acct_id = self._lookup_or_create_knowledge_acct(new_authors)

                knowledge_to_dist = old_acct_knowledge * redist_pct
                self._adjust_knowledge(knowledge_acct_id, line_num, -knowledge_to_dist)
                self._adjust_knowledge(new_knowledge_acct_id, line_num, knowledge_to_dist)
        self.conn.commit()

    def _knowledge_in_acct(self, knowledge_acct_id, line_num):
        select = "SELECT knowledge FROM lineknowledge WHERE knowledgeacctid = ? and linenum = ?"
        self.cursor.execute(select, (knowledge_acct_id, line_num))
        row = self.cursor.fetchone()
        if not row:
            return 0.0
        else:
            return row[0]
        
    def _non_safe_accts_with_knowledge_of(self, line_num):
        select = "SELECT knowledgeacctid FROM lineknowledge WHERE linenum = ? AND knowledgeacctid != ?;"
        self.cursor.execute(select, (line_num, self.SAFE_KNOWLEDGE_ACCT_ID))
        rows = self.cursor.fetchall()
        accts = [row[0] for row in rows]
        return accts

    def _adjust_knowledge(self, knowledge_acct_id, line_num, adjustment):
        insert = "INSERT OR IGNORE INTO lineknowledge (knowledgeacctid, linenum, knowledge) VALUES (?, ?, 0.0);"
        self.cursor.execute(insert, (knowledge_acct_id, line_num))
        update = "UPDATE lineknowledge SET knowledge = knowledge + ? WHERE knowledgeacctid = ? and linenum = ?;"
        self.cursor.execute(update, (adjustment, knowledge_acct_id, line_num))
        self.conn.commit()
        
    def _lookup_or_create_knowledge_acct(self, authors):
        authors = list(authors)
        authors.sort()
        authors_str = '\n'.join(authors)
        sql = "SELECT knowledgeacctid FROM knowledgeaccts WHERE authors = ?;"
        self.cursor.execute(sql, (unicode(authors_str),))
        row = self.cursor.fetchone()
        if not row:
            insert = "INSERT INTO knowledgeaccts (authors) VALUES (?);"
            self.cursor.execute(insert, (authors_str,))
            sql = "SELECT knowledgeacctid FROM knowledgeaccts WHERE authors = ?;"
            self.cursor.execute(sql, (authors_str,))
            row = self.cursor.fetchone()
            knowledge_acct_id = row[0]
            author_ids = [self._lookup_or_create_author(author) for author in authors]
            for author_id in author_ids:
                insert = "INSERT INTO knowledgeaccts_authors (knowledgeacctid, authorid) VALUES (?, ?);"
                self.cursor.execute(insert, (knowledge_acct_id, author_id))
            self.conn.commit()
            row = [knowledge_acct_id]
        return row[0]

    def _lookup_or_create_author(self, author):
        insert = "INSERT OR IGNORE INTO authors (author) VALUES (?);"
        self.cursor.execute(insert, (unicode(author),))
        select = "SELECT authorid FROM authors WHERE author = ?;"
        self.cursor.execute(select, (author,))
        row = self.cursor.fetchone()
        return row[0]

    def _tot_line_knowledge(self, line_num):
        sql = "SELECT SUM(knowledge) FROM lineknowledge WHERE linenum = ?;"
        self.cursor.execute(sql, (line_num,))
        row = self.cursor.fetchone()
        return row[0] or 0.0

    def _create_tables(self):
        sqls = ["CREATE TABLE IF NOT EXISTS authors (authorid INTEGER PRIMARY KEY ASC, author TEXT);",
                "CREATE UNIQUE INDEX IF NOT EXISTS authors_idx ON authors (author);",
                # by definition author 1 is the safe author
                "INSERT OR IGNORE INTO authors (authorid, author) VALUES (%d, NULL);" % self.SAFE_AUTHOR_ID,
                "CREATE TABLE IF NOT EXISTS knowledgeaccts (knowledgeacctid INTEGER PRIMARY KEY ASC, authors TEXT);",
                "CREATE UNIQUE INDEX IF NOT EXISTS knowledgeacctsauthors_idx ON knowledgeaccts (authors)",
                # by definition knowledge acct 1 is the "safe" account
                "INSERT OR IGNORE INTO knowledgeaccts (knowledgeacctid, authors) VALUES(%d, NULL);" % self.SAFE_KNOWLEDGE_ACCT_ID,
                "CREATE TABLE IF NOT EXISTS knowledgeaccts_authors (knowledgeacctid INTEGER, authorid INTEGER, PRIMARY KEY(knowledgeacctid, authorid));",
                # associate the safe user and knowledge acct
                "INSERT OR IGNORE INTO knowledgeaccts_authors (knowledgeacctid, authorid) VALUES (1, 1);",
                "CREATE TABLE IF NOT EXISTS lineknowledge (linenum INTEGER, knowledgeacctid INTEGER, knowledge REAL, PRIMARY KEY(linenum, knowledgeacctid));"]
        for s in sqls:
            self.conn.execute(s)

