"""
Estimate the unique knowledge encpsulated in a single FileData line.

Currently uses a sequential strategy like so:

for each revision in the log:

* take the difference of the added and deleted lines of that revision.

* if the difference is positive, add those lines as knowledge for the
  dev that authored the revision.

* if the difference is negative, take the pct of the entire knowledge
  currently in the file represented by the number of negative lines
  and destroy that knowledge proportionally among all
  knowledge-holders.

* take the min of the added and deleted lines.  This represents the
  'churn'--lines that have changed.  Create (knowledge_churn_constant
  * churn) new lines worth of knowledge and assign it to the dev who
  authored the revision.  Take (churn - new_knowledge) lines of
  knowledge proportionally from all knowledge that dev doesn't share
  and move it to a shared account.
"""

import sys
import math
import copy

from optparse import OptionParser

from common import FileData

def sequential_create_knowledge(dev_uniq, dev, adjustment):
    """
    Create adjustment lines of knowledge in dev's account.

    dev is a list of developers who shared this knowledge (may be only
    one).
    """
    if dev not in dev_uniq:
        dev_uniq[dev] = 0
    dev_uniq[dev] += adjustment

def sequential_destroy_knowledge(adjustment, tot_knowledge, dev_uniq):
    """
    Find the percentage of tot_knowledge the adjustment represents and
    destroy that percent knowledge in all knowledge accounts.

    If tot_knowledge is 0, destroys nothing by definition.
    """
    pct_to_destroy = 0
    if tot_knowledge:
        pct_to_destroy = abs(float(adjustment)) / float(tot_knowledge)
    for devs in dev_uniq:
        k = dev_uniq[devs]
        k -= k * pct_to_destroy
        dev_uniq[devs] = k

def sequential_share_knowledge_group(dev, shared_key_exploded, pct_to_share, dev_uniq):
    """
    Share pct_to_share knowledge from all accounts that dev doesn't
    belong to into corresponding accounts dev does belong to.
    """
    old_shared_key = '\0'.join(shared_key_exploded)
    shared_key_exploded.append(dev)
    # make sure the dev names stay alphabetical
    shared_key_exploded.sort()
    new_shared_key = '\0'.join(shared_key_exploded)
    group_knowledge = dev_uniq[old_shared_key]
    amt_to_share = float(pct_to_share) * float(group_knowledge)
    dev_uniq[old_shared_key] -= amt_to_share
    if new_shared_key not in dev_uniq:
        dev_uniq[new_shared_key] = 0
    dev_uniq[new_shared_key] += amt_to_share

def sequential_distribute_shared_knowledge(dev, shared_knowledge, tot_knowledge, dev_uniq):
    """
    Share the percent of knowledge represented by shared_knowledge of
    tot_knowledge from all accounts that dev doesn't belong to into
    (possibly new) accounts that he does.
    """
    pct_to_share = 0
    if tot_knowledge:
        pct_to_share = float(shared_knowledge) / float(tot_knowledge)
    for shared_key in dev_uniq.keys():
        shared_key_exploded = shared_key.split('\0')
        if dev not in shared_key_exploded:
            sequential_share_knowledge_group(dev, shared_key_exploded, pct_to_share, dev_uniq)

def sequential_estimate_uniq(fd, knowledge_churn_constant):
    """
    Estimate the amounts of unique knowledge for each developer who
    has made changes to the path represented by this FileData, using a
    knowledge_churn_constant indicating what pct of churned lines to
    treat as new knowledge.

    Returns a list of [([dev1, dev2...], knowledge), ...], indicating
    the knowledge shared uniquely by the group of devs in the first
    field (there may be only dev in the list or many)
    """
    tot_knowledge = 0
    dev_uniq = {}

    for dev, added, deleted in fd.dev_experience:
        adjustment = added - deleted
        if adjustment > 0:
            sequential_create_knowledge(dev_uniq, dev, adjustment)
        elif adjustment < 0:
            sequential_destroy_knowledge(adjustment, tot_knowledge, dev_uniq)
        churn = min(added, deleted)
        if churn != 0:
            new_knowledge = float(churn) * knowledge_churn_constant
            shared_knowledge = float(churn) - new_knowledge
            sequential_distribute_shared_knowledge(dev, shared_knowledge, tot_knowledge, dev_uniq)
            sequential_create_knowledge(dev_uniq, dev, new_knowledge)            
        tot_knowledge += adjustment + (churn * knowledge_churn_constant)

    dev_uniq = [(shared_key.split('\0'), shared) for shared_key, shared in dev_uniq.items()]
    
    return dev_uniq, int(tot_knowledge)
 
def sequential(lines, model_args):
    """
    Entry point for the sequential algorithm.

    See the description in the file docs.

    Yields FileData objects as tsv lines, with dev_uniq and
    tot_knowledge fields filled in.
    """
    knowledge_churn_constant = float(model_args[0])
    for line in lines:
        fd = FileData(line)
        dev_uniq, tot_knowledge = sequential_estimate_uniq(fd, knowledge_churn_constant)
        fd.dev_uniq = dev_uniq
        fd.tot_knowledge = tot_knowledge
        yield fd.as_line()

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--model', dest='model', metavar='MODEL[:MARG1[:MARG2]...]', default="sequential:0.1",
                      help='Knowledge model to use, with arguments.')
    options, args = parser.parse_args()

    model = options.model.split(':')
    model_func = locals()[model[0]]
    model_args = model[1:]
    
    for line in model_func(sys.stdin, model_args):
        print line
