# -*- coding: utf-8 -*-
{
    'name': "PDF Forms",

    'summary': """
        PDF Forms for any model""",

    'description': """
        Instructions:
            1. Prepare PDF Form fields. Field names should contain no space and ends with [0]
            2. Upload PDF Form
            3. Map PDF Form Fields
            4. Activate PDF Form
    """,

    'author': "Prodatanet",
    'website': "https://www.prodatanet.com.ph",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'PDF Forms',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/pdf_forms_view.xml',
        'views/pdf_forms_form_view.xml',
        'views/pdf_forms_form_mapping_view.xml'

    ],
    # only loaded in demonstration mode
#    'demo': [
#        'demo/demo.xml',
#    ],
}
