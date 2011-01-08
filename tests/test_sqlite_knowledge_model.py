import sqlite3

from nose.tools import ok_, eq_

from gbab.sqlite_knowledge_model import SqliteKnowledgeModel

class TestSqliteKnowledgeModel(object):

    def setup(self):
        self.conn = sqlite3.connect(':memory:')
        self.model = SqliteKnowledgeModel(self.conn,
                                          0.1,
                                          0.1, 'tests/knowledge_files/bus_risks.txt',
                                          'tests/knowledge_files/departed.txt')

    def teardown(self):
        self.conn.close()

    def test_no_barf_on_nones(self):
        self.model = SqliteKnowledgeModel(self.conn, 0.1, 0.1, None, None)

    def test_bus_risks(self):
        author1_id = self.model._lookup_or_create_author('author1')
        eq_(0.2, self.model._get_bus_risk(author1_id))
        author2_id = self.model._lookup_or_create_author('author2')
        eq_(0.3, self.model._get_bus_risk(author2_id))        
        another_author_id = self.model._lookup_or_create_author('anotherauthor')
        eq_(0.1, self.model._get_bus_risk(another_author_id))

    def test_departed(self):
        departed1_id = self.model._lookup_or_create_author('departedauth1')
        departed2_id = self.model._lookup_or_create_author('departedauth2')
        not_departed_id = self.model._lookup_or_create_author('notdeparted')
        ok_(self.model.is_departed(departed1_id))
        ok_(self.model.is_departed(departed2_id))
        ok_(not self.model.is_departed(not_departed_id))

    def test_line_added_then_changed_then_removed(self):
        auth1 = 'changedtestauth1'
        auth2 = 'changedtestauth2'
        line_id = 10000
        self.model.line_added(auth1, line_id)
        auth1_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth1])        
        eq_(1.0, self.model._knowledge_in_acct(auth1_knowledge_acct_id, line_id))
        self.model.line_changed(auth2, line_id)
        expected_val = 1.0 * (1.0 - 0.9)
        actual_val = self.model._knowledge_in_acct(auth1_knowledge_acct_id, line_id)
        self._fok(expected_val, actual_val)        
        
        auth2_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth2])                
        expected_val = 1.0 * (1.0 - 0.9)
        actual_val = self.model._knowledge_in_acct(auth2_knowledge_acct_id, line_id)
        self._fok(expected_val, actual_val)

        shared_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth1, auth2])
        expected_val = 1.0 * (1.0 - 0.1)
        actual_val = self.model._knowledge_in_acct(shared_knowledge_acct_id, line_id)
        self._fok(expected_val, actual_val)

        self.model.line_removed(auth2, line_id)

        actual_val = self.model._knowledge_in_acct(auth1_knowledge_acct_id, line_id)
        eq_(0.0, actual_val)
        
        actual_val = self.model._knowledge_in_acct(auth2_knowledge_acct_id, line_id)
        eq_(0.0, actual_val)

        actual_val = self.model._knowledge_in_acct(shared_knowledge_acct_id, line_id)
        eq_(0.0, actual_val)
        
    def _fok(self, fval1, fval2):
        ok_(fval1 + 0.001 > fval2 and fval1 - 0.001 < fval2)
