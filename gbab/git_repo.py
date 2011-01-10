import os
import re
import sys

from subprocess import Popen, PIPE

class GitRepo(object):

    def __init__(self, project_root, git_exe):
        self.project_root = project_root
        self.git_exe = git_exe

    def ls(self):
        """
        List the entire tree that git is aware of in this directory.
        """
        cwd = os.getcwd()
        self._chdir()        
        # --full-tree = allow absolute path for final argument (pathname)
        # --name-only = don't show the git id for the object, just the file name
        # -r = recurse
        git_cmd = ('%s ls-tree --full-tree --name-only -r HEAD' % self.git_exe).split(' ')
        git_cmd.append(self.project_root)
        git_p = Popen(git_cmd, stdout=PIPE)
        (out, err) = git_p.communicate()
        if err:
            print >> sys.stderr, "Error from git ls: %s" % err
            raise IOError(err)
        fnames = out.split('\n')
        os.chdir(cwd)
        return fnames

    def log(self, fname):
        """
        Return parsed logs in the form:

        [(author, diff]
        """
        return self._parse_log(fname)

    def git_root(self, chdir=True):
        """
        Given that we have chdir'd into a Git controlled dir, get the git
        root for purposes of adjusting paths.
        """
        cwd = os.getcwd()
        if chdir:
            os.chdir(self.project_root)
        git_cmd = ('%s rev-parse --show-toplevel' % self.git_exe).split(' ')
        git_p = Popen(git_cmd, stdout=PIPE)
        root = git_p.communicate()[0].strip()
        if chdir:
            os.chdir(cwd)
        return root


    # implementation

    def _parse_log(self, fname):
        parsed_entries = []
        # -z = null byte separate log entries
        # -w = ignore all whitespace when calculating changed lines
        # --follow = follow file history through renames
        # --patience = use the patience diff algorithm (looks to be better for our heatmapping)
        # -p show patches (diffs)
        cwd = os.getcwd()
        self._chdir()        
        git_cmd = ("%s log -z -w --follow --patience -p" % self.git_exe).split(' ')
        git_cmd.append(fname)
        git_p = Popen(git_cmd, stdout=PIPE)
        (out, err) = git_p.communicate()
        if err:
            print >> sys.stderr, "Error from git ls: %s" % err
            raise IOError(err)
        out = unicode(out, 'utf8', errors='ignore')

        log_entries = [entry for entry in out.split('\0') if entry.strip()]
        os.chdir(cwd)
        tot_entries = len(log_entries)
        
        for i, entry in enumerate(log_entries):
            try:
                header, diff = self._split_entry_header(entry)
                diff = '\n'.join(diff)
                if not diff.strip():
                    raise ValueError("Diff appeared to be empty")
                author = self._parse_author(header)
                if not author:
                    raise ValueError("Could not parse author")
                parsed_entries.append((author, diff))
            except ValueError as e:
                pass
                #print >> sys.stderr, "Could not parse git log entry %s" % entry
                #print >> sys.stderr, e

        parsed_entries.reverse()

        return parsed_entries

    def _parse_author(self, header_lines):
        # preserve any spaces that showed up in the name (though collapsed)
        segs = re.split(r'\s+', header_lines[1].strip())
        return ' '.join(segs[1:-1])
        
    def _split_entry_header(self, entry):
        lines = entry.split('\n')
        if not lines or len(lines) < 2:
            raise ValueError("Empty entry")
        if not lines[0].startswith("commit"):
            raise ValueError("No commit line")
        if not lines[1].startswith("Author"):
            raise ValueError("No author line")
        ind = 2
        lines_len = len(lines)
        while ind < lines_len and not lines[ind].startswith('diff'):
            ind += 1

        return lines[:ind], lines[ind:]

    def _chdir(self):
        # first we have to get into the git repo to make the git_root work...
        os.chdir(self.project_root)
        # then we can change to the git root
        os.chdir(self.git_root(False))
