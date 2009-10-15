"""
SugarCRM wizard. Last checked with:
* Cherokee 0.99.25
* SugarCE 5.5.0
"""
import validations
from config import *
from util import *
from Page import *
from Wizard import *
from Wizard_PHP import wizard_php_get_info
from Wizard_PHP import wizard_php_get_source_info

NOTE_SOURCES  = _("Path to the directory where the Sugar CRM source code is located. (Example: /usr/share/sugar)")
NOTE_WEB_DIR  = _("Web directory where you want Sugar CRM to be accessible. (Example: /crm)")
NOTE_HOST     = _("Host name of the virtual host that is about to be created.")
ERROR_NO_SRC  = _("Does not look like a Sugar CRM source directory.")
ERROR_NO_WEB  = _("A web directory must be provided.")
ERROR_NO_HOST = _("A host name must be provided.")

CONFIG_DIR = """
# The PHP rule comes here

%(pre_rule_minus1)s!match = directory
%(pre_rule_minus1)s!match!directory = %(web_dir)s
%(pre_rule_minus1)s!match!final = 0
%(pre_rule_minus1)s!document_root = %(local_src_dir)s

%(pre_rule_minus2)s!handler = redir
%(pre_rule_minus2)s!handler!rewrite!1!show = 1
%(pre_rule_minus2)s!handler!rewrite!1!substring = %(web_dir)s/index.php
%(pre_rule_minus2)s!match = request
%(pre_rule_minus2)s!match!request = ^/.*/.*\.php

%(pre_rule_minus3)s!handler = redir
%(pre_rule_minus3)s!handler!rewrite!1!show = 1
%(pre_rule_minus3)s!handler!rewrite!1!substring = %(web_dir)s/index.php
%(pre_rule_minus3)s!match = request
%(pre_rule_minus3)s!match!request = emailmandelivery.php

%(pre_rule_minus4)s!handler = redir
%(pre_rule_minus4)s!handler!rewrite!1!show = 0
%(pre_rule_minus4)s!handler!rewrite!1!substring = %(web_dir)s/log_file_restricted.html
%(pre_rule_minus4)s!match = request
%(pre_rule_minus4)s!match!request = ^/(.*\.log.*|not_imported_.*txt)
"""

CONFIG_SRV = """
%(pre_vsrv)s!nick = %(host)s
%(pre_vsrv)s!document_root = %(local_src_dir)s
%(pre_vsrv)s!directory_index = index.php,index.html

%(pre_rule_plus3)s!handler = redir
%(pre_rule_plus3)s!handler!rewrite!1!show = 1
%(pre_rule_plus3)s!handler!rewrite!1!substring = /index.php
%(pre_rule_plus3)s!match = request
%(pre_rule_plus3)s!match!request = ^/.*/.*\.php

%(pre_rule_plus2)s!handler = redir
%(pre_rule_plus2)s!handler!rewrite!1!show = 1
%(pre_rule_plus2)s!handler!rewrite!1!substring = /index.php
%(pre_rule_plus2)s!match = request
%(pre_rule_plus2)s!match!request = emailmandelivery.php

%(pre_rule_plus1)s!handler = redir
%(pre_rule_plus1)s!handler!rewrite!1!show = 0
%(pre_rule_plus1)s!handler!rewrite!1!substring = /log_file_restricted.html
%(pre_rule_plus1)s!match = request
%(pre_rule_plus1)s!match!request = ^/(.*\.log.*|not_imported_.*txt)

# The PHP rule comes here

%(pre_rule_minus1)s!handler = common
%(pre_rule_minus1)s!handler!iocache = 0
%(pre_rule_minus1)s!match = default
"""

SRC_PATHS = [
    "/usr/share/sugar",         # Debian, Fedora
    "/var/www/*/htdocs/sugar",  # Gentoo
    "/srv/www/htdocs/sugar",    # SuSE
    "/usr/local/www/data/sugar" # BSD
]

def is_sugar_dir (path, cfg, nochroot):
    path = validations.is_local_dir_exists (path, cfg, nochroot)
    module_inc = os.path.join (path, 'include/entryPoint.php')
    if not os.path.exists (module_inc):
        raise ValueError, ERROR_NO_SRC
    return path

DATA_VALIDATION = [
    ("tmp!wizard_sugar!sources", (is_sugar_dir, 'cfg')),
    ("tmp!wizard_sugar!host",    (validations.is_new_host, 'cfg')),
    ("tmp!wizard_sugar!web_dir",  validations.is_dir_formated)
]


class Wizard_VServer_Sugar (WizardPage):
    ICON = "sugarcrm.png"
    DESC = "Configure a new virtual server for Sugar CRM."

    def __init__ (self, cfg, pre):
        WizardPage.__init__ (self, cfg, pre,
                             submit = '/vserver/wizard/Sugar',
                             id     = "Sugar_Page1",
                             title  = _("Sugar Wizard"),
                             group  = WIZARD_GROUP_MANAGEMENT)

    def show (self):
        return True

    def _render_content (self, url_pre):
        txt  = '<h1>%s</h1>' % (self.title)
        guessed_src = path_find_w_default (SRC_PATHS)

        txt += '<h2>Sugar</h2>'
        table = TableProps()
        self.AddPropEntry (table, _('New Host Name'),    'tmp!wizard_sugar!host',    NOTE_HOST,    value="sugar.example.com")
        self.AddPropEntry (table, _('Source Directory'), 'tmp!wizard_sugar!sources', NOTE_SOURCES, value=guessed_src)
        txt += self.Indent(table)

        txt += '<h2>Logging</h2>'
        txt += self._common_add_logging()

        form = Form (url_pre, add_submit=True, auto=False)
        return form.Render(txt, DEFAULT_SUBMIT_VALUE)

    def _op_apply (self, post):
        # Store tmp, validate and clean up tmp
        self._cfg_store_post (post)

        self._ValidateChanges (post, DATA_VALIDATION)
        if self.has_errors():
            return

        self._cfg_clean_values (post)

        # Incoming info
        local_src_dir = post.pop('tmp!wizard_sugar!sources')
        host          = post.pop('tmp!wizard_sugar!host')
        pre_vsrv      = cfg_vsrv_get_next (self._cfg)

        # Add PHP Rule
        from Wizard_PHP import Wizard_Rules_PHP
        php_wizard = Wizard_Rules_PHP (self._cfg, pre_vsrv)
        php_wizard.show()
        php_wizard.run (pre_vsrv, None)

        # Replacement
        php_info = wizard_php_get_info (self._cfg, pre_vsrv)
        php_rule = int (php_info['rule'].split('!')[-1])

        pre_rule_plus3  = "%s!rule!%d" % (pre_vsrv, php_rule + 3)
        pre_rule_plus2  = "%s!rule!%d" % (pre_vsrv, php_rule + 2)
        pre_rule_plus1  = "%s!rule!%d" % (pre_vsrv, php_rule + 1)
        pre_rule_minus1 = "%s!rule!%d" % (pre_vsrv, php_rule - 1)

        # Common static
        pre_rule_plus4  = "%s!rule!%d" % (pre_vsrv, php_rule + 4)
        self._common_add_usual_static_files (pre_rule_plus4)

        # Add the new rules
        config = CONFIG_SRV % (locals())
        self._apply_cfg_chunk (config)
        self._common_apply_logging (post, pre_vsrv)


class Wizard_Rules_Sugar (WizardPage):
    ICON = "sugarcrm.png"
    DESC = "Configures Sugar CRM inside a public web directory."

    def __init__ (self, cfg, pre):
        WizardPage.__init__ (self, cfg, pre,
                             submit = '/vserver/%s/wizard/Sugar'%(pre.split('!')[1]),
                             id     = "Sugar_Page1",
                             title  = _("Sugar Wizard"),
                             group  = WIZARD_GROUP_MANAGEMENT)

    def show (self):
        # Check for PHP
        php_info = wizard_php_get_info (self._cfg, self._pre)
        if not php_info:
            self.no_show = "PHP support is required."
            return False
        return True

    def _render_content (self, url_pre):
        guessed_src = path_find_w_default (SRC_PATHS)

        table = TableProps()
        self.AddPropEntry (table, _('Web Directory'),   'tmp!wizard_sugar!web_dir', NOTE_WEB_DIR, value="/sugar")
        self.AddPropEntry (table, _('Source Directory'),'tmp!wizard_sugar!sources', NOTE_SOURCES, value=guessed_src)

        txt  = '<h1>%s</h1>' % (self.title)
        txt += self.Indent(table)
        form = Form (url_pre, add_submit=True, auto=False)
        return form.Render(txt, DEFAULT_SUBMIT_VALUE)

    def _op_apply (self, post):
        # Store tmp, validate and clean up tmp
        self._cfg_store_post (post)

        self._ValidateChanges (post, DATA_VALIDATION)
        if self.has_errors():
            return

        self._cfg_clean_values (post)

        # Incoming info
        local_src_dir = post.pop('tmp!wizard_sugar!sources')
        web_dir       = post.pop('tmp!wizard_sugar!web_dir')

        # Replacement
        php_info = wizard_php_get_info (self._cfg, self._pre)
        php_rule = int (php_info['rule'].split('!')[-1])

        pre_rule_minus4 = "%s!rule!%d" % (self._pre, php_rule - 4)
        pre_rule_minus3 = "%s!rule!%d" % (self._pre, php_rule - 3)
        pre_rule_minus2 = "%s!rule!%d" % (self._pre, php_rule - 2)
        pre_rule_minus1 = "%s!rule!%d" % (self._pre, php_rule - 1)

        # Add the new rules
        config = CONFIG_DIR % (locals())
        self._apply_cfg_chunk (config)