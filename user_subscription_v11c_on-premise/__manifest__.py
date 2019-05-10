# -*- coding: utf-8 -*-
{
    'name': "User Subscription",
    'description': "",
    'author': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account_invoicing', 'l10n_generic_coa','sale_management'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'data/user_activation_data.xml',
        'views/res_users_view.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/webclient_templates.xml',
        'data/mail_template_data.xml',
        'views/bir_paths_views.xml',
        'views/bir_atc_views.xml',
#        'views/bir_1604cf_views.xml',
#        'views/bir_1702q_views.xml',
#        'views/bir_2307_views.xml',
#        'views/bir_2550m_views.xml',
#        'views/bir_2551m_views.xml',
#        'views/bir_1601e_views.xml',
#        'views/bir_1601c_views.xml',
        'views/bir_main_menu_views.xml',
        'wizard/generate_pdf.xml',
        'wizard/generate_dat.xml',
        'report/bir_1601c_report_views.xml',
        'report/bir_1601e_report_views.xml',
        'report/bir_1702q_report_views.xml',
        'report/bir_2550m_report_views.xml',
        'report/bir_1601eq_report_views.xml',
        'report/bir_1604cf_report_views.xml',
        'report/bir_2307_report_views.xml',
        'report/bir_2551m_report_views.xml',
        'report/reports.xml',
        'views/account_invoice_views.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
#        'demo/demo.xml',
    ],
    'qweb': ['static/src/xml/base.xml'],
    'images': ["static/description/banner.gif"],
    'license': "AGPL-3",
    'installable': True,
    'application': True,
}
