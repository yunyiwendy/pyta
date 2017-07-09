"""Python Teaching Assistant

The goal of this module is to provide automated feedback to students in our
introductory Python courses, using static analysis of their code.

To run the checker, call the check function on the name of the module to check.

> import python_ta
> python_ta.check_all('mymodule')

Or, put the following code in your Python module:

if __name__ == '__main__':
    import python_ta
    python_ta.check_all()
"""
import importlib.util
import os
import sys
import tokenize
import webbrowser

import pylint.lint
import pylint.utils
from pylint.config import VALIDATORS, _call_validator

from astroid import modutils

from .reporters import REPORTERS, PlainReporter, ColorReporter
from .patches import patch_all

# Local version of website; will be updated later.
HELP_URL = 'http://www.cs.toronto.edu/~david/pyta/'

# check the python version
if sys.version_info < (3, 4, 0):
    print('You need Python 3.4 or later to run this script')


def check_errors(module_name='', config='', output=None):
    """Check a module for errors, printing a report."""
    _check(module_name=module_name, level='error', local_config=config, 
           output=output)


def check_all(module_name='', config='', output=None):
    """Check a module for errors and style warnings, printing a report."""
    _check(module_name=module_name, level='all', local_config=config, 
           output=output)


def _find_pylintrc_same_locale(curr_dir):
    """Search for a `.pylintrc` configuration file provided in same (user) 
    location as the source file to check.
    Return absolute path to the file, or None.
    `curr_dir` is an absolute path to a directory, containing a file to check.
    For more info see, pylint.config.find_pylintrc
    """
    if curr_dir.endswith('.py'):
        curr_dir = os.path.dirname(curr_dir)
    if os.path.exists(os.path.join(curr_dir, '.pylintrc')):
        return os.path.join(curr_dir, '.pylintrc')
    elif os.path.exists(os.path.join(curr_dir, 'pylintrc')):
        return os.path.join(curr_dir, 'pylintrc')


def _load_config(linter, config_location):
    """Load configuration into the linter (checker)."""
    linter.read_config_file(config_location)
    linter.config_file = config_location
    linter.load_config_file()
    print('### Loaded configuration file: {}'.format(config_location))


def reset_linter(config=None, file_linted=None):
    """Construct a new linter. Register config and checker plugins.
    To determine which configuration to use:
    • If the config argument is a string, use the config found at that location,
    • Otherwise, 
        • Try to use the config file at directory of the file being linted,
        • Otherwise try to use default config file shipped with python_ta.
        • If the config argument is a dictionary, apply those options afterward.
    Do not re-use a linter object. Returns a new linter."""

    # Tuple of custom options. See 'type' in pylint/config.py `VALIDATORS` dict.
    new_checker_options = (
        ('pyta-reporter',
            {'default': 'ColorReporter',
             'type': 'string',
             'metavar': '<pyta_reporter>',
             'help': 'Output messages with a specific reporter.'}),
        ('pyta-pep8',
            {'default': False,
             'type': 'yn',
             'metavar': '<yn>',
             'help': 'Use the pycodestyle checker.'}),
        ('pyta-number-of-messages',
            {'default': 5,
             'type': 'int',
             'metavar': '<number_messages>',
             'help': 'Display a certain number of messages to the user, without overwhelming them.'}),
    )

    custom_checkers = [
        'python_ta/checkers/forbidden_import_checker',
        'python_ta/checkers/global_variables_checker',
        'python_ta/checkers/dynamic_execution_checker',
        'python_ta/checkers/IO_Function_checker',
        # TODO: Fix this test
        'python_ta/checkers/invalid_range_index_checker',
        'python_ta/checkers/assigning_to_self_checker',
        'python_ta/checkers/always_returning_checker',
        'python_ta/checkers/type_inference_checker'
    ]

    # Register new options to a checker here to allow references to 
    # options in `.pylintrc` config file.
    # Options stored in linter: `linter._all_options`, `linter._external_opts`
    linter = pylint.lint.PyLinter(options=new_checker_options)
    linter.load_default_plugins()  # Load checkers, reporters
    linter.load_plugin_modules(custom_checkers)

    if isinstance(config, str) and config != '':
        # Use config file at the specified path instead of the default.
        _load_config(linter, config)
    else:
<<<<<<< HEAD
        # Check if `module_name` is not the type str, raise error.
        if not isinstance(module_name, str):
            print("The Module '{}' has an invalid name. Module name must be the "
                  "type str.".format(module_name))
            return
        module_name = module_name.replace(os.path.sep, '.')

        # Detect if the extension .py is added, and if it is, remove it.
        if module_name.endswith('.py'):
            module_name = module_name[:-3]

        spec = importlib.util.find_spec(module_name)

    if spec is None:
        print("The Module '{}' could not be found. ".format(module_name))
        return

    # Clear the astroid cache of this module (allows for on-the-fly changes
    # to be detected in consecutive runs in the interpreter).
    if spec.name in MANAGER.astroid_cache:
        del MANAGER.astroid_cache[spec.name]

    current_reporter = reporter(number_of_messages)
    linter = lint.PyLinter(reporter=current_reporter)
    linter.load_default_plugins()
    linter.load_plugin_modules(['python_ta/checkers/forbidden_import_checker',
                                'python_ta/checkers/global_variables_checker',
                                'python_ta/checkers/dynamic_execution_checker',
                                'python_ta/checkers/IO_Function_checker',
                                # TODO: Fix this test
                                #'python_ta/checkers/invalid_range_index_checker',
                                'python_ta/checkers/assigning_to_self_checker',
                                'python_ta/checkers/always_returning_checker'])

    if pep8:
=======
        # If available, use config file at directory of the file being linted.
        pylintrc_location = None
        if file_linted:
            pylintrc_location = _find_pylintrc_same_locale(file_linted)

        # Otherwise, use default config file shipped with python_ta package.
        if not pylintrc_location:
            pylintrc_location = _find_pylintrc_same_locale(os.path.dirname(__file__))
        _load_config(linter, pylintrc_location)

        # Override part of the default config, with a dict of config options.
        # Note: these configs are overridden by config file in user's codebase
        # location.
        if isinstance(config, dict):
            for key in config:
                linter.global_set_option(key, config[key])
            print('### Loaded configuration dictionary.')

    # The above configuration may have set the pep8 option.
    if linter.config.pyta_pep8:
>>>>>>> 6a56111ad8ff0a185a26c12a494d47dbe004d78a
        linter.load_plugin_modules(['python_ta/checkers/pycodestyle_checker'])

    patch_all()  # Monkeypatch pylint (override certain methods)
    return linter


def reset_reporter(linter, output_filepath=None):
    """Initialize a reporter with config options.
    Output is an absolute file path to output into.
    Cannot use ColorReporter when outputting to a file because the file cannot
    contain colorama ascii characters -- switches to use PlainReporter."""
    # Determine the type of reporter from the config setup.
    current_reporter = _call_validator(linter.config.pyta_reporter, 
                                       None, None, None)
    if isinstance(current_reporter, ColorReporter) and output_filepath:
        current_reporter = PlainReporter()
    current_reporter.set_output_filepath(output_filepath)
    linter.set_reporter(current_reporter)
    return current_reporter


def get_file_paths(rel_path):
    """A generator for iterating python files within a directory.
    `rel_path` is a relative path to a file or directory.
    Returns paths to all files in a directory.
    """
    if not os.path.isdir(rel_path):
        yield rel_path  # Don't do anything; return the file name.
    else:
        for root, _, files in os.walk(rel_path):
            for filename in (f for f in files if f.endswith('.py')):
                yield os.path.join(root, filename)  # Format path, from root.


def _verify_pre_check(filepath):
    """Check student code for certain issues."""
    # Make sure the program doesn't crash for students.
    # Could use some improvement for better logging and error reporting.
    try:
        # Check for inline "pylint:" comment, which may indicate a student
        # trying to disable a check.
        with tokenize.open(os.path.expanduser(filepath)) as f:
            for (tok_type, content, _, _, _) in tokenize.generate_tokens(f.readline):
                if tok_type != tokenize.COMMENT:
                    continue
                match = pylint.utils.OPTION_RGX.search(content)
<<<<<<< HEAD
                if match is None:
                    continue
                else:
                    print('ERROR: string "pylint:" found in comment. No checks will be run.')
                    return

        linter.check([spec.origin])
        current_reporter.print_messages(level)
=======
                if match is not None:
                    print('ERROR: string "pylint:" found in comment. ' +
                          'No check run on file `{}`\n'.format(filepath))
                    return False
    except IndentationError as e:
        print('ERROR: python_ta could not check your code due to an ' +
              'indentation error at line {}'.format(e.lineno))
        return False
    except tokenize.TokenError as e:
        print('ERROR: python_ta could not check your code due to a ' +
              'syntax error in your file')
        return False
    return True


def _get_valid_files_to_check(reporter, module_name, local_config):
    """A generator for all valid files to check. Uses a reporter to output 
    messages when an input cannot be checked.
    """
    # Allow call to check with empty args
    if module_name == '':
        m = sys.modules['__main__']
        spec = importlib.util.spec_from_file_location(m.__name__, m.__file__)
        module_name = [spec.origin]
    # Enforce API to expect 1 file or directory if type is list
    elif isinstance(module_name, str):
        module_name = [module_name]
    # Otherwise, enforce API to expect `module_name` type as list
    elif not isinstance(module_name, list):
        print('No checks run. Input to check, `{}`, has invalid type, must be a list of strings.\n'.format(module_name))
        return

    # Filter valid files to check
    for item in module_name:
        if not isinstance(item, str):  # Issue errors for invalid types
            print(reporter.filename_to_display(item))
            print('No check run on file `{}`, with invalid type. Must be type: str.\n'.format(item))
        elif os.path.isdir(item):
            yield item
        elif not os.path.exists(os.path.expanduser(item)):
            try:
                # For files with dot notation, e.g., `examples.<filename>`
                filepath = modutils.file_from_modpath(item.split('.'))
                if os.path.exists(filepath):
                    yield filepath
                else:
                    print(reporter.filename_to_display(item))
                    print('Could not find the file called, `{}`\n'.format(item))
            except ImportError:
                print(reporter.filename_to_display(item))
                print('Could not find the file called, `{}`\n'.format(item))
        else:
            yield item  # Check other valid files.

>>>>>>> 6a56111ad8ff0a185a26c12a494d47dbe004d78a

def _check(module_name='', level='all', local_config='', output=None):
    """Check a module for problems, printing a report.
    • The `module_name` can take several inputs:
      - string of a directory, or file to check (`.py` extension optional). 
      - list of strings of directories or files -- can have multiple.
      - no argument -- checks the python file containing the function call.
    • `level` is used to specify which checks should be made.
    • `local_config` is a dict of config options or string (config file name).
    • `output` is an absolute path to capture pyta data output. Default std out.
    """

    # Add reporters to an internal pylint data structure, for use with setting
    # custom pyta options in a Tuple, before (re)setting reporter.
    for reporter in REPORTERS:
        VALIDATORS[reporter.__name__] = reporter
    linter = reset_linter(config=local_config)
    current_reporter = reset_reporter(linter, output)

    # Try to check file, issue error message for invalid files.
    try:
        for locations in _get_valid_files_to_check(current_reporter, module_name, local_config):
            for file_py in get_file_paths(locations):
                # Load config file in user location. Construct new linter each
                # time, so config options don't bleed to unintended files.
                linter = reset_linter(config=local_config, file_linted=file_py)
                # Assume the local config will NOT set a new reporter.
                linter.set_reporter(current_reporter)
                current_reporter.register_file(file_py)
                if not _verify_pre_check(file_py):
                    continue  # Check the other files
                linter.check(file_py)  # Lint !
                current_reporter.print_messages(level)
                current_reporter.reset_messages()  # Clear lists for any next file.
        current_reporter.output_blob()
    except Exception as e:
        print('Unexpected error encountered - please report this to david@cs.toronto.edu!')
        print('Error message: "{}"'.format(e))
        raise e


def doc(msg_id):
    """Open a webpage explaining the error for the given message."""
    msg_url = HELP_URL + '#' + msg_id
    print('Opening {} in a browser.'.format(msg_url))
    webbrowser.open(msg_url)
