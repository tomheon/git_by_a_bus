import math
import os

class SummaryRenderer(object):

    def __init__(self, summary_model, output_dir):
        self.summary_model = summary_model
        self.output_dir = output_dir

    def render_all(self):
        for file_id, fname in self.summary_model.project_files('project_name'): 
            self._render_file_page(file_id, fname)

    # implementation

    def _render_file_page(self, file_id, fname):
        summarized_lines = self.summary_model.file_lines(file_id)

        try:
            os.mkdir(os.path.join(self.output_dir, 'files'))
        except:
            pass
        
        with open(os.path.join(self.output_dir, 'files', "%d.html" % file_id), "w") as fil:
            fil.write("<html>\n<head></head>\n<body>")
            fil.write("<table>\n<tr><th>Heatmap</th><th>Line</th></tr>\n")
            for summarized_line in summarized_lines:
                knowledge, risk, orphaned, line = summarized_line
                line = line.decode('utf-8').replace('\t', '    ').replace(' ', '&nbsp;')
                to_write = "<tr><td>%s</td><td>%s</td></tr>\n" % (self._heatmap(knowledge, risk, orphaned), line)
                to_write = to_write.encode('utf-8')
                fil.write(to_write)
                #            except:
                #                import sys
                #                print >> sys.stderr, "%s ERROR2" % fname
                #                print >> sys.stderr, line
                #                print >> sys.stderr, sys.exc_info()[0]
            fil.write('</table>\n')
            fil.write("</body></html>")

    def _heatmap(self, knowledge, risk, orphaned):
        risk_width = (risk / (knowledge + orphaned)) * 100
        orphan_width = (orphaned / (knowledge + orphaned)) * 100
        s = '<table><tr>'
        #risk_s = '<td width="100"><div style="width: %d%%; background-color: red; float: right;">%d</div></td>' % (int(risk_width), int(risk_width))
        #orphan_s = '<td width="100"><div style="width: %d%%; background-color: green;">%d</div></td>' % (int(orphan_width), int(orphan_width))
        risk_s = "<td>%d</td>" % risk_width
        orphan_s = "<td>%d</td>" % orphan_width        
        close_s = '</tr></table>'
        return ''.join([s, risk_s, orphan_s, close_s])

if __name__ == '__main__':
    import sys
    from gbab.summary_model import SummaryModel
    import sqlite3
    import os

    output_dir = sys.argv[1]
    db_path = os.path.join(output_dir, 'summary.db')
    conn = sqlite3.connect(db_path)
    summary_model = SummaryModel(conn)
    summary_renderer = SummaryRenderer(summary_model, output_dir)
    summary_renderer.render_all()
    
    
