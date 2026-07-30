app_name = "prime_shito"
app_title = "Prime Shito"
app_publisher = "Build With Moi"
app_description = "Shito Manufacturing "
app_email = "buildwithmoinow@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "prime_shito",
# 		"logo": "/assets/prime_shito/logo.png",
# 		"title": "Prime Shito",
# 		"route": "/prime_shito",
# 		"has_permission": "prime_shito.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/prime_shito/css/prime_shito.css"
# app_include_js = "/assets/prime_shito/js/prime_shito.js"

# include js, css files in header of web template
# web_include_css = "/assets/prime_shito/css/prime_shito.css"
# web_include_js = "/assets/prime_shito/js/prime_shito.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "prime_shito/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "prime_shito/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "prime_shito.utils.jinja_methods",
# 	"filters": "prime_shito.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "prime_shito.install.before_install"
# after_install = "prime_shito.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "prime_shito.uninstall.before_uninstall"
# after_uninstall = "prime_shito.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "prime_shito.utils.before_app_install"
# after_app_install = "prime_shito.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "prime_shito.utils.before_app_uninstall"
# after_app_uninstall = "prime_shito.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "prime_shito.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "prime_shito.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"prime_shito.tasks.all"
# 	],
# 	"daily": [
# 		"prime_shito.tasks.daily"
# 	],
# 	"hourly": [
# 		"prime_shito.tasks.hourly"
# 	],
# 	"weekly": [
# 		"prime_shito.tasks.weekly"
# 	],
# 	"monthly": [
# 		"prime_shito.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "prime_shito.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "prime_shito.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "prime_shito.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "prime_shito.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["prime_shito.utils.before_request"]
# after_request = ["prime_shito.utils.after_request"]

# Job Events
# ----------
# before_job = ["prime_shito.utils.before_job"]
# after_job = ["prime_shito.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"prime_shito.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# Installation
# ------------

after_install = "prime_shito.install.after_install"

# Website
# -------
# The storefront IS the main website, so the SPA is the home page.
home_page = "shop"

# Explicit routes rather than a `/<path:app_path>` catch-all. A root catch-all
# would shadow /login, /me, /update-password, ERPNext's /orders portal pages and
# every future www/ page, and would defeat Frappe's 404 caching.
website_route_rules = [
	{"from_route": "/packs", "to_route": "shop"},
	{"from_route": "/packs/<path:app_path>", "to_route": "shop"},
	{"from_route": "/cart", "to_route": "shop"},
	{"from_route": "/checkout", "to_route": "shop"},
	{"from_route": "/checkout/<path:app_path>", "to_route": "shop"},
	{"from_route": "/track", "to_route": "shop"},
	{"from_route": "/track/<path:app_path>", "to_route": "shop"},
	{"from_route": "/payment/<path:app_path>", "to_route": "shop"},
	{"from_route": "/about", "to_route": "shop"},
	{"from_route": "/contact", "to_route": "shop"},
	{"from_route": "/unsubscribe", "to_route": "shop"},
]

# Document Events
# ---------------

doc_events = {
	"Shito Pack": {
		"on_update": "prime_shito.api.catalog.clear_storefront_cache",
		"on_trash": "prime_shito.api.catalog.clear_storefront_cache",
	},
	"Shito Delivery Zone": {
		"on_update": "prime_shito.api.catalog.clear_storefront_cache",
		"on_trash": "prime_shito.api.catalog.clear_storefront_cache",
	},
}
