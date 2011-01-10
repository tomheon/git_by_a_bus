class DiffWalker(object):
    """
    Walk the chunks and hunks of a diff, returning them as a list of
    events.
    """

    def walk(self, diff):
        """
        Diff should be in the default git diff or git diff --patience
        output for a single file.


        Walks the diff to find added, changed, and deleted lines,
        returning a list of tuples of the form:
        
        [('added'|'changed'|'deleted', int(line_num), str(line_val)|None)]
        """
        chunks = self._chunkify(diff)

        tot_chunks = len(chunks)

        events = []

        for i, chunk in enumerate(chunks):
            self._step_chunk(chunk, events)

        return events

    # implementation

    def _chunkify(self, diff):
        """
        Break diff into chunks, a list of list of lines.

        The first line in each list of lines is the diff chunk header,
        with @@

        We skip everything up to the head of the first chunk.
        """
        chunks = []
        cur_chunk = []
        
        for line in diff.split('\n'):
            if self._starts_chunk(line):
                if cur_chunk:
                    chunks.append(cur_chunk)
                    cur_chunk = []
                cur_chunk.append(line)
            elif cur_chunk:
                cur_chunk.append(line)

        # catch the end of the last chunk, if there is one.
        if cur_chunk:
            chunks.append(cur_chunk)

        return chunks

    def _starts_chunk(self, line):
        return line and line.startswith('@@')

    def _step_chunk(self, chunk, events):
        header = chunk[0]
        
        # format of header is
        #
        # @@ -old_line_num,cnt_lines_in_old_chunk, +new_line_num,cnt_lines_in_new_chunk
        #
        _blank, lines_info, _rest = header.split('@@', 2)
        offsets = lines_info.strip().split(' ')
        
        # we only care about the new offset, since in the first chunk
        # of the file the new and old are the same, and since we add
        # and subtract lines as we go, we should stay in step with the
        # new offsets.
        
        new_offset = [abs(int(num)) for num in offsets[1].split(',')][0]

        # a hunk is  a group of contingent - + lines
        #
        # hunks: [(start_line_num, [old, lines, ...], [new, lines, ...])]
        #
        hunks = self._hunkize(chunk[1:], new_offset)

        tot_hunks = len(hunks)
        for i, hunk in enumerate(hunks):
            self._step_hunk(hunk, events)

    def _step_hunk(self, hunk, events):
        start_line_num, old_lines, new_lines = hunk
        old_len = len(old_lines)
        new_len = len(new_lines)
        max_len = max(old_len, new_len)
        line_num = start_line_num
        
        for i in range(max_len):
            if i < old_len and i < new_len:
                # if file exists in both arrays, it's changed,
                # just remember to strip out the '+' at the
                # beginning of the line
                events.append(('change', line_num, new_lines[i][1:]))
                line_num += 1
            elif i < old_len:
                # there is no corresponding line in the new file,
                # then this has been removed
                events.append(('remove', line_num, None))
            else:
                # this must be an added line, strip out the '+' at the
                # beginning
                events.append(('add', line_num, new_lines[i][1:]))
                line_num += 1

    def _hunkize(self, chunk_wo_header, first_line_num):
        hunks = []
        cur_old = []
        cur_new = []
        cur_line = first_line_num
        
        for line in chunk_wo_header:
            if self._is_old_line(line):
                cur_old.append(line)
            elif self._is_new_line(line):
                cur_new.append(line)
            elif cur_old or cur_new:
                hunks.append((cur_line, cur_old, cur_new))
                cur_line += len(cur_new) + 1
                cur_old = []
                cur_new = []
            else:
                cur_line += 1

        # catch the last hunk, if there is one
        if cur_old or cur_new:
            hunks.append((cur_line, cur_old, cur_new))

        return hunks

    def _is_old_line(self, line):
        return line and line.startswith('-')

    def _is_new_line(self, line):
        return line and line.startswith('+')
