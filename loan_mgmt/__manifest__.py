{
    'name': "Loan Management",
    'summary': 'Manage Loans with Accounting',
    'version': '1.0',
    'depends': ['base', 'contacts', 'account_invoicing'],
    'author': "Nathaniel Lew Aquino",
	'price': 130,
	'currency': 'EUR',
	'license': 'OPL-1'
    'category': 'Loan Management',
    'description': """
    Icon made by monkik(https://www.flaticon.com/authors/monkik)
    """,
    # data files always loaded at installation
    'data': [
        'security/loan_mgmt_security.xml',
        'security/ir.model.access.csv',
        'views/loan_mgmt_view.xml',
        'views/policy_view.xml',
        'views/res_partner_view.xml',
        'views/requirement_view.xml',
        'views/loan_type_view.xml',
        'views/loan_request_view.xml',
        'views/loan_request_line_view.xml',
        'data/ir_sequence_data.xml',
        'views/account_payment_view.xml',
        'views/account_invoice_view.xml',
        'views/js.xml',
        'views/loan_mgmt_dashboard_view.xml',
    ],
}