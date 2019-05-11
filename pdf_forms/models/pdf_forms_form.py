import time

from odoo import fields, models, api, _
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError
import datetime
from dateutil.relativedelta import relativedelta
from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from PyPDF2.generic import BooleanObject, NameObject, IndirectObject
import io as StringIO
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import base64
from collections import OrderedDict
from odoo.tools import email_split
import random
import datetime
import warnings
from odoo import SUPERUSER_ID
import re
import io
import zipfile


import logging

_logger = logging.getLogger(__name__)

def repl_func(m):
    """process regular expression match groups for word upper-casing problem"""
    return m.group(1) + m.group(2).upper()

def extract_email(email):
    """ extract the email address from a user-friendly email address """
    addresses = email_split(email)
    return addresses[0] if addresses else ''

class FormMapping(models.Model):
    _name = 'pdf_forms.form.mapping'
    
    @api.multi
    def get_name(self):
        for rec in self:
            rec.name = (rec.form_id.name if rec.form_id else '') + '-' + rec.pdf_field_name

    name = fields.Char(string='Name', compute="get_name", store=True)
    form_id = fields.Many2one('pdf_forms.form', string="PDF Form", required=True)
    model_id = fields.Many2one(related="form_id.model_id", store=True)
    pdf_field_name = fields.Char(string="PDF Field Name", required=True)
    model_field_name = fields.Many2one('ir.model.fields', string="Model Field Name")
    model_field_sub = fields.Char(string='Model Field Sub Field', help='Subfield for Many2one and One2many fields')

    @api.depends('model_field_name','model_field_sub','model_id')
    def _model_field_sub_type(self):
        for rec in self:
            if rec.model_field_name and rec.model_field_sub:
                field_string = 'partner_id.' + rec.model_field_name.name + rec.model_field_sub
                while '[' in field_string and ']' in field_string:
                    field_string = re.sub(r'\[[0-9]+\]', '', field_string)
                split_string = field_string.split('.')
                model = rec.model_id.model
                field_type = False
                field_name = False
                for i in range(len(split_string)):
                    if i != 0:
                        get_field = self.env['ir.model.fields'].sudo().search([('model_id.model','=',model),('name','=',split_string[i])])
                        field_name = get_field.name
                        field_type = get_field.ttype
                        model = get_field.relation if get_field.relation else model
                rec.model_field_sub_type = field_type
                rec.model_field_sub_parent = model
                rec.model_field_sub_field = field_name
            elif rec.model_field_name and not rec.model_field_sub:
                rec.model_field_sub_type = rec.model_field_name.ttype
                rec.model_field_sub_parent = rec.model_id.model
                rec.model_field_sub_field = rec.model_field_name.name

    model_field_sub_field = fields.Char(string="Actual Field", compute="_model_field_sub_type", store=True)
    model_field_sub_type = fields.Char(string="Type of Actual Field", compute="_model_field_sub_type", store=True)
    model_field_sub_parent = fields.Char(string="Parent Model of Actual Field", compute="_model_field_sub_type", store=True)
    model_field_sub_domain = fields.Char(string="Domain for searching many2one fields")
    type = fields.Selection([('checkbox','Checkbox'),('generic','Generic')], string="PDF Field Type")
    checkbox_prefix = fields.Char(string="Checkbox Value Prefix")
    checkbox_not = fields.Boolean(string="Check if this is a No checkbox", default=False)
    select_m2o = fields.Boolean(string="Check to search for other many2one field instead of writing (For many2one fields)")
    visible_if = fields.Char("Visible if this field is true")
    static_value = fields.Char(string="Static Value to be written in the form")
    field_depends = fields.Char(string="Fields separated by comma, if this field is a computed field")
    write_not_app = fields.Boolean(string="Write Not Applicable if Empty?")

class Form(models.Model):
    _name = 'pdf_forms.form'
    
    name = fields.Char('Form', required=True)
    model_id = fields.Many2one('ir.model', string='Apply To', copy=False)
    pdf_name_field = fields.Many2one('ir.model.fields', string="Downloaded PDF filename field", copy=False)
    mapping_ids = fields.One2many('pdf_forms.form.mapping', 'form_id', string="Mappings")
    temp_bin = fields.Binary("Temporary Binary Field")
    temp_bin_2 = fields.Binary("Temporary Binary Field 2")
    datas = fields.Binary(string='File Content')
    datas_fname = fields.Char('File Name')
    company_id = fields.Many2one('res.company', string="Company")
    
    @api.depends('mapping_ids')
    def _count_mapping(self):
        for rec in self:
            rec.count_mapping = len(rec.mapping_ids)
    
    count_mapping = fields.Integer(string="Mapping Count", compute="_count_mapping", store=True)
    state = fields.Selection([('draft','Draft'), ('active','Active')], string='Status', required=True, track_visibility='onchange', copy=False, default='draft')
    action_id = fields.Many2one('ir.actions.server', string="Server Action")

    @api.model
    def create(self, vals):
        if 'model_id' in vals:
            if vals['model_id']:
                form_id = self.env['pdf_forms.form'].sudo().search([('model_id','=',vals['model_id']), ('name','=',vals['name'])])
                if form_id and len(form_id) >= 1:
                    raise UserError("Cannot have the two forms with the same Name and Model!")
        res = super(Form, self).create(vals)
        
        return res


    @api.multi
    def write(self, vals):
        for rec in self:
            if 'model_id' in vals:
                if vals['model_id']:
                    form_id = self.env['pdf_forms.form'].sudo().search([('id','!=',rec.id), ('model_id','=',vals['model_id']), ('name','=',rec.name)])
                    if form_id and len(form_id) >= 1:
                        raise UserError("Cannot have the two forms with the same Name and Model!")
        res = super(Form, self).write(vals)
        return res

    @api.multi
    def active(self):
        self.ensure_one()
        if not self.action_id:
            vals = {
                'name': 'Print ' + self.name,
                'model_id': self.model_id.id,
                'state': 'code',
                'is_pdf_form': True,
                'code': 'action = env["pdf_forms.form"].sudo().browse(' + str(self.id) + ').print_pdf(str(str(records.ids)[:-1])[1:])',
                'pdf_form_id': self.id,
            }
            self.action_id = self.env['ir.actions.server'].create(vals).id
        else:
            self.draft()
            self.action_id.model_id = self.model_id.id
        if not self.action_id.binding_model_id:
            self.action_id.create_action()
        self.state = 'active'
        return True

    @api.multi
    def draft(self):
        self.ensure_one()
        if self.action_id:
            self.action_id.unlink_action()
        self.state = 'draft'
        return True

    @api.multi
    def button_active(self):
        for rec in self:
            rec.active()
        return True

    @api.multi
    def button_draft(self):
        for rec in self:
            rec.draft()
        return True

    @api.multi
    def toggle_state(self):
        for rec in self:
            if rec.state == 'draft':
                rec.active()
            else:
                rec.draft()
        return True

    @api.multi
    def unlink(self):
        for rec in self:
            rec.mapping_ids.unlink()
            rec.button_draft()
            rec.action_id.unlink()
        return super(Form, self).unlink()

    def _getFields(self, obj, tree=None, retval=None, fileobj=None):
        """
        Extracts field data if this PDF contains interactive form fields.
        The *tree* and *retval* parameters are for recursive use.

        :param fileobj: A file object (usually a text file) to write
            a report to on all interactive form fields found.
        :return: A dictionary where each key is a field name, and each
            value is a :class:`Field<PyPDF2.generic.Field>` object. By
            default, the mapping name is used for keys.
        :rtype: dict, or ``None`` if form data could not be located.
        """
        fieldAttributes = {'/FT': 'Field Type', '/Parent': 'Parent', '/T': 'Field Name', '/TU': 'Alternate Field Name',
                           '/TM': 'Mapping Name', '/Ff': 'Field Flags', '/V': 'Value', '/DV': 'Default Value'}
        if retval is None:
            retval = OrderedDict()
            catalog = obj.trailer["/Root"]
            # get the AcroForm tree
            if "/AcroForm" in catalog:
                tree = catalog["/AcroForm"]
            else:
                return None
        if tree is None:
            return retval

        obj._checkKids(tree, retval, fileobj)
        for attr in fieldAttributes:
            if attr in tree:
                # Tree is a field
                obj._buildField(tree, retval, fileobj, fieldAttributes)
                break
                
        if "/Fields" in tree:
            fields = tree["/Fields"]
            for f in fields:
                field = f.getObject()
                obj._buildField(field, retval, fileobj, fieldAttributes)

        return OrderedDict((k, v.get('/V', '')) for k, v in retval.items())
    
    
    @api.multi
    def generate_pdf_field_mappings(self):
        for rec in self:
            try:
                rec.mapping_ids.unlink()
            except Exception as e:
                pass
            pdf = PdfFileReader(io.BytesIO(base64.b64decode(rec.datas)), strict=False)
            text_fields = pdf.getFormTextFields()
            fields = rec._getFields(pdf)
            dict = {}
            for k,v in fields.items():
                if k not in text_fields:
                    dict[str(k)] = str(v)
            checkbox_fields = dict
            for k,v in text_fields.items():
                self.env['pdf_forms.form.mapping'].create({'form_id': rec.id, 'pdf_field_name': k, 'type': 'generic'})
            for k,v in checkbox_fields.items():
                self.env['pdf_forms.form.mapping'].create({'form_id': rec.id, 'pdf_field_name': k, 'type': 'checkbox', 'checkbox_prefix': '/' if '/' in v else ''})
        return True

            
    def set_need_appearances_writer(self, writer):
        try:
            catalog = writer._root_object
            # get the AcroForm tree
            if "/AcroForm" not in catalog:
                writer._root_object.update({
                    NameObject("/AcroForm"): IndirectObject(len(writer._objects), 0, writer)
                })

            need_appearances = NameObject("/NeedAppearances")
            writer._root_object["/AcroForm"][need_appearances] = BooleanObject(True)
            # del writer._root_object["/AcroForm"]['NeedAppearances']
            return writer

        except Exception as e:
            pass
        return writer
            
            
    def updateCheckboxValues(self, page, fields):
        for j in range(0, len(page['/Annots'])):
            writer_annot = page['/Annots'][j].getObject()
            for field in fields:
                if writer_annot.get('/T') == field:
                    writer_annot.update({
                        NameObject("/V"): NameObject(fields[field]),
                        NameObject("/AS"): NameObject(fields[field])
                    })
                    
    @api.multi
    def get_file_contents(self, rec_ids=[]):
        self.ensure_one()
        try:
            if rec_ids and len(rec_ids) > 0:
                rec = self
                pdf = PdfFileReader(io.BytesIO(base64.b64decode(rec.datas)))
                final_pdf = PdfFileWriter()
                att_ids = []
                for rec_id in rec_ids:
                    output_pdf = PdfFileWriter()
                    output_pdf.appendPagesFromReader(pdf)
                    text_dict = {}
                    checkbox_dict = {}
                    rec_id = self.env[self.model_id.model].sudo().browse(int(rec_id))
                    for mapping_id in rec.mapping_ids:
                        if mapping_id.model_field_name or mapping_id.static_value:
                            model_field = mapping_id.model_field_name
                            model_field_sub = mapping_id.model_field_sub
                            try:
                                val = eval('rec_id.' + model_field.name + (model_field_sub or '')) if not mapping_id.static_value else mapping_id.static_value
                                visible = True
                                if mapping_id.visible_if:
                                    try:
                                        visible = eval('rec_id.' + mapping_id.visible_if)
                                    except:
                                        pass
                                if mapping_id.type == 'generic' and visible:
                                    if mapping_id.static_value:
                                        text_dict[mapping_id.pdf_field_name] = val
                                    else:
                                        if mapping_id.write_not_app:
                                            text_dict[mapping_id.pdf_field_name] = str(val) if val else 'Not Applicable'
                                        else:
                                            text_dict[mapping_id.pdf_field_name] = str(val) if val else ''
                                else:
                                    if mapping_id.static_value:
                                        checkbox_dict[mapping_id.pdf_field_name] = (mapping_id.checkbox_prefix or '') + val
                                    else:
                                        if mapping_id.checkbox_not:
                                            checkbox_dict[mapping_id.pdf_field_name] = (mapping_id.checkbox_prefix or '') + ('0' if val else '1')
                                        else:
                                            checkbox_dict[mapping_id.pdf_field_name] = (mapping_id.checkbox_prefix or '') + ('1' if val else '0')
                                    
                            except Exception as e:
                                _logger.error("Error Writing PDF Field " + mapping_id.pdf_field_name + ": " + str(e))
                    num_pages = output_pdf.getNumPages()
                    for i in range(output_pdf.getNumPages()):
                        if '/Annots' in output_pdf.getPage(i):
                            output_pdf.updatePageFormFieldValues(output_pdf.getPage(i), text_dict)
                            self.updateCheckboxValues(output_pdf.getPage(i), checkbox_dict)
                    output_pdf = rec.set_need_appearances_writer(output_pdf)
                    bs = io.BytesIO()
                    output_pdf.write(bs)
                    get_file_name_field = rec.pdf_name_field.name if rec.pdf_name_field else False
                    try:
                        get_file_name = ""
                        if get_file_name_field:
                            get_file_name = eval("rec_id." + get_file_name_field) + ' - ' + rec.name
                        else:
                            get_file_name = str(rec_id.id) + ' - ' + rec.name
                    except:
                        get_file_name = str(rec_id.id)
                    att_ids.append(self.env['ir.attachment'].sudo().create({
                        'name': "TEMP",
                        'datas_fname': get_file_name + ".pdf",
                        'datas' :  base64.b64encode(bs.getvalue()),
                        'type' : 'binary',
                        'description': 'No Description'
                    }).id)
                    #merger.append(PdfFileReader(bs))
                    #final_pdf.appendPagesFromReader(pdf_temp)
                bts = io.BytesIO()
                if len(rec_ids) == 1:
                    temporary_file = self.env['ir.attachment'].sudo().browse(att_ids[0])
                    bts = io.BytesIO(base64.b64decode(temporary_file.datas))
                    temporary_file.sudo().unlink()
                else:
                    buff = io.BytesIO()
                    zip_archive = zipfile.ZipFile(buff, mode='w')
                    temp = []
                    for att_id in att_ids:
                        temporary_file = self.env['ir.attachment'].sudo().browse(att_id)
                        temp.append(io.BytesIO())
                        temp[len(temp)-1].write(base64.b64decode(temporary_file.datas))
                        zip_archive.writestr(temporary_file.datas_fname , temp[len(temp)-1].getvalue())
                        temporary_file.sudo().unlink() 
                    zip_archive.close()
                    bts = buff
                    #encoded_string = base64.b64encode(buff.getvalue())
                #final_pdf.write(bts)
        except Exception as e:
            _logger.error(str(e))
            raise UserError("Error Filling PDF. Please contact the administrator.\n\n" + str(e))
        return bts.getvalue()


    @api.multi
    def print_pdf(self, rec_id):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/pdf/download?f=' + str(self.id) + '&id=' + str(rec_id),
            'target': 'new',
        }
        

