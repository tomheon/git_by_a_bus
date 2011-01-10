import sqlite3

from nose.tools import ok_, eq_

from gbab.line_model import LineModel

class TestLineModel(object):

    def setup(self):
        self.conn = sqlite3.connect(':memory:')
        self.model = LineModel(self.conn)

    def teardown(self):
        self.conn.close()

    def test_line_manip(self):
        self.model.add_line(1, 'hi there')
        eq_(['hi there'], self.model.get_lines())
        self.model.add_line(2, 'goodbye')
        eq_(['hi there', 'goodbye'], self.model.get_lines())
        self.model.add_line(1, 'oh yeah')
        eq_(['oh yeah', 'hi there', 'goodbye'], self.model.get_lines())
        self.model.change_line(2, 'nope')
        eq_(['oh yeah', 'nope', 'goodbye'], self.model.get_lines())        
        self.model.remove_line(2)
        eq_(['oh yeah', 'goodbye'], self.model.get_lines())        
