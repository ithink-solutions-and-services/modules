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


class Bir1604cf(models.Model):
    _name = 'bir.1604cf'

    @api.depends('create_date')
    def _get_name(self):
        for rec in self:
            rec.name = "BIR 1604cf - " + str(fields.Date.from_string(str(rec.create_date)))

    name = fields.Char(string="Name",compute="_get_name")
    path_id = fields.Many2one('bir.paths', string="File Path")
    generated_file = fields.Many2one('ir.attachment', string='Generated File')
    generated_file_datas = fields.Binary(related="generated_file.datas",store=True)
    generated_file_name = fields.Char(related="generated_file.datas_fname",store=True)

    @api.one
    def generate_pdf(self):
        fullpath = str(self.path_id.name)
        path = str(self.path_id.path)
        filename = str(self.path_id.filename)
        packet = StringIO.BytesIO()
        cv=canvas.Canvas(packet, pagesize=legal)
        cv.setFont("Courier", 8)
        cv.drawString(1, 1, "Test Output")
#        cv.showPage()
        cv.save()
        packet.seek(0)
        result = PdfFileWriter()
        new_pdf = PdfFileReader(packet)
        if os.path.exists(fullpath):
            existing_pdf = PdfFileReader(open(fullpath, "rb"))
            page = existing_pdf.getPage(0)
            page.mergePage(new_pdf.getPage(0))
            result.addPage(page)
            outputStream = open(path+"/"+self.name+".pdf", "wb")
            result.write(outputStream)
            outputStream.close()
            attachment_data = {}
            encoded_string = ''
            if os.path.exists(path+"/"+self.name+".pdf"):
                with open((path+"/"+self.name+".pdf"), "rb") as pdf:
                    encoded_string = base64.b64encode(pdf.read())
            attachment_obj = self.env['ir.attachment']
            attachment_data = {
                'name':  (self.name or '') + _(' (Scheme attachment)'),
                'datas_fname': self.name+".pdf",
                'datas' : encoded_string,
                'type' : 'binary',
                'description': self.name or _('No Description'),
                'res_model':'bir.1604cf',
                'res_id': self.id,
            }
            attachment_id = attachment_obj.create(attachment_data)
            self.write({'generated_file' : attachment_id.id})
