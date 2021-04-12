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
    applied_sgs = {'name': [], 'id': []}

    for user in openstack_resources['user']:
        userid_to_names[user.id] = user.name
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
