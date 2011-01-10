import sqlite3

from nose.tools import ok_, eq_

from gbab.knowledge_model import KnowledgeModel
from tests.mocks import MockRiskModel

class TestKnowledgeModel(object):

    def setup(self):
        self.conn = sqlite3.connect(':memory:')
        self.risk_model = MockRiskModel()
        self.model = KnowledgeModel(self.conn, 0.1, self.risk_model)

    def teardown(self):
        self.conn.close()

    def test_line_added_then_changed_then_removed(self):
        auth1 = 'changedtestauth1'
        auth2 = 'changedtestauth2'
        line_num = 10000
        self.model.line_added(auth1, line_num)
        auth1_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth1])        
        eq_(KnowledgeModel.KNOWLEDGE_PER_LINE_ADDED, self.model._knowledge_in_acct(auth1_knowledge_acct_id, line_num))
        self.model.line_changed(auth2, line_num)
        expected_val = KnowledgeModel.KNOWLEDGE_PER_LINE_ADDED * (1.0 - 0.9)
        actual_val = self.model._knowledge_in_acct(auth1_knowledge_acct_id, line_num)
        self._fok(expected_val, actual_val)
        expected_summary = [(['changedtestauth1'], 100.0), (['changedtestauth1', u'changedtestauth2'], 900.0), (['changedtestauth2'], 100.0)]
        actual_summary = self.model.knowledge_summary(line_num)
        eq_(len(expected_summary), len(actual_summary))
        for i, e in enumerate(expected_summary):
            eq_(e[0], actual_summary[i][0])
            self._fok(e[1], actual_summary[i][1])
        
        auth2_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth2])                
        expected_val = KnowledgeModel.KNOWLEDGE_PER_LINE_ADDED * (1.0 - 0.9)
        actual_val = self.model._knowledge_in_acct(auth2_knowledge_acct_id, line_num)
        self._fok(expected_val, actual_val)

        shared_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth1, auth2])
        expected_val = KnowledgeModel.KNOWLEDGE_PER_LINE_ADDED * (1.0 - 0.1)
        actual_val = self.model._knowledge_in_acct(shared_knowledge_acct_id, line_num)
        self._fok(expected_val, actual_val)

        self.model.line_removed(auth2, line_num)

        actual_val = self.model._knowledge_in_acct(auth1_knowledge_acct_id, line_num)
        eq_(0.0, actual_val)
        
        actual_val = self.model._knowledge_in_acct(auth2_knowledge_acct_id, line_num)
        eq_(0.0, actual_val)

        actual_val = self.model._knowledge_in_acct(shared_knowledge_acct_id, line_num)
        eq_(0.0, actual_val)

    def test_knowledge_goes_to_safe(self):
        self.risk_model.is_safe = True
        auth1 = 'changedtestauth1'
        auth2 = 'changedtestauth2'        
        line_num = 10001
        self.model.line_added(auth1, line_num)
        auth1_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth1])
        eq_(KnowledgeModel.KNOWLEDGE_PER_LINE_ADDED,
            self.model._knowledge_in_acct(auth1_knowledge_acct_id, line_num))
        self.model.line_changed(auth2, line_num)

        shared_knowledge_acct_id = self.model._lookup_or_create_knowledge_acct([auth1, auth2])
        self._fok(0.0, self.model._knowledge_in_acct(shared_knowledge_acct_id, line_num))
        self._fok(KnowledgeModel.KNOWLEDGE_PER_LINE_ADDED * (1.0 - 0.1),
                  self.model._knowledge_in_acct(KnowledgeModel.SAFE_KNOWLEDGE_ACCT_ID, line_num))

        self.risk_model.is_safe = False

    def _fok(self, fval1, fval2):
        ok_(fval1 + 0.001 > fval2 and fval1 - 0.001 < fval2)
