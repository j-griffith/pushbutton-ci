import subprocess


def stackit(cloud, server, conf_file, branch='master', cinder_branch='master',
            use_floating_ip=False, ansible_log_dir='/tmp'):
    """Install devstack on the specified OpenStack Instance (server).

    Assumes a running Instance, installs devsack based on the provided
    parameters.

    :param cloud (os-cloud-config obj):
        The cloud you're operating on
    :param server (shade object):
        Server to install devstack on
    :param conf_file (str):
        location of local.conf template file
    :param branch (Optional str):
        devstack branch to use
    :param cinder_branch (Optional str):
        cinder branch to use, ie patchset id
        (refs/changes/02/291302/2)
    :param use_floating_ip (Optional bool):
        By default we use the private IP of
        the Instance to communicate with the Instance, set to True if you're
        running from a machine NOT in the cloud and need to use floating IP
        access.
    :param ansible_log_dir (Optional str):
        Location to dump log output from Ansible,
        default is /tmp
    Returns:
        (bool, str): True if succesful, False otherwise, and output from
        ansible playbook run.

    """
    host_ip = cloud.get_server_private_ip(server)
    if use_floating_ip:
        host_ip = cloud.get_server_public_ip(server)
    status = ''

    vars = 'hosts=%s,' % host_ip
    vars += ' devstack_conf=%s' % conf_file
    vars += ' results_dir=%s' % ansible_log_dir
    vars += ' patchset_ref=%s' % cinder_branch

    cmd = 'ansible-playbook ./stackbooks/install_devstack.yml --extra-vars '\
          '\"%s\" -i %s,' % (vars, host_ip)
    ansible_proc = subprocess.Popen(cmd, shell=True,
                                    stdout=subprocess.PIPE)
    output = ansible_proc.communicate()[0]

    if status == 'ok':
        return (True, output)
    else:
        return (False, output)


def run_tempest(cloud, server, use_floating_ip=False, ansible_log_dir='/tmp'):
    """Run tempest on the specified OpenStack Instance (server).

    Assumes a running devstack Instance with Tempest installed and configured.

    :param cloud (os-cloud-config obj):
        The cloud you're operating on
    :param server (shade object):
        Server to install devstack on
    :param use_floating_ip (Optional bool):
        By default we use the private IP of
        the Instance to communicate with the Instance, set to True if you're
        running from a machine NOT in the cloud and need to use floating IP
        access.
    :param ansible_log_dir (Optional str):
        Location to dump log output from Ansible,
        default is /tmp
    Returns:
        (bool, str): True if succesful, False otherwise, and output from
        ansible playbook run.
    """
    host_ip = cloud.get_server_private_ip(server)
    if use_floating_ip:
        host_ip = cloud.get_server_public_ip(server)

    status = ''

    vars = 'hosts=%s,' % host_ip
    vars += ' results_dir=%s' % ansible_log_dir

    cmd = 'ansible-playbook run_tempest.yml --extra-vars '\
          '\"%s\" -i %s,' % (vars, host_ip)
    ansible_proc = subprocess.Popen(cmd, shell=True,
                                    stdout=subprocess.PIPE)
    output = ansible_proc.communicate()[0]

    if status == 'ok':
        return (True, output)
    else:
        return (False, output)


def gather_logs(cloud, server, upload_script,
                use_floating_ip=False, ansible_log_dir='/tmp'):
    """Gather up logs from a CI Run.

    Gathers logs including stack.log.out, tempest output etc.
    :param cloud (os-cloud-config obj):
        The cloud you're operating on
    :param server (shade object):
        Server to install devstack on
    :param upload_script (str):
        Path of bash script to execute that gathers up the logs
    :param use_floating_ip (Optional bool):
        By default we use the private IP of
        the Instance to communicate with the Instance, set to True if you're
        running from a machine NOT in the cloud and need to use floating IP
        access.
    :param ansible_log_dir (Optional str):
        Location to dump log output from Ansible,
        default is /tmp
    Returns:
        (bool, str): True if succesful, False otherwise, and output from
        ansible playbook run.
    """
    host_ip = cloud.get_server_private_ip(server)
    if use_floating_ip:
        host_ip = cloud.get_server_public_ip(server)

    status = ''

    vars = 'hosts=%s,' % host_ip
    vars += ' results_dir=%s' % ansible_log_dir
    vars += ' upload_script=%s' % upload_script
    vars += ' instance_name=%s' % server.get('name')

    cmd = 'ansible-playbook run_cleanup.yml --extra-vars '\
          '\"%s\" -i %s,' % (vars, host_ip)
    ansible_proc = subprocess.Popen(cmd, shell=True,
                                    stdout=subprocess.PIPE)
    output = ansible_proc.communicate()[0]

    # TOOD(jdg): Figure out a way to parse ansible output here
    if status == 'ok':
        return (True, output)
    else:
        return (False, output)


def publish_results(web_server, publish_dir, local_results_dir):
    """Publish logs from CI Run on web server.

    Gathers logs including stack.log.out, tempest output etc.
    :param cloud (os-cloud-config obj):
        The cloud you're operating on
    :param server (shade object):
        Server to install devstack on
    :param upload_script (str):
        Path of bash script to execute that gathers up the logs
    :param use_floating_ip (Optional bool):
        By default we use the private IP of
        the Instance to communicate with the Instance, set to True if you're
        running from a machine NOT in the cloud and need to use floating IP
        access.
    :param ansible_log_dir (Optional str):
        Location to dump log output from Ansible,
        default is /tmp
    Returns:
        (bool, str): True if succesful, False otherwise, and output from
        ansible playbook run.
    """
    vars = 'hosts=%s,' % web_server
    vars += ' results_dir=%s' % local_results_dir
    vars += ' publish_dir=%s' % publish_dir

    cmd = 'ansible-playbook publish.yml --extra-vars '\
          '\"%s\" -i %s,' % (vars, web_server)
    ansible_proc = subprocess.Popen(cmd, shell=True,
                                    stdout=subprocess.PIPE)
    output = ansible_proc.communicate()[0]

    return output
