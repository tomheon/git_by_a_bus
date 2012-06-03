import sqlite3
import os

from gbab.summary_model import SummaryModel

def summarize(output_dir, queue):
    """
    Read from queue until receiving None, taking the results from the
    queue read and summarizing them into a db called summary.db in
    output_dir.
    """
    db_fname = os.path.join(output_dir, 'summary.db')
    conn = sqlite3.connect(db_fname)
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode = OFF')
    cursor.execute('PRAGMA synchronous = OFF')
    cursor.close()
    summary_model = SummaryModel(conn)
    
    while True:
        condensed_analysis = queue.get()
        if condensed_analysis is None:
            break
        summary_model.summarize(condensed_analysis)
    return db_fname
