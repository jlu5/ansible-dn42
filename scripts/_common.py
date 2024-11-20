import yaml

class VaultEncryptedDummy():
    pass

_vault_encrypted_dummy = VaultEncryptedDummy()
# Add a stub handler to ignore Ansible specific values like !vault
# See https://github.com/yaml/pyyaml/issues/86
yaml.SafeLoader.add_multi_constructor('!vault', lambda *args: _vault_encrypted_dummy)

def yaml_load(filename):
    with open(filename, encoding='utf-8') as f:
        return yaml.safe_load(f.read())

def get_hosts_group(yaml_group):
    """
    Get a dict of host definitions from the given YAML host group
    """
    results = {}
    if 'hosts' in yaml_group:
        results.update(yaml_group['hosts'])
    if 'children' in yaml_group:
        for group in yaml_group['children'].values():
            results.update(get_hosts_group(group))
    return results

def get_hosts(yaml_content, include_private=False):
    """
    Get a dict of all host definitions from hosts.yml
    """
    results = get_hosts_group(yaml_content['dn42routers'])
    if include_private:
        results |= get_hosts_group(yaml_content['private'])
    return results

def is_anycast_host(yaml_content, host):
    return host in get_hosts_group(yaml_content['anycast_recursors']) \
        | get_hosts_group(yaml_content['anycast_auth_dns'])
