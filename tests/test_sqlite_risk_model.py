import sqlite3

from gbab.sqlite_risk_model import SqliteRiskModel

from nose.tools import ok_, eq_

class TestSqliteRiskModel(object):

    def setup(self):
        self.conn = sqlite3.connect(':memory:')
        self.model = SqliteRiskModel(self.conn, 0.1, 'tests/risk_files/bus_risks.txt', 'tests/risk_files/departed.txt')

    def teardown(self):
        self.conn.close()

    def test_no_barf_on_none_files(self):
        SqliteRiskModel(self.conn, 0.1, None, None)

    def test_bus_risks(self):
        eq_(0.2, self.model.get_bus_risk('author1'))
        eq_(0.3, self.model.get_bus_risk('author2'))        
        eq_(0.1, self.model.get_bus_risk('somebodyelse'))
        eq_(0.4, self.model.get_bus_risk('why=god'))        

    def test_departed(self):
        ok_(self.model.is_departed('departedauth1'))
        ok_(self.model.is_departed('departedauth2'))
        ok_(not self.model.is_departed('notdeparted'))

