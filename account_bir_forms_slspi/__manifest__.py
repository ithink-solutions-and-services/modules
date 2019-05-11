{
    'name': "BIR Forms for Accounting",
    'author': "Nathaniel Lew Aquino",
    'license': 'OPL-1',
    'version': '1.0',
    'summary': "BIR Philippines Forms Generation",
    'description': """
        Base module for BIR Forms Generation
    """,
    'category': 'Accounting',
    'website': 'https://ithinksols.com',
    'depends': ['base', 'account_invoicing'],
    'data': ['security/ir.model.access.csv',
             'views/account_bir_views.xml.xml',
             'wizard/account_bir_forms_wizard_views.xml'
             ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
