import math
import os
import errno
import cgi

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
        self._render_index_page(project_root)
        #for file_id, fname in self.summary_model.project_files(project_root): 
        #    self._render_file_page(file_id, fname)

    # implementation

    def _render_index_page(self, project_root):
        with open(os.path.join("%s/index.html" % self.files_dir), "w") as fil:
            summary_str = "Git by a Bus Summary for Project %s" % cgi.escape(os.path.basename(project_root))
            fil.write("<html>\n<head>\n<title>%s</title>\n</head>\n" % summary_str)
            fil.write("<body>\n")
            fil.write("<h1>%s</h1>" % summary_str)
            self._render_total_stats(fil)
            self._render_riskiest_authors(fil)
            self._render_riskiest_files(fil)
            fil.write("</body>\n</html>\n")

    def _render_total_stats(self, fil):
        tot_knowledge = self.summary_model.total_knowledge()
        fil.write("<p>Total knowledge: %d over %d files</p>" % (tot_knowledge,
                                                                self.summary_model.count_files()))
        tot_risk = self.summary_model.total_risk()
        fil.write("<p>At risk: %d (%.2f percent)</p>" % (tot_risk,
                                                         float(tot_risk) / float(tot_knowledge) * 100.0))

        tot_orphaned = self.summary_model.total_orphaned()
        fil.write("<p>Orphaned: %d (%.2f percent)</p>" % (tot_orphaned,
                                                         float(tot_orphaned) / float(tot_knowledge) * 100.0))

    def _render_riskiest_files(self, fil):
        fil.write("<p>Top %d files by risk</p>" % NUM_RISKIEST_FILES)
        fil.write("<table>\n<tr>\n<th>File</th>\n<th>Risk</th>\n</tr>\n")
        for (fid, risk) in self.summary_model.fileids_with_risk(top=NUM_RISKIEST_FILES):
            fil.write("<tr>\n<td>%s</td>\n<td>%d</td>\n</tr>\n" % (self.summary_model.fpath(fid), int(risk)))
        fil.write("</table>")
        
    def _render_riskiest_authors(self, fil):
        fil.write("<p>Top %d authors/groups by (bus_risk * knowledge)</p>" % NUM_RISKIEST_AUTHORS)
        fil.write("<table>\n<tr>\n<th>Author(s)</th>\n<th>Bus Risk * Knowledge</th>\n</tr>\n")
        for (authstr, risk) in self.summary_model.authorgroups_with_risk(top=NUM_RISKIEST_AUTHORS):
            fil.write("<tr>\n<td>%s</td>\n<td>%d</td>\n</tr>\n" % (authstr, int(risk)))
        fil.write("</table>")
            
    def _create_files_dir(self):
        self.files_dir = os.path.join(self.output_dir, 'files')

        try:
            os.mkdir(self.files_dir)
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                pass
            else: 
                raise
            

    def _render_file_page(self, file_id, fname):
        summarized_lines = self.summary_model.file_lines(file_id)

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
    project_root = os.path.realpath(sys.argv[2])
    db_path = os.path.join(output_dir, 'summary.db')
    conn = sqlite3.connect(db_path)
    summary_model = SummaryModel(conn)
    summary_renderer = SummaryRenderer(summary_model, output_dir)
    summary_renderer.render_all(project_root)
    
    
