import keyring as kr


ldap_pwd = kr.get_password('ldap', 'password')
django_secret = kr.get_password('django', 'SECRET_KEY')
netbox_api = kr.get_password('netbox', 'netbox_api')
cisco_pwd = kr.get_password('cisco', 'password')
nj_pwd = kr.get_password('nj', 'password')
