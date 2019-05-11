# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.web.controllers.main import Home
from odoo.http import Controller, route,request
from openerp.addons.web.controllers.main import _serialize_exception, content_disposition        
import werkzeug
from odoo.tools import html_escape
import json
import logging
_logger = logging.getLogger(__name__)

class PdfFormsController(Home):

    @http.route(['/pdf/download'], type='http', auth="user")
    def get_pdf_form(self, f, id):
        try:
            form_id = request.env['pdf_forms.form'].browse(int(f))
            ids = []
            for str_id in str(id).split(', '):
                ids.append(int(str_id))
            pdf_content = form_id.sudo().get_file_contents(ids)
            if len(ids) > 0:
                if len(ids) > 1:
                    filename = form_id.name + ' - Multiple Records.zip'
                    content_type = 'application/zip'
                else:
                    record = request.env[form_id.model_id.model].sudo().browse(ids[0])
                    content_type = 'application/pdf'
                    filename = False
                    try:
                        filename = eval('record.' + form_id.pdf_name_field.name)
                        if filename:
                            filename = filename + ' - ' + form_id.datas_fname
                    except:
                        pass
            pdfhttpheaders = [('Content-Type', content_type), ('Content-Length', len(pdf_content))]
            response = request.make_response(pdf_content, headers=pdfhttpheaders)
            response.headers.add('Content-Disposition', content_disposition(filename if filename else form_id.datas_fname))
            response.set_cookie('fileToken', request.csrf_token())
            response.headers['Content-Disposition'] = response.headers['Content-Disposition'].replace('attachment', 'inline')
            return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
