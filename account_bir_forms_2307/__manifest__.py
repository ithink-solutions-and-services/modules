{
    'name': "BIR Form 2307",
    'author': "Nathaniel Lew Aquino",
    'license': 'OPL-1',
    'version': '1.0',
    'summary': "Download BIR Form 2307 in vendor bills",
    'description': """
        Module to enable downloading Certificate of Creditable Tax Withheld on Vendor Bills
    """,
    'category': 'Accounting',
    'website': 'https://ithinksols.com',
    'depends': ['base', 'account_bir','pdf_forms'],
    'data': [
             'data/account_bir_forms_slspi_data.xml',
             'wizard/account_bir_forms_slspi_wizard_views.xml'
             ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
