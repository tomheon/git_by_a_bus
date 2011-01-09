import sqlite3
import math
import sys
import os
import re

from multiprocessing import Pool, Queue, Manager
from optparse import OptionParser

from gbab.git_repo import GitRepo
from gbab.diff_walker import DiffWalker
from gbab.sqlite_knowledge_model import SqliteKnowledgeModel
from gbab.risk_model import RiskModel
from gbab.sqlite_line_model import SqliteLineModel

# used in workaround for multiprocessing bug
REALLY_LONG_TIME = 86400 * 10

def exit_with_error(err):
    print >> sys.stderr, "Error: " + err
    exit(1)

def parse_history(args):
    project, project_root, fname, queue, verbose = args
    repo = GitRepo(project_root, '/usr/bin/env git')
    entries = repo.log(fname)
    results = []
    diff_walker = DiffWalker()

    if verbose:
        print >> sys.stderr, "Parsing history for %s" % fname

    try:
        queue.put((project, project_root, fname, [(author, diff_walker.walk(diff)) for (author, diff) in entries]))
    except:
        print >> sys.stderr, "error", fname
    return True

def summarize(output_dir, queue):
    while True:
        x = queue.get()
        if x is None:
            break
    return "summary.db"

def analyze(a_id, inqueue, outqueue, departed_fname,
            risk_threshold, default_bus_risk, bus_risk_fname,
            created_knowledge_constant,
            verbose):
    i = 0
    
    while True:
        x = inqueue.get()
        if x is None:
            break
        conn = sqlite3.connect(':memory:')
        line_model =  SqliteLineModel(conn)
        risk_model = RiskModel(risk_threshold, default_bus_risk, departed_fname, bus_risk_fname)
        knowledge_model = SqliteKnowledgeModel(conn, created_knowledge_constant, risk_model)

        project, project_root, fname, entries = x
        for entry in entries:
            author, changes = entry
            for change in changes:
                i += 1
                if i % 1000 == 0 and verbose:
                    print >> sys.stderr, "Analyzer proc #%d applied change #%d" % (a_id, i)
                changetype, line_num, line = change
                if changetype == 'changed':
                    line_id = line_model.lookup_line_id(project, fname, line_num)
                    line_model.change_line(line_id, line)        
                    knowledge_model.line_changed(author, line_id)
                elif changetype == 'added':
                    line_id = line_model.add_line(project, fname, line_num, line)
                    knowledge_model.line_added(author, line_id)
                elif changetype == 'deleted':
                    line_id = line_model.lookup_line_id(project, fname, line_num)
                    line_model.remove_line(line_id)
                    knowledge_model.line_removed(author, line_id)

        outqueue.put("tbd summary")

        conn.commit()
        conn.close()
        
    return i

def _parse_interest_regexps(options):
    interesting = options.interesting
    not_interesting = options.not_interesting or []

    if options.case_sensitive:
        interesting = [re.compile(i) for i in interesting]
        not_interesting = [re.compile(n) for n in not_interesting]
    else:
        interesting = [re.compile(i, re.IGNORECASE) for i in interesting]
        not_interesting = [re.compile(n, re.IGNORECASE) for n in not_interesting]

    return interesting, not_interesting

def _is_interesting(fname, interesting, not_interesting):
    if not fname.strip():
        return False
    has_my_interest = any([i.search(fname) for i in interesting])
    if has_my_interest:
        has_my_interest = not any([n.search(fname) for n in not_interesting])
    return has_my_interest

def _interesting_fnames(repo, interesting, not_interesting):
    return [fname for fname in repo.ls() if _is_interesting(fname, interesting, not_interesting)]

def _render_summary(summary_db, output_dir):
    pass

def main(options, args):
    if options.risk_threshold is None:
        options.risk_threshold = math.pow(options.default_bus_risk, 3)

    options.num_analyzer_procs = int(options.num_analyzer_procs)
    options.num_git_procs = int(options.num_git_procs)    

    project_root = args[0]
    
    # calculate the files to analyze
    interesting, not_interesting = _parse_interest_regexps(options)

    repo = GitRepo(project_root, options.git_exe)
    
    fnames = _interesting_fnames(repo, interesting, not_interesting)
    
    mgr = Manager()
    analyzer_queue = mgr.Queue()
    summarizer_queue = mgr.Queue()

    # user-chosen procs +1 process for the summarizer
    pool = Pool(options.num_analyzer_procs + options.num_git_procs + 1)

    summarizer_result = pool.apply_async(summarize, (options.output_dir, summarizer_queue))

    analyzer_results = []
    for i in range(options.num_analyzer_procs):
        analyzer_results.append(pool.apply_async(analyze,
                                                 (i + 1, analyzer_queue, summarizer_queue,
                                                  options.departed_fname,
                                                  options.risk_threshold, options.default_bus_risk, options.bus_risk_fname,
                                                  options.knowledge_creation_constant,
                                                  options.verbose)))

    fnames = [('project_name', project_root, fname, analyzer_queue, options.verbose) for fname in fnames]
    parse_history_result = pool.map_async(parse_history, fnames, 20)

    # wait for the diff parsers to finish parsing all
    # diffs--workaround to bug in multiprocessing...must specify a
    # wait to have terminate work correctly
    parse_results = parse_history_result.get(REALLY_LONG_TIME)

    # tell the analyzers it's time to quit when they are done with the
    # diffs currently in the queue
    for i in range(options.num_analyzer_procs):
        analyzer_queue.put(None)
        
    print >> sys.stderr, "Analyzed %d changes over %d files" % (sum([ar.get(REALLY_LONG_TIME) for ar in analyzer_results]),
                                                                len(parse_results))

    # tell the summarizer queue to quit
    summarizer_queue.put(None)
    summary_db = summarizer_result.get(REALLY_LONG_TIME)
    
    _render_summary(summary_db, options.output_dir)
    
    print >> sys.stderr, "Done, summary is in %s/index.html" % options.output_dir


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--departed-file', dest='departed_fname', metavar='FILE',
                      help='File listing departed devs, one per line')
    parser.add_option('--bus-risk-file', dest='bus_risk_fname', metavar='FILE',
                      help='File of dev=float lines (e.g. ejorgensen=0.4) with custom bus risks for devs')
    parser.add_option("--num-git-procs", metavar="NUMBER", dest="num_git_procs", default=3,
                      help="The number of git processes to run simultaneously (defaults to 3)")
    parser.add_option("--num-analyzer-procs", metavar="NUMBER", dest="num_analyzer_procs", default=3,
                      help="The number of analyzer processes to run (defaults to 3).")
    parser.add_option('--interesting', metavar="REGEXP", dest='interesting', action='append',
                      help='Regular expression to determine which files should be included in calculations.  ' + \
                      'May be repeated, any match is sufficient to indicate interest. ' + \
                      'Defaults are \.java$ \.cs$ \.py$ \.c$ \.cpp$ \.h$ \.hpp$ \.pl$ \.rb$',
                      default=r'\.java$ \.cs$ \.py$ \.c$ \.cpp$ \.h$ \.hpp$ \.pl$ \.perl$ \.rb$ \.sh$'.split(' '))
    parser.add_option('--not-interesting', metavar="REGEXP", dest="not_interesting", action='append',
                      help="Regular expression to override interesting files.  May be repeated, any match is enough to squelch interest.")
    parser.add_option("--case-sensitive", dest="case_sensitive", action="store_true", default=False,
                      help="Use case sensitive regexps when determining interesting files (default is case-insensitive")
    parser.add_option('--git-exe', dest='git_exe', default='/usr/bin/env git',
                      help='Path to the git exe (defaults to "/usr/bin/env git")')
    parser.add_option('--default-bus-risk', dest='default_bus_risk', default=0.1, metavar="FLOAT",
                      help='Default risk that a dev will be hit by a bus in your analysis timeframe (defaults to 0.1).')
    parser.add_option('--risk-threshold', dest='risk_threshold', default=None, metavar="FLOAT",
                      help="Threshold past which to summarize risk (defaults to default bus risk cubed)")
    parser.add_option('--knowledge-creation-constant', dest='knowledge_creation_constant', metavar='FLOAT', default=0.1,
                      help='How much knowledge a changed line should create if a new line creates 1 (defaults to 0.1)')
    parser.add_option('--verbose', dest='verbose', default=False, action="store_true", help="Print comforting output")
    parser.add_option('--output', dest='output_dir', metavar='DIRNAME', default='output',
                      help='Output directory for data files and html summary (defaults to "output"), error if already existsp')
    
    options, args = parser.parse_args()

    try:
        os.mkdir(options.output_dir)
    except:
        exit_with_error("Output directory already exists, refusing to continue")

    main(options, args)
    
    
