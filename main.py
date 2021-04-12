import openstack
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def main():
    with open('sample.log', 'wb'):
        pass

    logger = logging.getLogger("exampleApp")
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler("sample.log")
    formatter = logging.Formatter('%(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    def log_resource(resource, res_name, filter_list=None):
        if filter_list is None:
            filter_list = []
        for res in resource:
            logger.info(res_name + ':')
            for x in res:
                if x not in filter_list:
                    if x == 'properties':
                        logger.info('\t' + x + ':')
                        for prop in res[x]:
                            logger.info('\t\t' + prop + ': ' + str(res[x][prop]))
                        logger.info('\t\t' + str(res[x]))
                    elif x == 'security_group_rules':
                        logger.info('\t' + x + ':')
                        for rule in res[x]:
                            logger.info('\t\trule:')
                            for y in rule:
                                logger.info('\t\t\t' + y + ': ' + str(rule[y]))
                    elif x == 'security_groups':
                        logger.info('\t' + x + ':')
                        for group in res[x]:
                            logger.info('\t\tgroup:')
                            for y in group:
                                logger.info('\t\t\t' + y + ': ' + str(group[y]))
                    else:
                        logger.info('\t' + str(x) + ': ' + str(res[x]))
            logger.info('')

    log_images_filter = [
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
    ]
    log_security_groups_filter = [
        'created_at',
        'description',
        'stateful',
        'project_id',
        'updated_at',
        'revision_number',
        'location',
        'tags',
    ]
    log_volume_filter = [
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
    ]
    log_server_filter = [
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
    ]
    log_user_filter = [
        'default_project_id',
        'description',
        'domain_id',
        'is_enabled',
        'links',
        'password',
        'password_expires_at',
        'location'
    ]

    conn = openstack.connection.from_config(cloud="openstack")
    images = [_ for _ in conn.image.images()]
    security_groups = [_ for _ in conn.network.security_groups()]
    volumes = [_ for _ in conn.block_storage.volumes()]
    servers = [_ for _ in conn.compute.servers()]
    users = [_ for _ in conn.identity.users()]
    conn.close()

    log_resource(images, 'image', log_images_filter)
    log_resource(security_groups, 'security_group', log_security_groups_filter)
    log_resource(volumes, 'volume', log_volume_filter)
    log_resource(servers, 'server', log_server_filter)
    log_resource(users, 'user', log_user_filter)

    resources = {}
    id_to_names = {}
    name_to_emails = {}
    applied_sgs_name = []
    applied_sgs_id = []

    for user in users:
        id_to_names[user.id] = user.name
        name_to_emails[user.id] = user.email
        resources[user.name] = {'servers': [], 'volumes': [], 'images': [], 'security_groups': []}

    for server in servers:
        if server.get('security_groups', None) is not None:
            for sg in server['security_groups']:
                if sg.get('name', None) is not None:
                    applied_sgs_name.append(sg['name'])
                elif sg.get('id', None) is not None:
                    applied_sgs_id.append(sg['id'])
        resources[id_to_names[server.user_id]]['servers'].append(server)

    for volume in volumes:
        resources[id_to_names[volume.user_id]]['volumes'].append(volume)

    for image in images:
        if image.get('owner', None) is not None and id_to_names.get(image['owner'], None) is not None:
            resources[id_to_names[image['owner']]]['images'].append(image)
        elif image.get('owner_id', None) is not None and id_to_names.get(image['owner_id'], None) is not None:
            resources[id_to_names[image['owner_id']]]['images'].append(image)
        elif image.get('properties', {}).get('owner_user_name', None) is not None:
            resources[image['properties']['owner_user_name']]['images'].append(image)
        elif image.get('properties', {}).get('user_id', None) is not None:
            resources[image['properties']['owner_user_name']]['images'].append(image)
        else:
            image_type = image.get('properties', {}).get('image_type', '')
            if image_type == '' or image_type == 'image':
                for user in users:
                    if image['name'].find(user.name) != -1:
                        resources[user.name]['images'].append(image)
            elif image_type == 'snapshot':
                for user in users:
                    for server in resources[user.name]['servers']:
                        if image['name'].find(server.name) != -1:
                            resources[user.name]['images'].append(image)

    for sec in security_groups:
        if sec['name'] not in applied_sgs_name and sec['id'] not in applied_sgs_id:
            for user in users:
                if sec['name'].find(user.name) != -1:
                    resources[user.name]['security_groups'].append(sec)

    for name in resources:
        logger.info(name + ':')
        for res in resources[name]:
            log_resource(resources[name][res], res)

    smtp_obj = smtplib.SMTP_SSL('smtp.rambler.ru:465')
    smtp_obj.login('makar.popov01@rambler.ru', )
    msg = MIMEMultipart()
    msg['From'] = 'makar.popov01@rambler.ru'
    msg['To'] = 'makar.popov01@rambler.ru'
    msg['Subject'] = 'OpenStack'
    body = ''
    for name in resources:
        body += name + ', your resources in the cloud:'
        for res in resources[name]:
            body += '\n\t' + res + ' :' + str(resources[name][res])
        body += '\n'
    print(body)
    msg.attach(MIMEText(body, 'plain'))
    smtp_obj.send_message(msg)
    smtp_obj.quit()


if __name__ == '__main__':
    main()
