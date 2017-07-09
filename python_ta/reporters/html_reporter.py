import os
import webbrowser
from collections import namedtuple

from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from base64 import b64encode

from .color_reporter import ColorReporter

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
TEMPLATE_FILE = 'template.txt'
OUTPUT_FILE = 'output.html'

class HTMLReporter(ColorReporter):
    _SPACE = '&nbsp;'
    _BREAK = '<br/>'
    _COLOURING = {'black': '<span class="black">',
                  'bold': '<span>',
                  'code-heading': '<span>',
                  'style-heading': '<span>',
                  'code-name': '<span>',
                  'style-name': '<span>',
                  'highlight': '<span class="highlight">',
                  'grey': '<span class="grey">',
                  'gbold': '<span class="gbold">',
                  'reset': '</span>'}

    def __init__(self, source_lines=None, module_name=''):
        super().__init__(source_lines, module_name)
        self.messages_by_file = []

    # Override this method
    def print_message_ids(self):
        # Sort the messages.
        self.sort_messages()
        # Call these two just to fill snippet attribute of Messages
        # (and also to fix weird bad-whitespace thing):
        self._colour_messages_by_type(style=False)
        self._colour_messages_by_type(style=True)

        MessageSet = namedtuple('MessageSet', 'filename code style')
        append_set = MessageSet(filename=self.filename_to_display(self.current_file_linted),
                               code=dict(self._sorted_error_messages),
                               style=dict(self._sorted_style_messages))
        self.messages_by_file.append(append_set)

    def output_blob(self):
        """Output to the template after all messages."""

        template = Environment(loader=FileSystemLoader(TEMPLATES_DIR)).get_template(TEMPLATE_FILE)

        # Embed resources so the output html can go anywhere, independent of assets.
        with open(os.path.join(TEMPLATES_DIR, 'pyta_logo_markdown.png'), 'rb+') as image_file:
            # Encode img binary to base64 (+33% size), decode to remove the "b'"
            pyta_logo_base64_encoded = b64encode(image_file.read()).decode()

        # Date/time (24 hour time) format:
        # Generated: ShortDay. ShortMonth. PaddedDay LongYear, Hour:Min:Sec
        dt = 'Generated: ' + str(datetime.now().
                                 strftime('%a. %b. %d %Y, %H:%M:%S'))
        output_path = os.path.join(os.getcwd(), OUTPUT_FILE)
        with open(output_path, 'w') as f:
            f.write(template.render(date_time=dt,
                                    mod_name=self._module_name,
                                    pyta_logo=pyta_logo_base64_encoded,
                                    code_err_title=self.code_err_title,
                                    style_err_title=self.style_err_title,
                                    no_err_message=self.no_err_message,
                                    messages_by_file=self.messages_by_file))
        print('Opening your report in a browser...')
        output_url = 'file:///{}'.format(output_path)
        webbrowser.open(output_url)

    _display = None
