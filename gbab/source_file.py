class SourceFile(object):
    """
    Represents a source file in the repository.
    """

    def __init__(self, project, fname, line_model, knowledge_model):
        """
        fname must be unique within project.

        project must be unique among all project names.

        line_model must support the following operations:

        * line_model.lookup_line_id(project, fname, line_num)

        * line_model.add_line(project, fname, line_num, line)

        * line_model.remove_line(line_id)

        * line_model.change_line(line_id, line)

        knowledge_model must support the following operations:

        * knowledge_model.line_changed(author, line_id)

        * knowledge_model.line_removed(author, line_id)

        * knowledge_model.line_added(author, line_id)
        """
        self.project = project
        self.fname = fname
        self.line_model = line_model
        self.knowledge_model = knowledge_model

    def change_line(self, author, line_num, line):
        """
        Change the line currently found at line_num to the text in line, attributing the change to author.
        """
        line_id = self.line_model.lookup_line_id(self.project, self.fname, line_num)
        self.line_model.change_line(line_id, line)        
        self.knowledge_model.line_changed(author, line_id)

    def remove_line(self, author, line_num):
        line_id = self.line_model.lookup_line_id(self.project, self.fname, line_num)
        self.line_model.remove_line(line_id)
        self.knowledge_model.line_removed(author, line_id)

    def add_line(self, author, line_num, line):
        line_id = self.line_model.add_line(self.project, self.fname, line_num, line)
        self.knowledge_model.line_added(author, line_id)
