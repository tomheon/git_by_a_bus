import math
import os
import errno
import cgi
import json

# max number of risky authors to write in summmary
NUM_RISKIEST_AUTHORS = 10

# max number of risky files to write in summmary
NUM_RISKIEST_FILES = 10


class SummaryRenderer(object):

    def __init__(self, summary_model, output_dir):
        self.summary_model = summary_model
        self.output_dir = output_dir

    def render_all(self, project_root):
        self._create_files_dir()
        self._render_summary_json(project_root)
        self._render_file_json(project_root)

    # implementation

    def _render_summary_json(self, project_root):
        with open(os.path.join(self.files_dir, 'summary.json'), "wb") as fil:
            fil.write(json.dumps(self.summary_model.project_summary(project_root), indent=4))

    def _render_file_json(self, project_root):
        for fileid, fname in self.summary_model.project_files(project_root):
            with open(os.path.join(self.files_dir, '%s.json' % str(fileid)), "wb") as fil:
                fil.write(json.dumps(self.summary_model.file_summary(fileid), indent=4))

    def _create_files_dir(self):
        self.files_dir = os.path.join(self.output_dir, 'files')

        try:
            os.mkdir(self.files_dir)
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                pass
            else:
                raise


if __name__ == '__main__':
    import sys
    from gbab.summary_model import SummaryModel
    import sqlite3
    import os

    output_dir = sys.argv[1]
    project_root = os.path.realpath(sys.argv[2])
    db_path = os.path.join(output_dir, 'summary.db')
    conn = sqlite3.connect(db_path)
    summary_model = SummaryModel(conn)
    summary_renderer = SummaryRenderer(summary_model, output_dir)
    summary_renderer.render_all(project_root)


