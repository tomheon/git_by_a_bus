"""
Generate file stats for all interesting files in a project using git (default) or svn.

Run python gen_file_stats.py -h for options.

Prints FileData objects encoded as tsv lines to stdout.  Only the
fname, dev_experience and cnt_lines fields are filled in.
"""

import os
import re

from optparse import OptionParser

import git_file_stats

if __name__ == '__main__':
    usage = "usage: %prog [options] git_controlled_path[=project_name]"
    parser = OptionParser()
    parser.add_option('-i', '--interesting', metavar="REGEXP", dest='interesting', action='append',
                      help='Regular expression to determine which files should be included in calculations.  ' + \
                      'May be repeated, any match is sufficient to indicate interest. ' + \
                      'Defaults are \.java$ \.cs$ \.py$ \.c$ \.cpp$ \.h$ \.hpp$ \.pl$ \.rb$ \.sh$',
                      default=[])
    parser.add_option('-n', '--not-interesting', metavar="REGEXP", dest="not_interesting", action='append',
                      help="Regular expression to override interesting files.  May be repeated, any match is enough to squelch interest.")
    parser.add_option('--case-sensitive', dest='case_sensitive', action='store_true', default=False,
                      help='Use case-sensitive regepxs when finding interesting / uninteresting files (defaults to case-insensitive)')
    parser.add_option('--git-exe', dest='git_exe', default='/usr/bin/env git',
                      help='Path to the git exe (defaults to "/usr/bin/env git")')
    parser.add_option('--svn', dest='use_svn', default=False, action='store_true',
                      help='Use svn intead of git to generate file statistics.  This requires you to install pysvn.')

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error("You must pass a single git controlled path as the argument.")
        
    path_project = args[0].split('=')

    project = None
    root = path_project[0]

    if len(path_project) > 1:
        project = path_project[1]
    else:
        # if they don't specify a project name, use the last piece of
        # the root.
        project = os.path.split(root)[1]

    interesting = options.interesting or r'\.java$ \.cs$ \.py$ \.c$ \.cpp$ \.h$ \.hpp$ \.pl$ \.rb$ \.sh$'.split(' ')
    not_interesting = options.not_interesting or []

    if options.case_sensitive:
        interesting = [re.compile(i) for i in interesting]
        not_interesting = [re.compile(n) for n in not_interesting]
    else:
        interesting = [re.compile(i, re.IGNORECASE) for i in interesting]
        not_interesting = [re.compile(n, re.IGNORECASE) for n in not_interesting]

    gen_stats = git_file_stats.gen_stats

    if options.use_svn:
        # only run the import if they actually try to use svn, since
        # we don't want to import pysvn and fail if we don't have to.
        import svn_file_stats
        gen_stats = svn_file_stats.gen_stats
    
    for line in gen_stats(root, project, interesting, not_interesting, options):
        if line.strip():
            print line
