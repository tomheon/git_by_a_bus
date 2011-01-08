class Mock(object):

    def __init__(self):
        self.call_log = []

    def _rcrd(self, tup):
        self.call_log.append(tup)

    def clear_call_log(self):
        self.call_log = []


class MockLineModel(Mock):

    def lookup_line_id(self, project, fname, line_num):
        self._rcrd((self.lookup_line_id, project, fname, line_num))
        return line_num + 1

    def add_line(self, project, fname, line_num, line):
        self._rcrd((self.add_line, project, fname, line_num, line))
        return line_num + 2

    def remove_line(self, line_id):
        self._rcrd((self.remove_line, line_id))

    def change_line(self, line_id, line):
        self._rcrd((self.change_line, line_id, line))


class MockKnowledgeModel(Mock):
    
    def line_changed(self, author, line_id):
        self._rcrd((self.line_changed, author, line_id))

    def line_removed(self, author, line_id):
        self._rcrd((self.line_removed, author, line_id))

    def line_added(self, author, line_id):
        self._rcrd((self.line_added, author, line_id))


class MockSourceFile(Mock):

    def change_line(self, author, line_num, line):
        self._rcrd((self.change_line, author, line_num, line))

    def remove_line(self, author, line_num):
        self._rcrd((self.remove_line, author, line_num))

    def add_line(self, author, line_num, line):
        self._rcrd((self.add_line, author, line_num, line))


class MockRiskModel(Mock):

    def __init__(self):
        self.is_safe = False

    def joint_bus_prob_is_safe(self, authors):
        return self.is_safe
