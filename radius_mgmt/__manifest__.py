{
    'name': "RADIUS Account Management",
    'summary': 'Manage Radius Accounts with Prepaid Generation',
    'version': '1.0',
    'depends': ['base', 'account.invoicing'],
    'author': "Nathaniel Lew Aquino",
	'price': 130,
	'currency': 'EUR',
	'license': 'OPL-1',
    'category': 'RADIUS Management',
    'description': """
    
    """,
    # data files always loaded at installation
    'data': [
	    'security/radius_v2_security.xml',
        'security/ir.model.access.csv',
		'data/radius_mgmt_data.xml',
		'views/radius_mgmt_views.xml',
		'views/radius_v1_views.xml',
		'views/radius_v2_views.xml',
		'views/res_partner_views.xml',
		'wizard/prepaid_wizard.xml'
    ],
    #'images': ['images/main_screenshot.jpg','images/main_1.jpg','images/main_2.jpg','images/main_3.jpg','images/main_4.jpg']
}