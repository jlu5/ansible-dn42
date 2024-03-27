import yaml
# Add a stub handler to ignore Ansible specific values like !vault
# See https://github.com/yaml/pyyaml/issues/86
yaml.add_multi_constructor('', lambda *args: None)

def yaml_load(filename):
    with open(filename, encoding='utf-8') as f:
        return yaml.full_load(f.read())

def get_hosts(yaml_content, include_private=False):
    """
    Get a list of all host definitions from hosts.yml
    """
    results = {}
    for region_groups in yaml_content['dn42routers']['children'].values():
        results.update(region_groups['hosts'])
    if include_private:
        results.update(yaml_content['private']['hosts'])
    return results

def is_anycast_host(yaml_content, host):
    return host in yaml_content['anycast_recursors']['hosts'] or \
        host in yaml_content['anycast_auth_dns']['hosts']
