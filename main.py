import openstack
import logging
import smtplib
import yaml
import argparse
import getpass
import keyring
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def log_properties(logger, properties, prop_filter=None, prefix_str=''):
    if prop_filter is None:
        prop_filter = []
    logger.info(prefix_str + 'properties:')
    for prop in properties:
        if prop not in prop_filter:
            logger.info(prefix_str + '\t' + prop + ': ' + str(properties[prop]))
            # logger.info("'" + prop + "',")


def log_security_group_rules(logger, sg_rules, sgr_filter=None, prefix_str=''):
    if sgr_filter is None:
        sgr_filter = []
    logger.info(prefix_str + 'security_group_rules:')
    for rule in sg_rules:
        logger.info(prefix_str + '\trule:')
        for y in rule:
            if y not in sgr_filter:
                logger.info(prefix_str + '\t\t' + y + ': ' + str(rule[y]))
                # logger.info("'" + y + "',")


def log_security_groups(logger, sec_groups, prefix_str=''):
    logger.info(prefix_str + 'security_groups:')
    for group in sec_groups:
        logger.info(prefix_str + '\tgroup: ' + group.name)


def log_resource(logger, resource, res_name, filter_list=None, prop_filter=None, sgr_filter=None, prefix_str=''):
    if filter_list is None:
        filter_list = []
    if prop_filter is None:
        prop_filter = []
    if sgr_filter is None:
        sgr_filter = []
    for res in resource:
        logger.info(prefix_str + res_name + ':')
        for x in res:
            if x not in filter_list:
                if x == 'properties':
                    log_properties(logger, res[x], prop_filter, prefix_str + '\t')
                elif x == 'security_group_rules':
                    log_security_group_rules(logger, res[x], sgr_filter, prefix_str + '\t')
                elif x == 'security_groups':
                    if res[x] is not None:
                        log_security_groups(logger, res[x], prefix_str + '\t')
                else:
                    logger.info(prefix_str + '\t' + str(x) + ': ' + str(res[x]))
                    # logger.info("'" + str(x) + "',")
        logger.info('')


def log_openstack_resources(logger, openstack_resources, log_filter=None):
    for res in openstack_resources:
        log_resource(logger, openstack_resources[res], res, None if log_filter is None else log_filter[res],
                     prop_filter=None if log_filter is None else log_filter['properties'],
                     sgr_filter=None if log_filter is None else log_filter['security_group_rules'])


def log_user_resources(logger, user_resources, log_filter=None):
    for name in user_resources:
        logger.info(name + ':')
        for res in user_resources[name]:
            log_resource(logger, user_resources[name][res], res,
                         None if log_filter is None else log_filter[res], prefix_str='\t',
                         prop_filter=None if log_filter is None else log_filter['properties'],
                         sgr_filter=None if log_filter is None else log_filter['security_group_rules'])


def sort_servers_by_users(user_resources, servers, userid_to_names):
    for server in servers:
        user_resources[userid_to_names[server.user_id]]['server'].append(server)


def sort_volumes_by_users(user_resources, volumes, userid_to_names):
    for volume in volumes:
        user_resources[userid_to_names[volume.user_id]]['volume'].append(volume)


def sort_images_by_users(user_resources, images, userid_to_names):
    for image in images:
        if image.get('owner', None) is not None and userid_to_names.get(image['owner'], None) is not None:
            user_resources[userid_to_names[image['owner']]]['image'].append(image)
        elif image.get('owner_id', None) is not None and userid_to_names.get(image['owner_id'], None) is not None:
            user_resources[userid_to_names[image['owner_id']]]['image'].append(image)
        elif image.get('properties', {}).get('owner_user_name', None) is not None:
            user_resources[image['properties']['owner_user_name']]['image'].append(image)
        elif image.get('properties', {}).get('user_id', None) is not None:
            user_resources[image['properties']['owner_user_name']]['image'].append(image)
        else:
            image_type = image.get('properties', {}).get('image_type', '')
            if image_type == '' or image_type == 'image':
                for userid in userid_to_names:
                    name = userid_to_names[userid]
                    if image['name'].find(name) != -1:
                        user_resources[name]['image'].append(image)
            elif image_type == 'snapshot':
                for userid in userid_to_names:
                    name = userid_to_names[userid]
                    for server in user_resources[name]['servers']:
                        if image['name'].find(server.name) != -1:
                            user_resources[name]['image'].append(image)


def sort_security_groups_by_users(user_resources, security_groups, userid_to_names, applied_sgs):
    for sec in security_groups:
        if sec['name'] not in applied_sgs['name'] and sec['id'] not in applied_sgs['id']:
            for userid in userid_to_names:
                name = userid_to_names[userid]
                if sec['name'].find(name) != -1:
                    user_resources[name]['security_group'].append(sec)


def sort_resources_by_users(openstack_resources):
    user_resources = {}
    userid_to_names = {}
    username_to_emails = {}
    applied_sgs = {'name': [], 'id': []}

    for user in openstack_resources['user']:
        userid_to_names[user.id] = user.name
        username_to_emails[user.id] = user.email
        user_resources[user.name] = {'server': [], 'volume': [], 'image': [], 'security_group': []}

    for server in openstack_resources['server']:
        if server.get('security_groups', None) is not None:
            for sg in server['security_groups']:
                if sg.get('name', None) is not None:
                    applied_sgs['name'].append(sg['name'])
                elif sg.get('id', None) is not None:
                    applied_sgs['id'].append(sg['id'])

    sort_servers_by_users(user_resources, openstack_resources['server'], userid_to_names)
    sort_volumes_by_users(user_resources, openstack_resources['volume'], userid_to_names)
    sort_images_by_users(user_resources, openstack_resources['image'], userid_to_names)
    sort_security_groups_by_users(user_resources, openstack_resources['security_group'], userid_to_names, applied_sgs)
    return user_resources


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


def mail_user_resources(logger, user_resources, email_config):
    smtp_obj = smtplib.SMTP_SSL(email_config['host'])
    smtp_obj.login(email_config['From'], email_config['password'])
    msg = MIMEMultipart()
    msg['From'] = email_config['From']
    msg['To'] = email_config['To']
    msg['Subject'] = email_config['Subject']
    body = ''
    for name in user_resources:
        body += name + ', your resources in the cloud:'
        for res in user_resources[name]:
            body += '\n\t' + res + ' :' + str(user_resources[name][res])
        body += '\n'
    logger.debug(body)
    msg.attach(MIMEText(body, 'plain'))
    # smtp_obj.send_message(msg)
    smtp_obj.quit()


def mail_openstack_resources(logger_config, openstack_config, email_config, output_filter=None):
    logger = init_info_logger(logger_config)
    log_filter = output_filter

    conn = init_openstack_connection(openstack_config)
    openstack_resources = init_openstack_resources(conn)
    conn.close()

    log_openstack_resources(logger, openstack_resources, log_filter)
    user_resources = sort_resources_by_users(openstack_resources)
    log_user_resources(logger, user_resources, log_filter)

    mail_user_resources(logger, user_resources, email_config)


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
    mail_openstack_resources(config['logger'], config['clouds']['openstack'], config['email'], config['output_filter'])


if __name__ == '__main__':
    main()
