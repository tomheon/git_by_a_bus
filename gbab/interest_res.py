import re

DEFAULT_INTERESTING_RES = r'\.java$ \.cs$ \.py$ \.c$ \.cpp$ \.h$ \.hpp$ \.pl$ \.perl$ \.rb$ \.sh$ \.js$'

def parse_interest_regexps(options):
    """
    Given command line options, generate a list of regexps which
    interesting_res files should match, or a list of files that
    uninteresting files should match.

    return (interesting_res, uninteresting_res)
    """
    interesting_res = options.interesting or DEFAULT_INTERESTING_RES.split(' ')
    not_interesting_res = options.not_interesting or []

    if options.case_sensitive:
        interesting_res = [re.compile(i) for i in interesting_res]
        not_interesting_res = [re.compile(n) for n in not_interesting_res]
    else:
        interesting_res = [re.compile(i, re.IGNORECASE) for i in interesting_res]
        not_interesting_res = [re.compile(n, re.IGNORECASE) for n in not_interesting_res]

    return interesting_res, not_interesting_res

def _is_interesting(fname, interesting_res, not_interesting_res):
    """
    Is the fname interesting?

    It is if it matches at least one of the interesting_res, and none
    of the not_interesting_res.
    """
    if not fname.strip():
        return False
    has_my_interest = any([i.search(fname) for i in interesting_res])
    if has_my_interest:
        has_my_interest = not any([n.search(fname) for n in not_interesting_res])
    return has_my_interest

def interesting_fnames(repo, interesting_res, not_interesting_res):
    """
    Get a list of interesting fnames from the repo, where
    'interesting' means 'matching at least one of interesting_res, and
    none of not_interesting_res'.
    """
    return [fname for fname in repo.ls() if _is_interesting(fname, interesting_res, not_interesting_res)]
