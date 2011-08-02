class Smoother(object):

    def smooth(self, tuples, window_size, indexes_to_smooth):
        for i in range(len(tuples)):
            start_smooth = i
            end_smooth = i + window_size
            window = tuples[start_smooth:end_smooth]
            for ind in indexes_to_smooth:
                tot = sum([t[ind] for t in window])
                avg = float(tot) / float(len(window))
                for ix in range(len(window)):
                    t = tuples[i + ix]
                    ls_cp = list(t)
                    ls_cp[ind] = avg
                    tuples[i + ix] = tuple(ls_cp)
        return tuples
