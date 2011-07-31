import sqlite3

from gbab.summary_model import SummaryModel
from gbab.summary_renderer import SummaryRenderer

def render_summary(project_root, summary_db, output_dir):
    conn = sqlite3.connect(summary_db)
    renderer = SummaryRenderer(SummaryModel(conn), output_dir)
    renderer.render_all(project_root)
    conn.close()
