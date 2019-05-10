{
    'name': "BIR Forms for Accounting",
    'author': "Nathaniel Lew Aquino",
    'license': 'OPL-1',
    'version': '1.0',
    'summary': "BIR Philippines Forms Generation",
    'description': """
    
    """,
    'category': 'Accounting',
    'website': 'https://ithinksols.com',
    'images': [
    ],
    'depends': ['base', 'account_invoicing'],
    'data': ['security/ir.model.access.csv',

             'views/views.xml',

             'templates/templates.xml',
             ],
    'qweb': [
    ],
    'test': [
    ],
    'js': [
    ],
    'external_dependencies': {
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
