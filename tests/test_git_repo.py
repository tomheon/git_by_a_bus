import os

from nose.tools import ok_

from gbab.git_repo import GitRepo

class TestGitRepo(object):

    def setup(self):
        self.curdir = os.getcwd()
        self.git_repo = GitRepo(self.curdir, '/usr/bin/env git')

    def teardown(self):
        os.chdir(self.curdir)

    def test_ls(self):
        fnames = self.git_repo.ls()
        ok_('tests/test_git_repo.py' in fnames)

    def test_log(self):
        log_entries = self.git_repo.log('tests/test_git_repo.py')
        authors = [le[0] for le in log_entries]
        ok_('tomheon' in authors)
