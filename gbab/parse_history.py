import sys

from gbab.git_repo import GitRepo
from gbab.diff_walker import DiffWalker

def parse_history(args):
    """
    args is a tuple of the form

    (project, project_root, fname, queue, verbose)

    Run git, parsing the log and putting the resulting log / diff
    entries into queue for analysis by the analyzer.
    """
    project_root, fname, queue, verbose = args
    repo = GitRepo(project_root, '/usr/bin/env git')
    entries = repo.log(fname)
    repo_root = repo.git_root()
    results = []
    diff_walker = DiffWalker()

    if verbose:
        print >> sys.stderr, "Parsing history for %s" % fname

    try:
        queue.put((repo_root, project_root, fname, [(author.strip(), diff_walker.walk(diff)) for (author, diff) in entries]))
    except:
        print >> sys.stderr, "error", fname
    return True
