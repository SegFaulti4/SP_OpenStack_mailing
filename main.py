import openstack
import logging
import smtplib
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
        logger.info('')


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


def main():
    with open('sample.log', 'wb'):
        pass

    logger = logging.getLogger("exampleApp")
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler("sample.log")
    formatter = logging.Formatter('%(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    log_filter = {
        'image': [
            'checksum',
            'container_format',
            'created_at',
            'disk_format',
            'is_hidden',
            'is_protected',
            'hash_algo',
            'hash_value',
            'min_disk',
            'min_ram',
            'size',
            'store',
            'status',
            'updated_at',
            'virtual_size',
            'visibility',
            'file',
            'locations',
            'direct_url',
            'url',
            'metadata',
            'architecture',
            'hypervisor_type',
            'instance_type_rxtx_factor',
            'instance_uuid',
            'needs_config_drive',
            'kernel_id',
            'os_distro',
            'os_version',
            'needs_secure_boot',
            'os_shutdown_timeout',
            'ramdisk_id',
            'vm_mode',
            'hw_cpu_sockets',
            'hw_cpu_cores',
            'hw_cpu_threads',
            'hw_disk_bus',
            'hw_cpu_policy',
            'hw_cpu_thread_policy',
            'hw_rng_model',
            'hw_machine_type',
            'hw_scsi_model',
            'hw_serial_port_count',
            'hw_video_model',
            'hw_video_ram',
            'hw_watchdog_action',
            'os_command_line',
            'hw_vif_model',
            'is_hw_vif_multiqueue_enabled',
            'is_hw_boot_menu_enabled',
            'vmware_adaptertype',
            'vmware_ostype',
            'has_auto_disk_config',
            'os_type',
            'os_admin_user',
            'hw_qemu_guest_agent',
            'os_require_quiesce',
            'schema',
            'location',
            'tags'
        ],
        'security_group': [
            'created_at',
            'description',
            'stateful',
            'project_id',
            'updated_at',
            'revision_number',
            'location',
            'tags',
        ],
        'volume': [
            'links',
            'availability_zone',
            'source_volume_id',
            'description',
            'snapshot_id',
            'size',
            'image_id',
            'is_bootable',
            'metadata',
            'volume_image_metadata',
            'status',
            'attachments',
            'created_at',
            'project_id',
            'migration_status',
            'migration_id',
            'replication_status',
            'extended_replication_status',
            'consistency_group_id',
            'replication_driver_data',
            'is_encrypted',
            'location'
        ],
        'server': [
            'links',
            'access_ipv4',
            'access_ipv6',
            'addresses',
            'admin_password',
            'attached_volumes',
            'availability_zone',
            'block_device_mapping',
            'config_drive',
            'created_at',
            'description',
            'disk_config',
            'flavor_id',
            'flavor',
            'has_config_drive',
            'host_status',
            'hypervisor_hostname',
            'is_locked',
            'kernel_id',
            'launch_index',
            'launched_at',
            'metadata',
            'networks',
            'personality',
            'power_state',
            'progress',
            'project_id',
            'ramdisk_id',
            'reservation_id',
            'root_device_name',
            'scheduler_hints',
            'server_groups',
            'status',
            'task_state',
            'terminated_at',
            'trusted_image_certificates',
            'updated_at',
            'vm_state',
            'location',
            'tags',
            'compute_host',
            'host_id',
            'hostname',
            'image_id',
            'image',
            'instance_name',
            'key_name',
            'user_data'
        ],
        'user': [
            'default_project_id',
            'description',
            'domain_id',
            'is_enabled',
            'links',
            'password',
            'password_expires_at',
            'location'
        ],
        'properties': [
            'owner_specified.openstack.md5',
            'owner_specified.openstack.object',
            'owner_specified.openstack.sha256',
            'public',
            'stores',
            'project',
            'project_domain',
            'isp',
            'base_image_ref',
            'boot_roles',
            'image_location',
            'image_state',
            'image_type',
            'owner_project_name',
            # 'owner_user_name',
            # 'user_id',
            'shared',
        ],
        'security_group_rules': [
            # 'id',
            'tenant_id',
            # 'security_group_id',
            'ethertype',
            'direction',
            'protocol',
            'port_range_min',
            'port_range_max',
            'remote_ip_prefix',
            'remote_group_id',
            'description',
            'tags',
            'created_at',
            'updated_at',
            'revision_number',
            'project_id',
        ]
    }

    openstack_resources = {}

    conn = openstack.connection.from_config(cloud="openstack")
    openstack_resources['image'] = [_ for _ in conn.image.images()]
    openstack_resources['security_group'] = [_ for _ in conn.network.security_groups()]
    openstack_resources['volume'] = [_ for _ in conn.block_storage.volumes()]
    openstack_resources['server'] = [_ for _ in conn.compute.servers()]
    openstack_resources['user'] = [_ for _ in conn.identity.users()]
    conn.close()

    for res in openstack_resources:
        log_resource(logger, openstack_resources[res], res, log_filter[res],
                     prop_filter=log_filter['properties'], sgr_filter=log_filter['security_group_rules'])

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

    for name in user_resources:
        logger.info(name + ':')
        for res in user_resources[name]:
            log_resource(logger, user_resources[name][res], res, log_filter[res], prefix_str='\t',
                         prop_filter=log_filter['properties'], sgr_filter=log_filter['security_group_rules'])

    smtp_obj = smtplib.SMTP_SSL('smtp.rambler.ru:465')
    smtp_obj.login('makar.popov01@rambler.ru', )
    msg = MIMEMultipart()
    msg['From'] = 'makar.popov01@rambler.ru'
    msg['To'] = 'makar.popov01@rambler.ru'
    msg['Subject'] = 'OpenStack'
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


if __name__ == '__main__':
    main()
