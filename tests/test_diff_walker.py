from nose.tools import eq_

from gbab.diff_walker import DiffWalker
from tests.mocks import MockSourceFile

def test_sample_diffs():
    src_file = MockSourceFile()    
    test_data = [('diff1.txt', [(src_file.add_line,
                                 'author1',
                                 51,
                                 "        dev = dev.replace(',', '_').replace(':', '_')")]),
                 ('diff2.txt', [(src_file.remove_line,
                                 'author1',
                                 13),
                                (src_file.remove_line,
                                 'author1',
                                 13)]),
                 ('diff3.txt', [(src_file.change_line,
                                 'author1',
                                 150,
                                 "               Paths must be absolute paths to local git-controlled directories (they may be subdirs in the git repo)."),
                                (src_file.remove_line,
                                 'author1',
                                 151)]),
                 ('diff4.txt', [(src_file.change_line,
                                 'author1',
                                 17,
                                 "from common import is_interesting, FileData, safe_author_name"),
                                (src_file.change_line,
                                 'author1',
                                 87,
                                 "            author = safe_author_name(author)")]),
                 ('diff5.txt', [(src_file.add_line,
                                 'author1',
                                 5,
                                 "def safe_author_name(author):"),
                                (src_file.add_line,
                                 'author1',
                                 6,
                                 "        return author.replace(',', '_').replace(':', '_')"),
                                (src_file.change_line,
                                 'author1',
                                 122,
                                 "        line = safe_author_name(line)")]),
                 ('diff6.txt', [(src_file.remove_line,
                                 'author1',
                                 13),
                                (src_file.remove_line,
                                 'author1',
                                 13)])]
                 
    for sample_diff_fname, expected_call_log in test_data:
        diff_walker = DiffWalker()
    
        with open('tests/sample_diffs/%s' % sample_diff_fname, 'r') as fil:
            diff = fil.read()
            diff_walker.walk('author1', diff, src_file)

            eq_(expected_call_log, src_file.call_log)

        src_file.clear_call_log()

