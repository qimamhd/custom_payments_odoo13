# -*- coding: utf-8 -*-
{
    'name': 'Custom Payments odoo 13---',
	'version': '13.0.1.0.0',
	'summary': 'custom forms',
	'category': 'Tools',
	'author': 'Developers team',
	'maintainer': 'qimamhd-tech Techno Solutions',
	'company': 'qimamhd-tech Techno Solutions',
	'website': 'https://www.qimamhd-tech.com',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr_attendance', 'sale',],

    # always loaded
    'data': [
        'accouting/security/ir.model.access.csv',
        'accouting/security/security.xml',
        'accouting/views/payment_view.xml',
        'accouting/views/res_config_setting.xml',
        # 'accouting/views/set_cst_cntr_required.xml',
        # 'accouting/views/res_config_setting.xml',
        # 'accouting/views/show_cost_item.xml',
        'accouting/reports/payment_report.xml',
	#'wizards/recap.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,

}
