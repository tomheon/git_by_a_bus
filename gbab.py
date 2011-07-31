#!/usr/bin/env python

import math
import sys
import os

from multiprocessing import Pool, Queue, Manager
from optparse import OptionParser, OptionGroup

from gbab.git_repo import GitRepo
from gbab.interest_res import parse_interest_regexps
from gbab.interest_res import interesting_fnames
from gbab.analyze import analyze
from gbab.summarize import summarize
from gbab.parse_history import parse_history
from gbab.render import render_summary

# used in workaround for multiprocessing bug
REALLY_LONG_TIME = 86400 * 10

def exit_with_error(err):
    print >> sys.stderr, "Error: " + err
    exit(1)

def main(options, args):
    # if the user has not specified a level of risk below which we
    # won't consider, default it to the default bus risk
    # cubed--another way to say it: we don't consider anything less
    # risky than three devs all getting hit by a bus in the same
    # timeframe.
    if options.risk_threshold is None:
        options.risk_threshold = math.pow(options.default_bus_risk, 3)

    options.num_analyzer_procs = int(options.num_analyzer_procs)
    options.num_git_procs = int(options.num_git_procs)    

    project_root = args[0]
    # need the realpath to work with symlinks
    project_root = os.path.realpath(project_root)
    
    # calculate the files to analyze
    interesting_res, not_interesting_res = parse_interest_regexps(options)

    repo = GitRepo(project_root, options.git_exe)
    
    fnames = interesting_fnames(repo, interesting_res, not_interesting_res)

    if not fnames:
        print >> sys.stderr, "No interesting files found, exiting."
        exit(1)

    # use queues for the various processes we will kick off to
    # communicate with each other.
    mgr = Manager()
    # the processes that parse the git history for each file will put
    # the histories into this queue for the next analyzer processes to
    # analyze
    analyzer_queue = mgr.Queue()
    # the analyzer processes will dump the analyses here for the
    # summarizer to summarize.
    summarizer_queue = mgr.Queue()

    # spin up the user-chosen number of git and analyzer proces, +1
    # process for the summarizer
    pool = Pool(options.num_analyzer_procs + options.num_git_procs + 1)

    # start the summarizer and have it wait for input on the summarizer queue.
    summarizer_result = pool.apply_async(summarize, 
                                          # where to write summaries
                                         (options.output_dir,
                                          # where to look for results to summarize
                                          summarizer_queue)) 

    analyzer_results = []
    for i in range(options.num_analyzer_procs):
        analyzer_results.append(pool.apply_async(analyze,
                                                 # i + 1 just used as
                                                 # an id to identify
                                                 # the analyzer in
                                                 # verbose output.
                                                 (i + 1, 
                                                  analyzer_queue, 
                                                  summarizer_queue,
                                                  options.departed_fname,
                                                  options.risk_threshold, 
                                                  options.default_bus_risk, 
                                                  options.bus_risk_fname,
                                                  options.knowledge_creation_constant,
                                                  options.verbose)))

    # start up the proces parse the history each file and dump them into the analyzer queue.
    fnames_with_args = [(project_root, 
                         fname, 
                         analyzer_queue, 
                         options.verbose) for fname in fnames]
    parse_history_result = pool.map_async(parse_history, 
                                          fnames_with_args, 
                                          # batch size, number of
                                          # procs set aside for git.
                                          options.num_git_procs)

    # wait for the diff parsers to finish parsing all
    # diffs--workaround to bug in multiprocessing...must specify a
    # wait to have terminate work correctly if we want to stop early.
    parse_results = parse_history_result.get(REALLY_LONG_TIME)

    # tell the analyzers it's time to quit when they are done with the
    # diffs currently in the queue by adding one None per analyzer to
    # the end of the queues.
    for i in range(options.num_analyzer_procs):
        analyzer_queue.put(None)
        
    print >> sys.stderr, \
        "Analyzed %d changes over %d files" % (sum([ar.get(REALLY_LONG_TIME) 
                                                    for ar in analyzer_results]),
                                               len(parse_results))

    # tell the summarizer queue to quit
    summarizer_queue.put(None)
    summary_db = summarizer_result.get(REALLY_LONG_TIME)
    
    # render the summary db and we're done.
    render_summary(project_root, summary_db, options.output_dir)
    
    print >> sys.stderr, "Done, summary is in %s/index.html" % options.output_dir


if __name__ == '__main__':
    usage = "usage: %prog [options] project_root_to_analyze"

    parser = OptionParser(usage=usage)

    input_group = OptionGroup(parser, "Input Options", 
                              "Options to instruct GBAB which files to analyze and how risky to consider different authors")
    input_group.add_option('--interesting', metavar="REGEXP", dest='interesting', action='append',
                      help='Regular expression to determine which files should be included in calculations.  ' + \
                      'May be repeated, any match is sufficient to indicate interest. ' + \
                      'Defaults are \.java$ \.cs$ \.py$ \.c$ \.cpp$ \.h$ \.hpp$ \.pl$ \.rb$')
    input_group.add_option('--not-interesting', metavar="REGEXP", dest="not_interesting", action='append',
                           help="Regular expression to override interesting files.  May be repeated, " + \
                               "any match is enough to squelch interest.")
    input_group.add_option("--case-sensitive", dest="case_sensitive", action="store_true", default=False,
                           help="Use case sensitive regexps when determining interesting files (default is case-insensitive")
    input_group.add_option('--departed-file', dest='departed_fname', metavar='FILE',
                           help='File listing departed devs, one per line')
    input_group.add_option('--bus-risk-file', dest='bus_risk_fname', metavar='FILE',
                           help='File of dev=float lines (e.g. ejorgensen=0.4) with custom bus risks for devs')
    input_group.add_option('--default-bus-risk', dest='default_bus_risk', default=0.1, metavar="FLOAT",
                           help='Default risk that a dev will be hit by a bus in your analysis timeframe (defaults to 0.1).')
    parser.add_option_group(input_group)

    proc_group = OptionGroup(parser, "Multiprocessing Options", 
                             "Options controlling how many processes GBAB spins up " + \
                                 "(try upping these if you have CPU / memory to spare and you " + \
                                 "are running against a large / old repository).")
    proc_group.add_option("--num-git-procs", metavar="NUMBER", dest="num_git_procs", default=3,
                          help="The number of git processes to run simultaneously (defaults to 3)")
    proc_group.add_option("--num-analyzer-procs", metavar="NUMBER", dest="num_analyzer_procs", default=3,
                          help="The number of analyzer processes to run (defaults to 3).")
    parser.add_option_group(proc_group)

    adv_group = OptionGroup(parser, "Advanced Tuning Options",
                            "Options to tune the GBAB algorithm")
    adv_group.add_option('--risk-threshold', dest='risk_threshold', default=None, metavar="FLOAT",
                         help="Threshold past which to summarize risk (defaults to default bus risk cubed)")
    adv_group.add_option('--knowledge-creation-constant', dest='knowledge_creation_constant', metavar='FLOAT', default=0.1,
                         help='How much knowledge a changed line should create if a new line creates 1 (defaults to 0.1)')
    parser.add_option_group(adv_group)


    parser.add_option('--git-exe', dest='git_exe', default='/usr/bin/env git',
                      help='Path to the git exe (defaults to "/usr/bin/env git")')
    parser.add_option('--verbose', dest='verbose', default=False, action="store_true", help="Print comforting output")
    parser.add_option('--output', dest='output_dir', metavar='DIRNAME', default='output',
                      help='Output directory for data files and html summary (defaults to "output"), error if already exists')
    
    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error("one project_root_to_analyze required, or pass -h for help.")

    try:
        os.mkdir(options.output_dir)
    except:
        exit_with_error("Output directory already exists, refusing to continue")

    main(options, args)
    
    
