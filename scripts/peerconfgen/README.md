# peerconfgen - dn42 peering generator for WireGuard and BIRD

![Video Demonstration](../../web/peerconfgen-demo.mp4)

## Usage

To run this script you need the `requests` and `ruamel.yaml` libraries (`pip install requests ruamel.yaml`)

### Adding/updating peerings

For example, if you were AS4242421080 and wanted to peer with my "sjc" node, you would run something like: `peerconfgen.py sjc highdef` and interactively fill in the prompts.

For peer name section, **you should only include your AS name**, and not any router names specific to your network (e.g. rtr1). Please only use names containing lowercase letters or numbers.

```
$ peerconfgen.py --help
usage: peerconfgen.py [-h] [--dry-run] [--replace] node peername

Interactively generate peering configs (WireGuard+BIRD) by scraping plain text
node info and autofilling as many fields as possible.

positional arguments:
  node           Node to generate config for
  peername       Short name / identifier for peer

options:
  -h, --help     show this help message and exit
  --dry-run, -n  Only print generated output; do not write it to disk
  --replace, -r  Overwrite existing config blocks
```

The `--replace` option allows you to overwrite existing configurations - otherwise doing so is an error.

### Removing peerings

```
usage: peerconfrm.py [-h] node peername

Script to automate removing old peerings.

positional arguments:
  node        Node to generate config for
  peername    Short name / identifier for peer

options:
  -h, --help  show this help message and exit
```

Note that this leaves behind stubs in the WireGuard configuration YAML so that old interfaces get cleaned up properly. (Ansible is generally imperative and not declarative)
