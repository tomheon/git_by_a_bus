from nose.tools import eq_

from gbab.diff_walker import DiffWalker

def test_sample_diffs():
    test_data = [('diff1.txt', [('add',
                                 51,
                                 "        dev = dev.replace(',', '_').replace(':', '_')")]),
                 ('diff2.txt', [('remove',
                                 13,
                                 None),
                                ('remove',
                                 13,
                                 None)]),
                 ('diff3.txt', [('change',
                                 150,
                                 "               Paths must be absolute paths to local git-controlled directories (they may be subdirs in the git repo)."),
                                ('remove',
                                 151,
                                 None)]),
                 ('diff4.txt', [('change',
                                 17,
                                 "from common import is_interesting, FileData, safe_author_name"),
                                ('change',
                                 87,
                                 "            author = safe_author_name(author)")]),
                 ('diff5.txt', [('add',
                                 5,
                                 "def safe_author_name(author):"),
                                ('add',
                                 6,
                                 "        return author.replace(',', '_').replace(':', '_')"),
                                ('change',
                                 122,
                                 "        line = safe_author_name(line)")]),
                 ('diff6.txt', [('remove',
                                 13,
                                 None),
                                ('remove',
                                 13,
                                 None)])]
                 
    for sample_diff_fname, expected_changes in test_data:
        diff_walker = DiffWalker()
    
        with open('tests/sample_diffs/%s' % sample_diff_fname, 'r') as fil:
            diff = fil.read()
            changes = diff_walker.walk(diff)

            eq_(expected_changes, changes)
