import sqlite3

from nose.tools import ok_, eq_

from gbab.sqlite_line_model import SqliteLineModel

class TestSqliteLineModel(object):

    def setup(self):
        self.conn = sqlite3.connect(':memory:')
        self.model = SqliteLineModel(self.conn)

    def teardown(self):
        self.conn.close()

    def testLookupCreateRemove(self):
        eq_(None, self.model.lookup_line_id('no such proj', 'no such file', 100))
        self.model.add_line('proj', 'fil', 12, 'hi there')
        eq_(None, self.model.lookup_line_id('no such proj', 'no such file', 100))                
        line_id = self.model.lookup_line_id('proj', 'fil', 12)
        ok_(line_id)
        self.model.remove_line(line_id)
        eq_(None, self.model.lookup_line_id('no such proj', 'no such file', 100))

    def testGetChange(self):
        eq_(None, self.model.get_line(0))
        self.model.add_line('proj', 'fil', 12, 'hi there')
        line_id = self.model.lookup_line_id('proj', 'fil', 12)
        ok_(line_id)
        line = self.model.get_line(line_id)
        eq_('proj', line.project)
        eq_('fil', line.fname)
        eq_(12, line.line_num)
        eq_(line_id, line.line_id)
        eq_('hi there', line.line)
        self.model.change_line(line_id, 'bye here')
        line = self.model.get_line(line_id)
        eq_('proj', line.project)
        eq_('fil', line.fname)
        eq_(12, line.line_num)
        eq_(line_id, line.line_id)
        eq_('bye here', line.line)
        
        

