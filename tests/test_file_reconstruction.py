import sqlite3

from nose.tools import eq_

from gbab.diff_walker import DiffWalker
from gbab.line_model import LineModel

def test_reconstruction():
    conn = sqlite3.connect(':memory:')
    line_model = LineModel(conn)
    diff_walker = DiffWalker()
    
    for ind in range(13):
        diff_file_ind = ind + 1
        diff_fname = "tests/sample_recons/diff%s.txt" % diff_file_ind
        actual_fname = "tests/sample_recons/file%s.txt" % diff_file_ind
        with open(diff_fname, 'r') as diff_fil:
            diff = diff_fil.read()
            for (changetype, line_num, line) in diff_walker.walk(diff):
                line_model.apply_change(changetype, line_num, line)

            recons_lines = line_model.get_lines()
            
            with open(actual_fname, 'r') as actual_fil:
                actual_lines = [line.rstrip('\n') for line in actual_fil]
                eq_(actual_lines, recons_lines)

    conn.close()

