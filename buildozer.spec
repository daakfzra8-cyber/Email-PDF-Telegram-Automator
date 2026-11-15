[app]

# (str) Title of your application
title = Email Telegram Sync

# (str) Package name
package.name = emailtelegramsync

# (str) Package domain (needed for android packaging)
package.domain = org.emailtelegram

# (list) Source files to include (let it find python files)
source.include_exts = py,png,jpg,kv,atlas

# (list) Application requirements
requirements = python3,kivy,requests,sqlite3,urllib3,certifi,idna,charset-normalizer

# (str) Supported orientation (portrait, landscape or all)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET, ACCESS_NETWORK_STATE

[buildozer]
log_level = 2
warn_on_root = 1
