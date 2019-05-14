{
    'name': "Billing with Accounting",
    'author': "Nathaniel Lew Aquino",
    'license': 'OPL-1',
    'version': '1.0',
    'summary': "Billing module with invoicing, receipt printing, reports",
    'category': 'Billing',
    'website': 'www.ithinksols.com',
    'depends': ['base', 'account'],
    'data': [
             'data/ir_sequence_data.xml',
             'data/ir_actions_report_data.xml',

             'views/account_billing_views.xml',
             ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
