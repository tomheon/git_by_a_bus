import sys
import sqlite3

from gbab.line_model import LineModel
from gbab.risk_model import RiskModel
from gbab.knowledge_model import KnowledgeModel

def analyze(a_id, 
            inqueue, 
            outqueue,
            departed_fname,
            risk_threshold, 
            default_bus_risk, 
            bus_risk_fname,
            created_knowledge_constant,
            verbose):
    """
    Pull from inqueue until it returns None, analyzing each history
    coming in from inqueue and publishing the results to outqueue.

    This function is expected to be used when creating a new process,
    so keep the arguments simple base types.

    departed_fname: file with departed devs listed, one per line.

    risk_threshold: the risk below which no longer consider risky and
    can safely discard a risk.

    default_bus_risk: the default probability that a dev will be hit
    by a bus within the analysis timeframe.

    bus_risk_fname: the file in which to find the custom risks that a
    dev will get hit by a bus in the timeframe.

    created_knowledge_constont: if 1 represents the knowledge created
    when a new line is added, this is the knowledge created when a
    line is changed.

    verbose: print comforting output?

    What is inserted into outqueue is a tuple of the form:

    (project, repo_root, project_root, fname, [(line, [([author, ...], knowledge, risk, orphaned), ...])])
    """
    # since the risk model is only populated from files and is read
    # only, we can create it once per process and re-use it.
    risk_model = RiskModel(risk_threshold, default_bus_risk, bus_risk_fname, departed_fname)
    
    changes_processed = 0
    
    while True:
        args = inqueue.get()
        # None is the signal that we're finished analyzing and can
        # quit
        if args is None:
            break

        # we re-create the line model and the knowledge model each
        # time and then throw them away after extracting the final
        # pertinent information, since unlike the risk model they are
        # not read-only.
        conn = sqlite3.connect(':memory:')
        line_model =  LineModel(conn)
        knowledge_model = KnowledgeModel(conn, created_knowledge_constant, risk_model)

        repo_root, project_root, fname, entries = args
        
        for entry in entries:
            author, changes = entry
            for change in changes:
                changes_processed += 1
                if changes_processed % 1000 == 0 and verbose:
                    print >> sys.stderr, "Analyzer proc #%d applied change #%d" % (a_id, changes_processed)

                changetype, line_num, line = change
                line_model.apply_change(changetype, line_num, line)
                knowledge_model.apply_change(changetype, author, line_num)

        # pick up any remaining changes in the models
        conn.commit()
        outqueue.put(_condense_analysis(repo_root, project_root, fname, line_model, knowledge_model, risk_model))
        conn.close()
        
    return changes_processed

def _condense_analysis(repo_root, project_root, fname, line_model, knowledge_model, risk_model):
    """
    Return a tuple of the form:
    (repo_root, project_root, fname, [(line, [([author, ...], knowledge, risk, orphaned), ...])])
    """

    line_condensations = []

    for i, line in enumerate(line_model.get_lines()):
        line_num = i + 1
        author_knowledges = knowledge_model.knowledge_summary(line_num)
        # hold the (authors, knowledge, orphaned) for each knowledge
        # allocation against this line, calculating the orphaned as
        # needed.
        tmp = []
        for authors, knowledge in author_knowledges:
            orphaned = 0.0
            if all(risk_model.is_departed(author) for author in authors):
                orphaned = knowledge
            tmp.append((authors, knowledge, orphaned))

        # now calculate and add the risk, so it's (authors, knowledge,
        # risk, orphaned)
        author_knowledges = tmp
        author_knowledges.sort()
        author_knowledges = [(authors,
                              knowledge,
                              # knowledge at risk is the probability
                              # of all authors leaving times knowledge
                              # in the line.
                              risk_model.joint_bus_prob(authors) * knowledge,
                              orphaned) for (authors,
                                             knowledge,
                                             orphaned) in author_knowledges]

        line_condensations.append((line, author_knowledges))

    return (repo_root, project_root, fname, line_condensations)
        

