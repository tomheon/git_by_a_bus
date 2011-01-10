import sqlite3
import math

from gbab.risk_model import RiskModel

from nose.tools import ok_, eq_

class TestRiskModel(object):

    def setup(self):
        self.model = RiskModel(math.pow(0.1, 3), 0.1, 'tests/risk_files/bus_risks.txt', 'tests/risk_files/departed.txt')

    def teardown(self):
        pass

    def test_no_barf_on_none_files(self):
        RiskModel(math.pow(0.1, 3), 0.1, None, None)

    def test_bus_risks(self):
        eq_(0.2, self.model.get_bus_risk('author1'))
        eq_(0.3, self.model.get_bus_risk('author2'))        
        eq_(0.1, self.model.get_bus_risk('somebodyelse'))
        eq_(0.4, self.model.get_bus_risk('why=god'))        

    def test_departed(self):
        ok_(self.model.is_departed('departedauth1'))
        ok_(self.model.is_departed('departedauth2'))
        ok_(not self.model.is_departed('notdeparted'))

    def test_joint_prob_is_safe(self):
        a1 = 'testjointriskprob1'
        a2 = 'testjointriskprob2'
        a3 = 'testjointriskprob3'
        ok_(not self.model.joint_bus_prob_below_threshold([a1]))
        ok_(not self.model.joint_bus_prob_below_threshold([a1, a2]))
        ok_(self.model.joint_bus_prob_below_threshold([a1, a2, a3]))        