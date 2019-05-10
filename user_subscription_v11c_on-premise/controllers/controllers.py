# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
import odoo
import imghdr
import functools
import io
import os
import sys
import jinja2
from odoo import http, tools
from odoo.addons.web.controllers.main import Database, Binary
from odoo.addons.web.controllers import main
from odoo.modules import get_resource_path
import base64
from dateutil.relativedelta import relativedelta
import datetime
import json
import werkzeug
from odoo.addons.web.controllers.main import Home
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
import smtplib

import logging
_logger = logging.getLogger(__name__)

key = "WWWPRODATANETINC"

def ensure_db(redirect='/web/database/selector'):
    # This helper should be used in web client auth="none" routes
    # if those routes needs a db to work with.
    # If the heuristics does not find any database, then the users will be
    # redirected to db selector or any url specified by `redirect` argument.
    # If the db is taken out of a query parameter, it will be checked against
    # `http.db_filter()` in order to ensure it's legit and thus avoid db
    # forgering that could lead to xss attacks.
    db = request.params.get('db') and request.params.get('db').strip()

    # Ensure db is legit
    if db and db not in http.db_filter([db]):
        db = None

    if db and not request.session.db:
        # User asked a specific database on a new session.
        # That mean the nodb router has been used to find the route
        # Depending on installed module in the database, the rendering of the page
        # may depend on data injected by the database route dispatcher.
        # Thus, we redirect the user to the same page but with the session cookie set.
        # This will force using the database route dispatcher...
        r = request.httprequest
        url_redirect = werkzeug.urls.url_parse(r.base_url)
        if r.query_string:
            # in P3, request.query_string is bytes, the rest is text, can't mix them
            query_string = iri_to_uri(r.query_string)
            url_redirect = url_redirect.replace(query=query_string)
        request.session.db = db
        abort_and_redirect(url_redirect)

    # if db not provided, use the session one
    if not db and request.session.db and http.db_filter([request.session.db]):
        db = request.session.db

    # if no database provided and no database in session, use monodb
    if not db:
        db = db_monodb(request.httprequest)

    # if no db can be found til here, send to the database selector
    # the database selector will redirect to database manager if needed
    if not db:
        werkzeug.exceptions.abort(werkzeug.utils.redirect(redirect, 303))

    # always switch the session to the computed db
    if db != request.session.db:
        request.session.logout()
        abort_and_redirect(request.httprequest.url)

    request.session.db = db

class Home(Home):

    @http.route('/web/login', type='http', auth="none", sitemap=False)
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid is not False:
                request.params['login_success'] = True
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            request.uid = old_uid
            if not http.request.env['res.users'].sudo().search([('active','=',False),('login','=',request.params['login'])]):
                values['error'] = _("Wrong login/password")
            else:
                try:
                    if http.request.env['res.users'].sudo().search([('active','=',False),('login','=',request.params['login']),('sub_type','=','trial')]):
                        values['error'] = _("Trial Account has Expired")
                    elif http.request.env['res.users'].sudo().search([('active','=',False),('login','=',request.params['login']),('sub_type','=','activated')]):
                        values['error'] = _("Account has Expired")
                    else:
                        values['error'] = _("Wrong login/password")
                except AccessDenied as e:
                    pass

        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employee can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

class UserActivate(http.Controller):


    def decode(self, key, string):
        encoded_chars = []
        for i in range(len(string)):
            key_c = key[i % len(key)]
            encoded_c = chr((ord(string[i]) - ord(key_c) + 256) % 256)
            encoded_chars.append(encoded_c)
        encoded_string = ''.join(encoded_chars)
        return encoded_string


    @http.route('/renew', auth='public')
    def send_email_renew_request(self, **post):
        type = post.get('xx')
        if type == "pjopiq":
            user_id = http.request.env['res.users'].sudo().search([('active','=',False),('login','=', post.get('x'))])
        elif type == "jksdiq":
            user_id = http.request.env['res.users'].sudo().search([('active','=',True),('login','=', post.get('x'))])
        else:
            return werkzeug.utils.redirect('/web/login')
        if not user_id:
            return werkzeug.utils.redirect('/web/login')
        try:
            message = "Test"
            sender = "nathaniel.aquino28@gmail.com"
            receivers = "naquino@prodatanet.com.ph"
            smtpObj = smtplib.SMTP(host='mail.go2canada.com.ph', port=465)
            smtpObj.ehlo()
            smtpObj.starttls()
            smtpObj.ehlo()
            smtpObj.login(user="naquino@ubi-online.com", password="prodatanet")
            smtpObj.sendmail(sender, receivers, message)
            smtpObj.quit()
#        template = False
#        try:
#            template = http.request.env.ref('user_activation_v11c.email_template_renew_subscription', raise_if_not_found=True)
#            template.sudo().with_context(lang=user_id.lang).sudo().send_mail(user_id.id, force_send=True, raise_exception=True)
#            user_id.sudo().write({'renew_request': True})
        except Exception as e:
            _logger.error(str(e))
        finally:
            return werkzeug.utils.redirect('/web/login')


    @http.route('/oflskdied', auth='public')
    def subscribe_user(self, **post):
        post_data = json.loads(self.decode(key, post.get('oeldpq')))
        activation_token = post_data['token']
        if not http.request.env['res.users.token'].sudo().search([('name','=',activation_token)]):
            email_adds = []
            if ';' in post_data['email']:
                email_adds = post_data['email'].split(';')
            else:
                email_adds.append(post_data['email'])
            activation_type = post_data['expiration_type']
            activation_duration = int(post_data['duration'])
            group = post_data['group']
            new_expiry = datetime.datetime.now().date().strftime("%Y-%m-%d")
            if activation_type == 'months':
                new_expiry = datetime.datetime.strptime(new_expiry, "%Y-%m-%d") + relativedelta(months=activation_duration)
            elif activation_type == 'years':
                new_expiry = datetime.datetime.strptime(new_expiry, "%Y-%m-%d") + relativedelta(years=activation_duration)
            for email in email_adds:
                vals = {
                    'expiry_date': new_expiry.strftime("%Y-%m-%d"),
                    'active': True,
                    'sub_type': 'activated',
                    'renew_request': False,
                    'first_notice': False,
                    'second_notice': False,
                    'login': email,
                    'name': email,
                    'password': 'a'
                }
                add_group_id = False
                if group == 'billing':
                    add_group_id = http.request.env.ref("account.group_account_invoice")
                elif group == 'billingmanager':
                    add_group_id = http.request.env.ref("account.group_account_manager")
                if add_group_id:
                    user_id = http.request.env['res.users'].sudo().create(vals)
                    try:
                        if group in ['billing','billingmanager']:
                            http.request.env.ref("sales_team.group_sale_manager").sudo().write({'users': [(3, user_id.id)]})
                            http.request.env.ref("sales_team.group_sale_salesman_all_leads").sudo().write({'users': [(3, user_id.id)]})
                            http.request.env.ref("sales_team.group_sale_salesman").sudo().write({'users': [(3, user_id.id)]})
                            http.request.env.ref("account.group_account_manager").sudo().write({'users': [(3, user_id.id)]})
                    except Exception as e:
                        pass
                    try:
                        if group == 'billing':
                            http.request.env.ref("sales_team.group_sale_salesman").sudo().write({'users': [(4, user_id.id)]})
                        elif group == 'billingmanager':
                            http.request.env.ref("sales_team.group_sale_salesman_all_leads").sudo().write({'users': [(4, user_id.id)]})
                    except Exception as e:
                        pass
                    add_group_id.sudo().write({'users': [(4, user_id.id)]})
                    token_vals = {
                        'user_id': user_id.id,
                        'name': activation_token
                    }
                    http.request.env['res.users.token'].sudo().create(token_vals)

        return werkzeug.utils.redirect('/web/login')



    @http.route('/kskjapowi', auth='public')
    def activate_user(self, **post):
        global key
        post_data = json.loads(self.decode(key, post.get('oqwenm')))
        email_adds = []
        if ';' in post_data['email']:
            email_adds = str(post_data['email']).split(';')
        else:
            email_adds.append(post_data['email'])
        for email in email_adds:
            user_id = http.request.env['res.users'].sudo().browse(http.request.env['res.users'].sudo().search([('login','=ilike',email)]).id)
            user_id_inact = http.request.env['res.users'].sudo().browse(http.request.env['res.users'].sudo().search([('active','=',False),('login','=ilike',email)]).id)
            if user_id or user_id_inact:
                activation_token = post_data['token']
                if not http.request.env['res.users.token'].sudo().search([('name','=',activation_token)]):
                    activation_type = post_data['expiration_type']
                    activation_duration = int(post_data['duration'])
                    new_expiry = datetime.datetime.now().date().strftime("%Y-%m-%d")
                    if user_id:
                        if user_id.sub_type == 'activated':
                            new_expiry = user_id.expiry_date
    #                new_expiry = user_id.expiry_date if user_id else datetime.datetime.now().date().strftime("%Y-%m-%d")
                    if activation_type == 'months':
                        new_expiry = datetime.datetime.strptime(new_expiry, "%Y-%m-%d") + relativedelta(months=activation_duration)
                    elif activation_type == 'years':
                        new_expiry = datetime.datetime.strptime(new_expiry, "%Y-%m-%d") + relativedelta(years=activation_duration)
                    vals = {
                        'expiry_date': new_expiry.strftime("%Y-%m-%d"),
                        'active': True,
                        'renew_request': False,
                        'first_notice': False,
                        'second_notice': False,
                        'sub_type': 'activated',
                    }
                    user_id = user_id if user_id else user_id_inact
                    user_id.sudo().write(vals)
                    token_vals = {
                        'user_id': user_id.id,
                        'name': activation_token
                    }
                    http.request.env['res.users.token'].sudo().create(token_vals)
        return werkzeug.utils.redirect('/web/login')

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.user_subscription_v11c_on-premise', "views")
env = main.jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps
db_monodb = http.db_monodb

class BinaryCustom(Binary):
    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none", cors="*")
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        # Here we are changing the default logo with logo selected on debrand settings
        company_logo = request.env['res.company'].sudo().search([])[0].logo
        custom_logo = tools.image_resize_image(company_logo, (150, None))
        placeholder = functools.partial(get_resource_path, 'web', 'static', 'src', 'img')
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = odoo.SUPERUSER_ID

        if not dbname:
            response = http.send_file(placeholder(imgname + imgext))
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                if custom_logo:
#                    image_base64 = custom_logo.decode('base64')
                    image_base64 = base64.b64decode(custom_logo)
                    image_data = io.BytesIO(image_base64)
                    imgext = '.' + (imghdr.what(None, h=image_base64) or 'png')
                    response = http.send_file(image_data, filename=imgname + imgext, mtime=None)
                    request.env['res.company'].sudo().browse(1).sudo().write({'logo':  custom_logo})
                else:
                    with registry.cursor() as cr:
                        cr.execute("""SELECT c.logo_web, c.write_date
                                        FROM res_users u
                                   LEFT JOIN res_company c
                                          ON c.id = u.company_id
                                       WHERE u.id = %s
                                   """, (uid,))
                        row = cr.fetchone()
                        if row and row[0]:
                            image_base64 = str(row[0]).decode('base64')
                            image_data = io.BytesIO(image_base64)
                            imgext = '.' + (imghdr.what(None, h=image_base64) or 'png')
                            response = http.send_file(image_data, filename=imgname + imgext, mtime=row[1])
                        else:
                            response = http.send_file(placeholder('nologo.png'))

            except Exception as e:
                response = http.send_file(placeholder(imgname + imgext))
        return response


class OdooDebrand(Database):
    # Render the Database management html page
    def _render_template(self, **d):
        d.setdefault('manage', True)
        d['insecure'] = odoo.tools.config.verify_admin_password('admin')
        d['list_db'] = odoo.tools.config['list_db']
        d['langs'] = odoo.service.db.exp_list_lang()
        d['countries'] = odoo.service.db.exp_list_countries()
        d['pattern'] = main.DBNAME_PATTERN
        # databases list
        d['databases'] = []
        try:
            d['databases'] = http.db_list()
            d['incompatible_databases'] = odoo.service.db.list_db_incompatible(d['databases'])
        except odoo.exceptions.AccessDenied:
            monodb = db_monodb()
            if monodb:
                d['databases'] = [monodb]

        try:
            company_id = request.env['res.company'].sudo().search([])
            d['company_name'] = company_id and company_id[0].name
            d['favicon_url'] = company_id and company_id[0].favicon_url or ''
            d['company_logo_url'] = company_id and company_id[0].company_logo_url or ''
            return env.get_template("database_manager_extend.html").render(d)
        except Exception as e:
            _logger.error(str(e))
            d['company_name'] = ''
            d['favicon_url'] = ''
            d['company_logo_url'] = ''
            return main.env.get_template("database_manager.html").render(d)

