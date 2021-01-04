import yaml
# Add a stub handler to ignore Ansible specific values like !vault
# See https://github.com/yaml/pyyaml/issues/86
yaml.add_multi_constructor('', lambda *args: None)

def yaml_load(filename):
    with open(filename) as f:
        return yaml.full_load(f.read())
