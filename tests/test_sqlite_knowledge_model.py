import sqlite3

from nose.tools import ok_, eq_

from gbab.sqlite_knowledge_model import SqliteKnowledgeModel
from tests.mocks import MockRiskModel

class TestSqliteKnowledgeModel(object):

    def setup(self):
        self.conn = sqlite3.connect(':memory:')
        self.risk_model = MockRiskModel()
        self.model = SqliteKnowledgeModel(self.conn, 0.1, self.risk_model)

    def teardown(self):
        self.conn.close()

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

    def test_knowledge_goes_to_safe(self):
        self.risk_model.is_safe = True
        auth1 = 'changedtestauth1'
        auth2 = 'changedtestauth2'        
        line_id = 10001
        self.model.line_added(auth1, line_id)
        auth1_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth1])
        eq_(1.0, self.model._knowledge_in_acct(auth1_knowledge_acct_id, line_id))
        self.model.line_changed(auth2, line_id)

        shared_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth1, auth2])
        self._fok(0.0, self.model._knowledge_in_acct(shared_knowledge_acct_id, line_id))
        self._fok(1.0 * (1.0 - 0.1), self.model._knowledge_in_acct(SqliteKnowledgeModel.SAFE_KNOWLEDGE_ACCT_ID, line_id))

        self.risk_model.is_safe = False
        
    def _fok(self, fval1, fval2):
        ok_(fval1 + 0.001 > fval2 and fval1 - 0.001 < fval2)
