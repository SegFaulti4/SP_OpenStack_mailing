import logging


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
