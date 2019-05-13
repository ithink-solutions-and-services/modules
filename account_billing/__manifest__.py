{
    'name': "Billing with Accounting",
    'author': "Nathaniel Lew Aquino",
    'license': 'OPL-1',
    'version': '1.0',
    'summary': "Billing module with invoicing, receipt printing, reports",
    'category': 'Billing',
    'website': 'www.ithinksols.com',
    'depends': ['base', 'account'],
    'data': ['security/ir.model.access.csv',

             'views/views.xml',

             'templates/templates.xml',
             ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
