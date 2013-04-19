# Git by a Bus: Estimate unique and at-risk knowledge in your source code.

## History

I originally developed Git by a Bus at HubSpot, who kindly allowed me
to open source it.

Motivation and description of the algorithm are here:

http://dev.hubspot.com/bid/57694/Git-by-a-Bus

## Bugs

If you find any, let me know on github or by email at
edmund@hut8labs.com

## Installation and Dependencies

The entire project is written in python, known to work with 2.6.1 and
2.6.5. The python isn't very exotic, so it may work with earlier
versions as well. Let me know if you problems or successes with other
versions.

Git by a Bus requires a locally executable git (unless you are using
svn) and local git repositories of each project you want to analyze.

If you are using the experimental svn support, you must have pysvn
installed and available in your PYTHONPATH (to test try running python
from the command line and 'import pysvn'.  If it works you should be
all set).  I've tested with pysvn version 1.7.4, but again the usage
of pysvn isn't very exotic, so earlier versions might work.  You
should see the subversion notes below if you really want to use svn.

## Running

The driver file is git_by_a_bus.py, which you should run with "python
git_by_a_bus.py <paths to projects>". Run it with the -h flag to get a
list of options and more detailed usage. See the partial re-runs
section below for tips about cheaper re-runs.

## Output

The git_by_a_bus.py driver runs the following scripts in sequence:

* gen_file_stats.py

* estimate_unique_knowledge.py

* estimate_file_risk.py

* summarize.py

Each produces a corresponding tsv in the output directory (e.g.
gen_file_stats.py produces output/gen_file_stats.tsv), which is used
as input to the next step.

The summarize.py file produces an html summary in output/index.html
and output/{devs,projects,files}.

## Partial Re-Runs

Sometimes you want to re-run with a different set of bus risks or
lists of departed devs.  Or maybe you want to exclude some files you
forgot to mark as uninteresting and crunch again.  Given that the
gen_file_stats.py step is by far the slowest, you might want to try a
little file manipulation to speed up the process.

If you run with the -c flag, git_by_a_bus.py will only try to
regenerate missing files. So for example you could adjust the contents
of output/gen_file_stats.tsv, remove all the other tsvs in output, and
run the git_by_a_bus.py command again with an added -c flag, in which
case git_by_a_bus.py will notice the existing gen_file_stats.tsv and
not attempt to re-generate it.  See the output section above for a
full list of outputs.

## Subversion Notes

Git by a Bus has experimental support for svn.  It uses svn urls
instead of local repositories, and it's orders of magnitude slower
than the git version.  For example, a moderately sized local
repository here at HubSpot takes about 2 minutes to anazlyze using
git, and about 90 minutes to analyze using svn.  It also puts a fair
amount of strain on the svn server, as it has to run a full log for
each file and a diff between each sequential version of each file.

If you have an svn repository you want to analyze, I suggest using
"git svn" to convert the svn repository to git and then analyzing the
git repository, since it will be much faster on repeated runs. The git
svn bridge puts a fair amount of load on the svn server during
conversion as well, so for large and busy repos you might want to
consider making a local copy with svnadmin hotcopy and then converting
to git from the copy.
