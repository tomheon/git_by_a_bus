from nose.tools import eq_

from gbab.source_file import SourceFile
from tests.mocks import MockLineModel, MockKnowledgeModel

def test_init():
    test_vals = [('test_project', 'test_fname', 'test_line_model', 'test_knowledge_model'),
                 ('test_project2', 'test_fname2', 'test_line_model2', 'test_knowledge_model2')]
    for tv in test_vals:
        src_file = SourceFile(tv[0], tv[1], tv[2], tv[3])
        eq_(tv[0], src_file.project)
        eq_(tv[1], src_file.fname)
        eq_(tv[2], src_file.line_model)
        eq_(tv[3], src_file.knowledge_model)

def test_change_line():
    line_model = MockLineModel()
    knowledge_model = MockKnowledgeModel()
    src_file = SourceFile('project1', 'fname1', line_model, knowledge_model)
    src_file.change_line('author1', 20, 'this is the line')
    src_file.change_line('author2', 101, 'this is the second line')
    eq_([(line_model.lookup_line_id, 'project1', 'fname1', 20),
         (line_model.change_line, 21, 'this is the line'),
         (line_model.lookup_line_id, 'project1', 'fname1', 101),
         (line_model.change_line, 102, 'this is the second line')],
        line_model.call_log)
    eq_([(knowledge_model.line_changed, 'author1', 21),
         (knowledge_model.line_changed, 'author2', 102)],
        knowledge_model.call_log)

def test_remove_line():
    line_model = MockLineModel()
    knowledge_model = MockKnowledgeModel()
    src_file = SourceFile('project2', 'fname2', line_model, knowledge_model)
    src_file.remove_line('author1', 204)
    src_file.remove_line('author2', 300)
    eq_([(line_model.lookup_line_id, 'project2', 'fname2', 204),
         (line_model.remove_line, 205),
         (line_model.lookup_line_id, 'project2', 'fname2', 300),
         (line_model.remove_line, 301)],
        line_model.call_log)
    eq_([(knowledge_model.line_removed, 'author1', 205),
         (knowledge_model.line_removed, 'author2', 301)],
        knowledge_model.call_log)
    
def test_add_line():
    line_model = MockLineModel()
    knowledge_model = MockKnowledgeModel()
    src_file = SourceFile('project3', 'fname3', line_model, knowledge_model)
    src_file.add_line('author1', 1, 'this is a great line')
    src_file.add_line('author2', 3, 'but this is even a better line')    
    eq_([(line_model.add_line, 'project3', 'fname3', 1, 'this is a great line'),
         (line_model.add_line, 'project3', 'fname3', 3, 'but this is even a better line')],
        line_model.call_log)
    eq_([(knowledge_model.line_added, 'author1', 3),
         (knowledge_model.line_added, 'author2', 5)],
        knowledge_model.call_log)
    
