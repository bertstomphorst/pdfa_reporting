# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, _
from odoo.tools.misc import find_in_path

import base64
import os
import re
import io
import subprocess
from distutils.version import LooseVersion
from tempfile import NamedTemporaryFile

import logging

_logger = logging.getLogger(__name__)


# region Ghostscript helpers

def _get_ghostscript_bin():
    ghostscript_bin = find_in_path('ghostscript')
    if ghostscript_bin is None:
        raise IOError
    return ghostscript_bin


# Check the presence of Ghostscript and return its version at Odoo start-up

ghostscript_state = 'install'
try:
    process_presence = subprocess.Popen([_get_ghostscript_bin(), '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
except (OSError, IOError):
    _logger.info('You need Ghostscript to convert pdfs.')
else:
    _logger.info('Will use the Ghostscript binary at %s' % _get_ghostscript_bin())
    out_presence, err_presence = process_presence.communicate()
    version = re.search(b'([0-9.]+)', out_presence).group(0).decode('ascii')
    if LooseVersion(version) < LooseVersion('9.50'):
        _logger.info('Upgrade Ghostscript to (at least) 9.50')
        ghostscript_state = 'upgrade'
    else:
        _logger.info('Ghostscript version ' + version)
        ghostscript_state = 'ok'


# endregion

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    pdfa_option = fields.Selection(string='PDF/A archiving',
                                   selection=[('no', 'None'),
                                              ('pdfa1b', 'PDF/A-1b'),
                                              ('pdfa2b', 'PDF/A-2b')
                                              ],
                                   help="PDF/A is an ISO-standardized version of the Portable Document Format (PDF) "
                                        "specialized for the digital preservation of electronic documents.\n"
                                        "Sometimes, customers require to receive invoices in PDF/A-format",
                                   default='no')

    def _render_qweb_pdf(self, res_ids=None, data=None):
        """ override to process pdfa_option """

        # get default output
        result, data_format = super()._render_qweb_pdf(res_ids, data)

        # process pdfa_option
        result = self.run_ghostscript(result, self.pdfa_option)

        return result, data_format

    @staticmethod
    def run_ghostscript(pdf, pdfa_option):
        _logger.info('execute with PDF/A-option: %s' % pdfa_option)

        if not pdfa_option or pdfa_option == 'no':
            return pdf

        # prepare files for input/output
        with NamedTemporaryFile(delete=False, suffix='.pdf') as input_file:
            input_file.write(pdf)
        input_file_name = input_file.name

        output_file = NamedTemporaryFile(delete=False, suffix='.pdf')
        output_file.close()
        output_file_name = output_file.name

        # prepare commandline args for ghostscript
        command_args = []

        if pdfa_option == 'pdfa1b':
            command_args.extend([
                '-dPDFA=1',
                '-sColorConversionStrategy=UseDeviceIndependentColor',
                '-dPDFACompatibilityPolicy=1',
            ])
        elif pdfa_option == 'pdfa2b':
            command_args.extend([
                '-dPDFA=2',
                '-sColorConversionStrategy=UseDeviceIndependentColor',
                '-dPDFACompatibilityPolicy=2',
                '-dEmbedAllFonts=true',
                '-dMaxSubsetPct=100',
                '-dSubsetFonts=true'
            ])

        shared_args = []
        shared_args.extend([
            '-sDEVICE=pdfwrite',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            '-dNOOUTERSAVE',
            '-sOutputFile=' + output_file_name,
            input_file_name])

        # execute
        try:
            ghostscript = [_get_ghostscript_bin()] + command_args + shared_args
            # _logger.info('execute ghostscript: %s' % ghostscript)

            process = subprocess.Popen(ghostscript, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()

            if err:
                _logger.info('ghostscript failed . Message: %s' % err)

            # read converted pdf and remove the used files
            with open(output_file_name, 'rb') as converted_file:
                pdf = converted_file.read()

            os.unlink(input_file_name)
            os.unlink(output_file_name)

        except (OSError, IOError, ValueError):
            raise

        return pdf
