import argparse
import getpass
import keyring
import logging
import smtplib
import yaml
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import StringIO

import openstack

from os_logging import log_openstack_resources as log_os_res
from os_logging import log_user_resources as log_usr_res
from os_sort import sort_resources_by_users as sort_res


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-ne", "--newpass_email", required=False, help="Set new email password",
                        action="store_true")
    parser.add_argument("-no", "--newpass_openstack", required=False, help="Set new openstack cloud password",
                        action="store_true")
    parser.add_argument("-yc", "--yaml_config", help="Set yaml configuration file path",
                        type=str, default='config.yaml')
    arguments = parser.parse_args()
    return arguments


def init_info_logger(logger_config):
    with open(logger_config['filename'], 'wb'):
        pass
    logger = logging.getLogger("mainLogger")
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logger_config['filename'])
    formatter = logging.Formatter(logger_config['Formatter'])
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def init_openstack_connection(config):
    return openstack.connection.Connection(region_name=config['region_name'],
                                           identity_api_version=config['identity_api_version'],
                                           interface=config['interface'],
                                           auth=config['auth'])


def init_openstack_resources(conn):
    openstack_resources = {'image': [_ for _ in conn.image.images()],
                           'security_group': [_ for _ in conn.network.security_groups()],
                           'volume': [_ for _ in conn.block_storage.volumes()],
                           'server': [_ for _ in conn.compute.servers()],
                           'user': [_ for _ in conn.identity.users()]}
    return openstack_resources


def make_resources_msg_body(username, resources, msg_prefix=None, msg_infix=None, msg_postfix=None, output_filter=None):
    if msg_prefix is None:
        msg_prefix = ''
    if msg_infix is None:
        msg_infix = ''
    if msg_postfix is None:
        msg_postfix = ''
    body_stream = StringIO()
    tmp_logger = logging.getLogger("tmpLogger")
    tmp_logger.setLevel(logging.INFO)
    sh = logging.StreamHandler(body_stream)
    sh.setFormatter(logging.Formatter('%(message)s'))
    tmp_logger.addHandler(sh)
    log_usr_res(tmp_logger, {username + msg_infix: resources}, output_filter)
    return msg_prefix + body_stream.getvalue() + msg_postfix


def send_user_resources_via_mail(logger, user_resources, username_to_emails, email_config, output_filter=None):
    if email_config.get('max_msg_per_connection', None) is None:
        max_msg = 3
    else:
        max_msg = email_config['max_msg_per_connection']

    msg_sent = 0
    smtp_obj = smtplib.SMTP_SSL(email_config['host'])
    smtp_obj.login(email_config['From'], email_config['password'])

    for name in user_resources:
        msg = MIMEMultipart()
        msg['From'] = email_config['From']
        msg['Subject'] = email_config['Subject']
        if email_config.get('To', None) is not None:
            msg['To'] = email_config['To']
        elif username_to_emails.get(name, None) is not None:
            msg['To'] = username_to_emails[name]
        if msg.get('To', None) is not None:
            body = make_resources_msg_body(name, user_resources[name], email_config['msg_prefix'],
                                           email_config['msg_infix'], email_config['msg_postfix'],
                                           output_filter)
            logger.debug(body)
            msg.attach(MIMEText(body, 'plain'))
            smtp_obj.send_message(msg)

            msg_sent += 1
            if msg_sent > max_msg:
                smtp_obj.quit()
                smtp_obj = smtplib.SMTP_SSL(email_config['host'])
                smtp_obj.login(email_config['From'], email_config['password'])
                msg_sent = 0

    smtp_obj.quit()


def module(logger_config, openstack_config, email_config, output_filter=None):
    logger = init_info_logger(logger_config)
    log_filter = output_filter

    conn = init_openstack_connection(openstack_config)
    openstack_resources = init_openstack_resources(conn)
    conn.close()

    log_os_res(logger, openstack_resources, log_filter)
    user_resources = sort_res(openstack_resources)
    log_usr_res(logger, user_resources, log_filter)

    username_to_emails = {}
    for user in openstack_resources['user']:
        username_to_emails[user.id] = user.email
    send_user_resources_via_mail(logger, user_resources, username_to_emails, email_config, output_filter)


def main():
    args = parse_arguments()
    filename = args.yaml_config

    with open(filename, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    openstack_system_name = 'openstack'
    email_system_name = 'email'
    username = 'default'

    if args.newpass_openstack:
        password = getpass.getpass(prompt="Enter openstack password:")
        try:
            keyring.set_password(openstack_system_name, username, password)
        except Exception as error:
            print('Error: {}'.format(error))

    if args.newpass_email:
        password = getpass.getpass(prompt="Enter email password:")
        try:
            keyring.set_password(email_system_name, username, password)
        except Exception as error:
            print('Error: {}'.format(error))

    if config['clouds']['openstack']['auth'].get('password', None) is None:
        config['clouds']['openstack']['auth']['password'] = keyring.get_password(openstack_system_name, username)
    if config['email'].get('password', None) is None:
        config['email']['password'] = keyring.get_password(email_system_name, username)
    module(config['logger'], config['clouds']['openstack'], config['email'], config['output_filter'])


if __name__ == '__main__':
    main()
