class Mock(object):

    def __init__(self):
        self.call_log = []

    def _rcrd(self, tup):
        self.call_log.append(tup)

    def clear_call_log(self):
        self.call_log = []


class MockRiskModel(Mock):

    def __init__(self):
        self.is_safe = False

    def joint_bus_prob_below_threshold(self, authors):
        return self.is_safe

    def is_departed(self, author):
        return False
