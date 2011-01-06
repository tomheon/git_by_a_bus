"""
Module to generate file stats using git.

The only function here intended for external consumption is gen_stats.

Output of gen_stats should be exactly the same as the output of
git_file_stats.gen_stats, but in practice they may differ by a line or
two (appears to be whitespace handling, perhaps line endings?)
"""

import sys
import os
import re

from subprocess import Popen, PIPE

from common import is_interesting, FileData, safe_author_name
    
def gen_stats(root, project, interesting, not_interesting, options):
    """
    root: the path a local, git controlled-directory that is the root
    of this project

    project: the name of the project

    interesting: regular expressions that indicate an interesting path
    if they match

    not_interesting: regular expressions that trump interesting and
    indicate a path is not interesting.

    options: from gen_file_stats.py's main, currently only uses
    git_exe.

    Yields FileData objects encoded as tsv lines.  Only the fname,
    dev_experience and cnt_lines fields are filled in.
    """
    git_exe = options.git_exe

    # since git only works once you're in a git controlled path, we
    # need to get into one of those...
    prepare(root, git_exe)

    files = git_ls(root, git_exe)

    for f in files:
        if is_interesting(f, interesting, not_interesting):
            dev_experience = parse_dev_experience(f, git_exe)
            if dev_experience:
                fd = FileData(':'.join([project, f]))
                fd.dev_experience = dev_experience
                fd.cnt_lines = count_lines(f)
                fd_line = fd.as_line()
                if fd_line.strip():
                    yield fd_line


def count_lines(f):
    fil = open(f, 'r')
    count = 0
    for line in fil:
        count += 1
    fil.close()
    return count

def parse_experience(log):
    """
    Parse the dev experience from the git log.
    """
    # list of tuple of shape [(dev, lines_add, lines_removed), ...]
    exp = []

    # entry lines were zero separated with -z
    entry_lines = log.split('\0')

    current_entry = []
    
    for entry_line in entry_lines:
        if not entry_line.strip():
            # blank entry line marks the end of an entry, we're ready to process
            local_entry = current_entry
            current_entry = []
            if len(local_entry) < 2:
                print >> sys.stderr, "Weird entry, cannot parse: %s\n-----" % '\n'.join(local_entry)
                continue
            author, changes = local_entry[:2]
            author = safe_author_name(author)
            try:
                changes_split = re.split(r'\s+', changes)
                # this can be two fields if there were file renames
                # detected, in which case the file names are on the
                # following entry lines, or three fields (third being
                # the filename) if there were no file renames
                lines_added, lines_removed = changes_split[:2]
                lines_added = int(lines_added)
                lines_removed = int(lines_removed)

                # don't record revisions that don't have any removed or
                # added lines...they mean nothing to our algorithm
                if lines_added or lines_removed:
                    exp.append((author, lines_added, lines_removed))
            except ValueError:
                print >> sys.stderr, "Weird entry, cannot parse: %s\n-----" % '\n'.join(local_entry)                    
                continue
        else:
            # continue to aggregate the entry
            lines = entry_line.split('\n')
            current_entry.extend([line.strip() for line in lines])

    # we need the oldest log entries first.
    exp.reverse()
    return exp
            
def parse_dev_experience(f, git_exe):
    """
    Run git log and parse the dev experience out of it.
    """
    # -z = null byte separate logs
    # -w = ignore all whitespace when calculating changed lines
    # --follow = follow file history through renames
    # --numstat = print a final ws separated line of the form 'num_added_lines num_deleted_lines file_name'
    # --format=format:%an = use only the author name for the log msg format
    git_cmd = ("%s log -z -w --follow --numstat --format=format:%%an" % git_exe).split(' ')
    git_cmd.append(f)
    git_p = Popen(git_cmd, stdout=PIPE)
    (out, err) = git_p.communicate()
    return parse_experience(out)

def git_ls(root, git_exe):
    """
    List the entire tree that git is aware of in this directory.
    """
    # --full-tree = allow absolute path for final argument (pathname)
    # --name-only = don't show the git id for the object, just the file name
    # -r = recurse
    git_cmd = ('%s ls-tree --full-tree --name-only -r HEAD' % git_exe).split(' ')
    git_cmd.append(root)
    git_p = Popen(git_cmd, stdout=PIPE)
    files = git_p.communicate()[0].split('\n')
    return files

def git_root(git_exe):
    """
    Given that we have chdir'd into a Git controlled dir, get the git
    root for purposes of adjusting paths.
    """
    git_cmd = ('%s rev-parse --show-toplevel' % git_exe).split(' ')
    git_p = Popen(git_cmd, stdout=PIPE)
    return git_p.communicate()[0].strip()

def prepare(root, git_exe):
    # first we have to get into the git repo to make the git_root work...
    os.chdir(root)
    # then we can change to the git root
    os.chdir(git_root(git_exe))
