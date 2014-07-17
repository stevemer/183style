'''
Style Grader class with instance-method plugin-based functionality.
'''

import codecs
from ConfigParser import ConfigParser
from collections import defaultdict
import sys

from cpplint import CleansedLines, RemoveMultiLineComments

from style_grader_functions import check_if_function, print_success
from style_grader_classes import SpacingTracker
from StyleError import StyleError
import comment_checks
import multi_line_checks
import misc_checks
import single_line_checks

def safely_open(filename):
    try:
        dirty_text = codecs.open(filename, 'r', 'utf8', 'replace').readlines()
        for num, line in enumerate(dirty_text):
            dirty_text[num] = line.rstrip('\r')
        return dirty_text
    except IOError:
        sys.stderr.write('This file could not be read: "%s."  '
                         'Please check filename and resubmit \n' % filename)

class StyleRubric(object):
    '''
    A style grader to generate StyleErrors from a list of C++ files.
    '''
    def __init__(self):
        ''' Load functionality based on config file specifications '''
        self.config = ConfigParser()
        self.config.read('rubric.ini')
        self.error_tracker = dict()
        self.error_types = defaultdict(int)
        self.total_errors = 0
        self.student_files = self.config.get('FILES', 'student_files').split(',')
        self.includes = self.config.get('FILES', 'permitted_includes').split(',')
        self.all_rme = set()
        self.single_line_checks = self.load_functions(single_line_checks)
        self.multi_line_checks = self.load_functions(multi_line_checks)
        self.comment_checks = self.load_functions(comment_checks)
        self.misc_checks = self.load_functions(misc_checks)
        self.global_in_object = False;
        self.global_object_braces = []
        self.global_in_object_index = 0


    def add_global_brace(self, brace):
        self.global_object_braces.append(brace)
        self.global_in_object_index += 1

    def pop_global_brace(self):
        self.global_object_braces.pop()
        if self.global_in_object_index == 0:
            self.global_in_object = False

    def load_functions(self, module):
        functions = list()
        group = module.__name__.upper()
        for check in self.config.options(group):
            if self.config.get(group, check).lower() == 'yes':
                functions.append(getattr(module, 'check_'+check))
        return functions

    def reset_for_new_file(self, filename):
        self.spacer = SpacingTracker()
        self.outside_main = True
        self.egyptian = False
        self.not_egyptian = False
        self.braces_error = False #To prevent multiple braces errors
        self.in_switch = False
        self.current_file = filename
        self.error_tracker[filename] = list()

    def add_error(self, label=None, line=0, column=0, data=dict()):
        self.total_errors += 1
        self.error_types[label] += 1
        line = line if line else self.current_line_num + 1
        self.error_tracker[self.current_file].append(StyleError(1, label, line, column_num=column, data=data))

    def grade_student_file(self, filename):
        self.reset_for_new_file(filename)
        extension = filename.split('.')[-1]
        if extension not in ['h', 'cpp']:
            sys.stderr.write('Incorrect file type\n')
            return
        data = safely_open(filename)
        raw_data = safely_open(filename)
        RemoveMultiLineComments(filename, data, '')
        clean_lines = CleansedLines(data)
        clean_code = clean_lines.lines
        for self.current_line_num, code in enumerate(clean_code):
            for function in self.single_line_checks: function(self, code)
            for function in self.multi_line_checks: function(self, clean_lines)
        # COMMENT CHECKS #TODO
        for self.current_line_num, text in enumerate(raw_data):
            if self.config.get('COMMENT_CHECKS', 'line_width').lower() == 'yes':
                getattr(comment_checks, 'check_line_width')(self, text)
            if check_if_function(text):
                if self.config.get('COMMENT_CHECKS', 'missing_rme').lower() == 'yes':
                    getattr(comment_checks, 'check_missing_rme')(self, raw_data)
        for function in self.misc_checks: function(self)
        self.error_tracker[filename].sort()

    def print_errors(self):
        for filename, errors in self.error_tracker.iteritems():
            print 'Grading {}...'.format(filename)
            if not len(errors):
                print_success()
            for error in errors:
                print error
            print
