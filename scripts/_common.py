import pprint
import yaml
# Add a stub handler to ignore Ansible specific values like !vault
# See https://github.com/yaml/pyyaml/issues/86
yaml.add_multi_constructor('', lambda *args: None)

def yaml_load(filename):
    with open(filename) as f:
        return yaml.full_load(f.read())

def get_hosts(yaml_content):
    """
    Get a list of all host definitions from hosts.yml
    """
    results = {}
    for region_groups in yaml_content['dn42routers']['children'].values():
        results.update(region_groups['hosts'])
    return results
