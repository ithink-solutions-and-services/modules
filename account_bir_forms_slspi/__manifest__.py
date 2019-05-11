{
    'name': "BIR Summary List of Sales, Purchases, and Importations",
    'author': "Nathaniel Lew Aquino",
    'license': 'OPL-1',
    'version': '1.0',
    'summary': "Module to enable generation of Summary List of Sales, Purchases, and Importations",
    'description': """
        Module to enable generation of Summary List of Sales, Purchases, and Importations
    """,
    'category': 'Accounting',
    'website': 'https://ithinksols.com',
    'depends': ['base', 'account_bir'],
    'data': [
             'data/account_bir_forms_slspi_data.xml',
             'wizard/account_bir_forms_slspi_wizard_views.xml'
             ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
