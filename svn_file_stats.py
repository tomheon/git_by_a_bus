"""
Hackish module to use svn for generating file stats.

The only function here intended for external consumption is gen_stats.

Output of gen_stats should be exactly the same as the output of
git_file_stats.gen_stats, but in practice they may differ by a line or
two (appears to be whitespace handling, perhaps line endings?)
"""

import sys
import os
import re

import pysvn

from common import is_interesting, FileData, safe_author_name

def gen_stats(root, project, interesting, not_interesting, options):
    """
    root: the root svn url of the project we are generating stats for
    (does not need to be the root of the svn repo).  Must be a url,
    not a checkout path.

    project: the project identifier.

    interesting: regular expressions that indicate an interesting path
    if they match

    not_interesting: regular expressions that trump interesting and
    indicate a path is not interesting.

    options: currently unused, options from gen_file_stats.py's main.

    Yields FileData objects encoded as tsv lines.  Only the fname,
    dev_experience and cnt_lines fields are filled in.
    """
    client = pysvn.Client()

    # we need the repo root because the paths returned by svn ls are relative to the repo root,
    # not our project root
    repo_root = client.root_url_from_path(root)

    interesting_fs = [f[0].repos_path for f in client.list(root, recurse=True) if
                      is_interesting(f[0].repos_path, interesting, not_interesting) and f[0].kind == pysvn.node_kind.file]

    for f in interesting_fs:
        dev_experience = parse_dev_experience(f, client, repo_root)
        if dev_experience:
            fd = FileData(':'.join([project, f]))
            # don't take revisions that are 0 lines added and 0 removed, like properties
            fd.dev_experience = [(dev, added, removed) for dev, added, removed in dev_experience if added or removed]
            fd.cnt_lines = count_lines(f, client, repo_root)
            fd_line = fd.as_line()
            if fd_line.strip():
                yield fd_line

def parse_dev_experience(f, client, repo_root):
    """
    f: a path relative to repo_root for a file from whose log we want
    to parse dev experience.

    client: the pysvn client

    repo_root: the root of the svn repository
    """
    # a list of tuples of form (dev, added_lines, deleted_lines), each
    # representing one commit
    dev_experience = []

    # a list of tuples with the paths / revisions we want to run diffs
    # on to reconstruct dev experience
    comps_to_make = []

    # since the name of the file can change through its history due to
    # moves, we need to keep the most recent one we're looking for
    fname_to_follow = f

    added_line_re = re.compile(r'^\+')
    
    # strict_node_history=False: follow copies
    #
    # discover_changed_paths: make the data about copying available in the changed_paths field
    for log in client.log("%s%s" %(repo_root, f), strict_node_history=False, discover_changed_paths=True):
        cp = log.changed_paths

        # even though we are only asking for the log of a single file,
        # svn gives us back all changed paths for that revision, so we
        # have to look for the right one
        for c in cp:
            if fname_to_follow == c.path:
                # since we're going back in time with the log process,
                # a copyfrom_path means we need to follow the old file
                # from now on.
                if c.copyfrom_path:
                    fname_to_follow = c.copyfrom_path                    
                comps_to_make.append((c.path, log.revision, log.author))
                break

    # our logic needs oldest logs first
    comps_to_make.reverse()

    # for the first revision, every line is attributed to the first
    # author as an added line
    txt = client.cat("%s%s" % (repo_root, comps_to_make[0][0]),
                     comps_to_make[0][1])

    exp = txt.count('\n')
    if not txt.endswith('\n'):
        exp += 1
    dev_experience.append((comps_to_make[0][2], exp, 0))

    # for all the other entries, we must diff between revisions to
    # find the number and kind of changes
    for i in range(len(comps_to_make) - 1):
        old_path = "%s%s" % (repo_root, comps_to_make[i][0])
        old_rev = comps_to_make[i][1]

        new_path = "%s%s" % (repo_root, comps_to_make[i + 1][0])
        new_rev = comps_to_make[i + 1][1]
        
        author = comps_to_make[i + 1][2]
        
        try:
            diff = client.diff('.',
                               old_path,
                               revision1=old_rev,
                               url_or_path2=new_path,
                               revision2=new_rev,
                               diff_options=['-w'])
            diff = diff.split('\n')
            ind_dbl_ats = 0
            for i, line in enumerate(diff):
                if line.startswith('@@'):
                    ind_dbl_ats = i
                    break
            added = 0
            removed = 0
            for line in diff[ind_dbl_ats:]:
                if line.startswith('+'):
                    added += 1
                if line.startswith('-'):
                    removed += 1
            dev_experience.append((safe_author_name(author), added, removed))
        except:
            # on one occasion I saw a non-binary item that existed in
            # the filesystem with svn ls but errored out with a diff
            # against that revision.  Note the error and proceed.
            print >> sys.stderr, "Error diffing %s %s and %s %s: " % \
                  (old_path, str(old_rev), new_path, str(new_rev)), sys.exc_info()[0]
        
    return dev_experience

def count_lines(f, client, repo_root):
    """
    Count the lines in the file located at path f under repo root.
    """
    txt = client.cat("%s%s" % (repo_root, f))
    lines = txt.count('\n')
    if not txt.endswith('\n'):
        lines += 1
    return lines

    

    
