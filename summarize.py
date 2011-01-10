"""
Hackish script to generate summary html for file risk data.

Puts the results in output_dir/{devs,files,projects}, with an index at
output_dir/index.html
"""

import sys
import os
import math

from optparse import OptionParser

from common import FileData, parse_departed_devs

# we cut off any value below this as just noise.
GLOBAL_CUTOFF = 10

class Dat(object):
    """
    A single piece of data for the aggregate routines to aggregate,
    using the a_* fields to grab the appropriate keys.
    """
    
    def __init__(self, valtype, file_data, dev, val):
        """
        valtype: arbitrary string indicating the type of the data

        file_data: the FileData object

        dev: the group of 1 or more developers associated with this
        value

        val: the value
        """
        self.valtype = valtype
        self.file_data = file_data
        self.dev = dev
        self.val = val

    def __repr__(self):
        return "valtype: %s, file_data: %s, dev: %s, val: %s " % (self.valtype,
                                                                  self.file_data,
                                                                  self.dev,
                                                                  str(self.val))

# a_* methods.
#
# Used as keys to identify an aggregate (e.g. an aggregate by dev, valtype, and project would be filed under:
#
# (a_dev, a_valtype, a_project)
#
# Then invoked on the aggregate hash to navigate to the appropriate
# destinations / sources of values.

def a_unique(dat):
    return 'unique'

def a_orphaned(dat):
    return 'orphaned'

def a_dev(dat):
    if isinstance(dat.dev, list):
        return ' and '.join(dat.dev)
    else:
        return dat.dev

def a_project(dat):
    return dat.file_data.project

def a_fname(dat):
    return dat.file_data.fname

def a_valtype(dat):
    return dat.valtype

def agg(path, diction, dat):
    """
    dat has the value to aggregate and the data associated with the value (FileData, devs)

    path is a series of a_* keys return values to walk to the right
    point in the aggregation.

    diction is the dictionary to aggregate the value into
    """
    
    orig = diction
    # walk the dictionary to the last key
    for p in path[:-1]:
        k = p(dat)
        if k not in diction:
            diction[k] = {}
        diction = diction[k]

    # aggregate the val
    last_p = path[-1]
    last_k = last_p(dat)
    if last_k not in diction:
        diction[last_k] = 0
    diction[last_k] += dat.val

def agg_all(aggs, dat):
    for path, diction in aggs.items():
        agg(path, diction, dat)

def create_agg(aggs, path):
    aggs[path] = {}

def split_out_dev_vals(dev_vals, departed_devs):
    """
    Split the values in dev_vals into those that are held by only
    non-departed devs and those held by departed devs.

    If value held by departed devs can be aggregated into value held
    by non-departed devs, do so.

    return two lists: the first the values held by non-departed devs,
    the second the values held by departed devs.
    """

    def is_departed(dev):
        return dev in departed_devs

    def is_not_departed(dev):
        return dev not in departed_devs

    def add_dev_val_lookup(devs, lookup, val):
        devs.sort()
        lookup_str = '\0'.join(devs)
        if lookup_str not in lookup:
            lookup[lookup_str] = 0
        lookup[lookup_str] += val
    
    lookup = dict([('\0'.join(devs), val) for (devs, val) in dev_vals])
    departed_lookup = {}
    
    for devs, val in dev_vals:
        present = filter(is_not_departed, devs)
        departed = filter(is_departed, devs)
        if departed:
            departed.sort()                            
            if present:
                # some val has dropped out with departed folks, it
                # needs to be rolled up into the groups of devs who
                # are in the group and still present
                add_dev_val_lookup(present, lookup, val)
            else:
                # the val has nowhere to go...all potential aggregates
                # are gone.  we put it in the departed section to
                # return it.
                add_dev_val_lookup(departed, departed_lookup, val)
            lookup_str = '\0'.join(devs)
            if lookup_str in lookup:
                del lookup[lookup_str]
                
    return [(devs_lookup.split('\0'), val) for devs_lookup, val in lookup.items()], \
           [(dep_lookup.split('\0'), val) for dep_lookup, val in departed_lookup.items()]

def summarize(lines, departed_devs):
    """
    Aggregate the FileData in lines, considering all devs in
    departed_devs to be hit by a bus.
    """
    
    aggs = {}

    # aggregate by valtype and our top-level objects, used by the
    # index page.
    create_agg(aggs, (a_valtype, a_dev))
    create_agg(aggs, (a_valtype, a_project))
    create_agg(aggs, (a_valtype, a_fname))

    # aggregates by project for the projects pages
    create_agg(aggs, (a_project, a_valtype, a_fname))
    create_agg(aggs, (a_project, a_valtype, a_dev))

    # aggregates by dev group of 1 or more for the devs pages.
    create_agg(aggs, (a_dev, a_valtype, a_fname))
    create_agg(aggs, (a_dev, a_valtype, a_project))

    # fname aggregate for the files pages
    create_agg(aggs, (a_fname, a_valtype, a_dev))

    for line in lines:
        fd = FileData(line)

        # we don't do anything with the risk represented by departed
        # devs...the risk has already turned out to be real and the
        # knowledge is gone.
        dev_risk, _ignored = split_out_dev_vals(fd.dev_risk, departed_devs)
        for devs, risk in dev_risk:
            agg_all(aggs, Dat('risk', fd, devs, risk))
        dev_uniq, dev_orphaned = split_out_dev_vals(fd.dev_uniq, departed_devs)
        for devs, uniq in dev_uniq:
            agg_all(aggs, Dat('unique knowledge', fd, devs, uniq))
            # hack: to get the devs with most shared knowledge to show
            # up on the devs pages, explode the devs and aggregate
            # them pairwise here under a different valtype that only
            # the devs pages will use
            for dev1 in devs:
                for dev2 in devs:
                    # don't double count the similarity
                    if dev1 < dev2:
                        agg_all(aggs, Dat('shared knowledge (devs still present)', fd, [dev1, dev2], uniq))
        # if there is knowledge unique to groups of 1 or more devs who
        # are all departed, this knowledge is orphaned.
        for devs, orphaned in dev_orphaned:
            agg_all(aggs, Dat('orphaned knowledge', fd, devs, orphaned))

    return aggs

def tupelize(agg, tuples_and_vals, key_list):
    for k, v in agg.items():
        loc_key = list(key_list)
        loc_key.append(k)
        if not isinstance(v, dict):
            tuples_and_vals.append((tuple(loc_key), v))
        else:
            tupelize(v, tuples_and_vals, loc_key)

def sort_agg(agg, desc):
    tuples_and_vals = []
    tupelize(agg, tuples_and_vals, [])
    tuples_and_vals = [(t[1], t) for t in tuples_and_vals]
    tuples_and_vals.sort()
    if desc:
        tuples_and_vals.reverse()
    tuples_and_vals = [t[1] for t in tuples_and_vals]
    return tuples_and_vals

def by_valtype_html(valtype, nouns, noun, linker, limit):
    html = []
    limit_str = ''
    if limit:
        limit_str = 'Top %d ' % limit
    html.append("<h3>%s%s by highest estimated %s</h3>" % (limit_str, noun, valtype))
    html.append("<table style=\"width: 80%\">")
    html.append("<tr><th>%s</th><th>Total estimated %s</th></tr>" % (noun, valtype))
    max_value = max([n[1] for n in nouns])
    for t, val in nouns:
        if round(val) > GLOBAL_CUTOFF:
            vals_t = (linker(t[0]),
                      int(round(val)),
                      math.ceil(100 * (val / max_value)))
            html.append("<tr><td>%s (%d)</td><td style=\"width: 80%%;\"><div style=\"background-color: LightSteelBlue; width: %d%%;\">&nbsp;</div></td></tr>" % vals_t)
    html.append("</table>") 
    return html

def project_fname(project):
    return os.path.join('projects', "%s.html" % project)

def project_linker(project):
    return "<a href=\"%s\">%s</a>" % (project_fname(project), project)        

def fname_fname(fname):
    return os.path.join('files', "%s.html" % fname.replace(':', '__').replace(os.path.sep, '__'))

def fname_linker(fname):
    return "<a href=\"%s\">%s</a>" % (fname_fname(fname), fname)    

def dev_fname(dev):
    return os.path.join('devs', "%s.html" % dev)

def dev_linker(dev):
    return "<a href=\"%s\">%s</a>" % (dev_fname(dev), dev)

def parent_linker(fnamer):
    def f(to_link):
        return "<a href=\"%s\">%s</a>" % (os.path.join('..', fnamer(to_link)), to_link)        
    return f

def summarize_by_valtype(agg_by_single, noun, linker):
    return summarize_top_by_valtype(agg_by_single, noun, linker, None)

def summarize_top_by_valtype(agg_by_single, noun, linker, limit):
    html = []
    for valtype, nouns in agg_by_single.items():
        nouns = sort_agg(nouns, True)
        if limit:
            nouns = nouns[:limit]
        html.extend(by_valtype_html(valtype, nouns, noun, linker, limit))
    return html

def add_global_explanation(html):
    html.append('<p>Note: values smaller than %d have been truncated in the interest of space.</p>' % GLOBAL_CUTOFF)
    html.append('<p>Note: the scale of the bars is relative only within, not across, tables.</p>')

def create_index(aggs, output_dir):
    html = []
    html.append("<html>\n<head><title>Git By a Bus Summary Results</title></head>\n<body>")
    html.append("<h1>Git by a Bus Summary Results</h1>")
    add_global_explanation(html)
    html.extend(summarize_top_by_valtype(aggs[(a_valtype, a_project)], 'Projects', project_linker, 100))
    html.extend(summarize_top_by_valtype(aggs[(a_valtype, a_dev)], 'Devs', dev_linker, 100))
    html.extend(summarize_top_by_valtype(aggs[(a_valtype, a_fname)], 'Files', fname_linker, 100))
    html.append("</body>\n</html>")
    outfil = open(os.path.join(output_dir, 'index.html'), 'w')
    outfil.write('\n'.join(html))
    outfil.close()

def create_detail_page(detail, noun, valtype_args, fname, custom_lines_f):
    html = []
    html.append("<html>\n<head><title>Git By a Bus Summary Results for %s: %s</title></head>\n<body>" % (noun, detail))
    html.append("<p><a href=\"../index.html\">Index</a></p>")
    html.append("<h1>Git by a Bus Summary Results for %s: %s</h1>" % (noun, detail))
    add_global_explanation(html)
    if custom_lines_f:
        html.extend(custom_lines_f(detail, noun, valtype_args, fname))
    for vtarg in valtype_args:
        html.extend(summarize_top_by_valtype(vtarg[0], vtarg[1], vtarg[2], vtarg[3]))
    html.append("</body>\n</html>")
    outfil = open(fname, 'w')
    outfil.write('\n'.join(html))
    outfil.close()

def create_detail_pages(output_dir, subdir, details, noun, detail_fname, aggs_with_nouns, custom_lines_f = None):
    try:
        os.mkdir(os.path.join(output_dir, subdir))
    except:
        pass

    for detail in details:
        outfile_name = os.path.join(output_dir, detail_fname(detail))
        vt_args = [(agg[detail], nouns, linker, None) for agg, nouns, linker in aggs_with_nouns if detail in agg]
        create_detail_page(detail, noun, vt_args, outfile_name, custom_lines_f)

def create_project_pages(aggs, output_dir):
    dev_agg = aggs[(a_project, a_valtype, a_dev)]
    fname_agg = aggs[(a_project, a_valtype, a_fname)]
    projects = fname_agg.keys()
    create_detail_pages(output_dir, 'projects', projects, 'Project', project_fname, [(dev_agg, 'Devs', parent_linker(dev_fname)),                                                                                                                     (fname_agg, 'Files', parent_linker(fname_fname))])



def create_dev_pages(aggs, output_dir, departed_devs):

    # callback to pass into create_detail_pages to make
    #
    # * the links to individual devs making up a group and
    #
    # * the table of devs with most shared knowledge for individual
    # devs
    def dev_custom(devs, noun, valtype_args, fname):
        html = []
        linker = parent_linker(dev_fname)
        the_devs = devs.split(' and ')
        if len(the_devs) > 1:
            html.append("<p>Common knowledge / risk for devs:</p>\n<ul>")
            for the_dev in the_devs:
                html.append("<li>%s</li>\n" % linker(the_dev))
            html.append("</ul>")
        elif len(the_devs) == 1:
            # do a little custom aggregation to show who we share most with
            the_dev = the_devs[0]
            if the_dev in departed_devs:
                return html
            agg = aggs[(a_valtype, a_dev)]
            shared_k_agg = agg.get('shared knowledge (devs still present)',[])
            top_shares = {}
            for dev_devs, shared in shared_k_agg.items():
                the_dev_devs = dev_devs.split(' and ')
                if len(the_dev_devs) != 2:
                    continue
                dev1, dev2 = the_dev_devs
                if dev1 == the_dev:
                    top_shares[dev2] = shared
                elif dev2 == the_dev:
                    top_shares[dev1] = shared
            top_shares = [(shared, odev) for odev, shared in top_shares.items()]
            top_shares.sort()
            top_shares.reverse()
            top_shares = [([ts[1]], ts[0]) for ts in top_shares]
            if top_shares:
                html.extend(by_valtype_html('shared', top_shares, 'devs', parent_linker(dev_fname), 10))
                        
        return html

    project_agg = aggs[(a_dev, a_valtype, a_project)]
    fname_agg = aggs[(a_dev, a_valtype, a_fname)]
    devs = fname_agg.keys()
    create_detail_pages(output_dir, 'devs', devs, 'Dev', dev_fname, [(project_agg, 'Projects', parent_linker(project_fname)),
                                                                     (fname_agg, 'Files', parent_linker(fname_fname))], dev_custom)

def create_file_pages(aggs, output_dir):
    dev_agg = aggs[(a_fname, a_valtype, a_dev)]
    fnames = dev_agg.keys()
    create_detail_pages(output_dir, 'files', fnames, 'File', fname_fname, [(dev_agg, 'Devs', parent_linker(dev_fname))])

def add_dev_dev(dev_dev, dev1, dev2, diff):
    if dev1 not in dev_dev:
        dev_dev[dev1] = {}
    dev_dev[dev1][dev2] = diff

def read_dev_x_cmp(x_cmp_fname, make_sym):
    dev_dev = {}
    fil = open(x_cmp_fname, 'r')
    for line in fil:
        line = line.strip()
        dev1, dev2, diff = line.split('\t')
        diff = float(diff)
        add_dev_dev(dev_dev, dev1, dev2, diff)
        if make_sym:
            add_dev_dev(dev_dev, dev2, dev1, diff)        
    fil.close()
    return dev_dev

def create_summary(lines, output_dir, departed_devs):
    aggs = summarize(lines, departed_devs)
    create_index(aggs, output_dir)
    create_project_pages(aggs, output_dir)
    create_dev_pages(aggs, output_dir, departed_devs)
    create_file_pages(aggs, output_dir)
    
if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-d', '--departed-dev-file', dest='departed_dev_file', metavar='FILE',
                      help='File listing departed devs, one per line')
    options, args = parser.parse_args()

    departed_devs = []
    if options.departed_dev_file:
        parse_departed_devs(options.departed_dev_file, departed_devs)

    create_summary(sys.stdin, args[0], departed_devs)

    # print to the tsv so if folks look there they get redirected
    # correctly
    print "Summary is available at %s/index.html" % args[0]
