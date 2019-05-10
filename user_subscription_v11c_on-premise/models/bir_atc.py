from odoo import models, fields, api, SUPERUSER_ID, _
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError

import io as StringIO
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, legal
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import base64
import os.path

import logging
_logger = logging.getLogger(__name__)


class BirAtc(models.Model):
    _name = 'bir.atc'

    name = fields.Char(string="ATC")
    nip = fields.Char(string='Nature of Income Payment')
    tax_rate = fields.Float(string="Tax Rate(%)")
    type = fields.Selection([('ind','Ind'),('corp','Corp')])
