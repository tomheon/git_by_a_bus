import sqlite3

from nose.tools import ok_, eq_

from mocks import MockKnowledgeModel

from gbab.source_file import SourceFile
from gbab.diff_walker import DiffWalker
from gbab.sqlite_line_model import SqliteLineModel

def test_reconstruction():
    conn = sqlite3.connect(':memory:')
    line_model = SqliteLineModel(conn)
    knowledge_model = MockKnowledgeModel()
    src_file = SourceFile('testproj', 'testfile.txt', line_model, knowledge_model)
    diff_walker = DiffWalker()

    for ind in range(13):
        diff_file_ind = ind + 1
        diff_fname = "tests/sample_recons/diff%s.txt" % diff_file_ind
        actual_fname = "tests/sample_recons/file%s.txt" % diff_file_ind
        with open(diff_fname, 'r') as diff_fil:
            diff = diff_fil.read()
            diff_walker.walk('me', diff, src_file)

            recons_lines = [line for line_id, line in line_model.file_lines('testproj', 'testfile.txt')]
            
            with open(actual_fname, 'r') as actual_fil:
                actual_lines = [line.rstrip('\n') for line in actual_fil]
                eq_(actual_lines, recons_lines)
    
    conn.close()

