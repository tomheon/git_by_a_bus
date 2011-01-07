class DiffWalker(object):
    """
    Walk the chunks and hunks of a diff, processing them in the
    associated SourceFile object as added, removed, and changed lines.
    """

    def walk(self, author, diff, source_file):
        """
        Diff should be in the default git diff or git diff --patience
        output for a single file.

        source_file should be a SourceFile object (or support the
        equivalent operations)

        Walks the diff to find added, changed, and deleted lines and
        calling into source_file to process them.
        """
        chunks = self._chunkify(diff)

        for chunk in chunks:
            self._step_chunk(chunk, author, source_file)

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
            line = line.rstrip('\r')
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

    def _step_chunk(self, chunk, author, source_file):
        header = chunk[0]
        
        # format of header is
        #
        # @@ -old_line_num,cnt_lines_in_old_chunk, +new_line_num,cnt_lines_in_new_chunk
        #
        _blank, lines_info, _rest = header.split('@@')
        offsets = lines_info.strip().split(' ')
        
        # we only care about the new offset, since in the first chunk
        # of the file the new and old are the same, and since we add
        # and subtract lines as we go, we should stay in step with the
        # new offsets.
        new_offset, new_cnt_lines = [abs(int(num)) for num in offsets[1].split(',')]

        # a hunk is  a group of contingent - + lines
        #
        # hunks: [(start_line_num, [old, lines, ...], [new, lines, ...])]
        #
        hunks = self._hunkize(chunk[1:], new_offset)

        for hunk in hunks:
            self._step_hunk(author, hunk, source_file)

    def _step_hunk(self, author, hunk, source_file):
        start_line_num, old_lines, new_lines = hunk
        old_len = len(old_lines)
        new_len = len(new_lines)
        max_len = max(old_len, new_len)
            
        for i in range(max_len):
            line_num = start_line_num + i
                
            if i < old_len and i < new_len:
                # if file exists in both arrays, it's changed,
                # just remember to strip out the '+' at the
                # beginning of the line
                source_file.change_line(author, line_num, new_lines[i][1:])
            elif i < old_len:
                # there is no corresponding line in the new file,
                # then this has been deleted
                source_file.remove_line(author, line_num)
            else:
                # this must be an added line, strip out the '+' at the
                # beginning
                source_file.add_line(author, line_num, new_lines[i][1:])

    def _hunkize(self, chunk_wo_header, first_line_num):
        hunks = []
        cur_old = []
        cur_new = []

        for i, line in enumerate(chunk_wo_header):
            if self._is_old_line(line):
                cur_old.append(line)
            elif self._is_new_line(line):
                cur_new.append(line)
            elif cur_old or cur_new:
                start_of_hunk_line = first_line_num + i - len(cur_old) - len(cur_new)
                hunks.append((start_of_hunk_line, cur_old, cur_new))
                cur_old = []
                cur_new = []

        # catch the last hunk, if there is one
        if cur_old or cur_new:
            hunks.append((first_line_num + len(chunk_wo_header) - 1, cur_old, cur_new))

        return hunks

    def _is_old_line(self, line):
        return line and line.startswith('-')

    def _is_new_line(self, line):
        return line and line.startswith('+')
