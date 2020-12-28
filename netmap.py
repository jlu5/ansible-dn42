#!/usr/bin/env python3
"""
Generates a network map (.kml file) for AS42421080.
"""

import argparse
import collections
import time

import geopy
import simplekml
import yaml
# Add a stub handler to ignore Ansible specific values like !vault
# See https://github.com/yaml/pyyaml/issues/86
yaml.add_multi_constructor('', lambda *args: None)

def _yaml_load(filename):
    with open(filename) as f:
        return yaml.full_load(f.read())

class NetmapGeocoder():
    """geopy wrapper that saves geocoding results to disk.
    The underlying backend is lazy-loaded when the API is queried, so an API key is only needed when we queru a new location."""
    def __init__(self, db_filename, api_key):
        self.db_filename = db_filename
        self.api_key = api_key
        try:
            self.entries = _yaml_load(db_filename)
        except FileNotFoundError:
            self.entries = {}

        self._backend = None

    def _init_backend(self):
        if not self.api_key:
            raise ValueError("No API key given for geocoding. Run with --geocode-apikey <key>")
        elif self._backend is None:
            self._backend = geopy.geocoders.GoogleV3(api_key=self.api_key)

    def geocode(self, location, **kwargs):
        if location not in self.entries:
            self._init_backend()
            time.sleep(0.01)  # throttle our API calls slightly
            result = self._backend.geocode(location, **kwargs)
            coords = (result.longitude, result.latitude)
            print(f"Geocode: found coords {coords} for location {location}")
            self.entries[location] = coords
        else:
            print(f"Geocode: using existing coords {self.entries[location]} for location {location}")
        return self.entries[location]

    def save(self):
        with open(self.db_filename, 'w') as f:
            yaml.dump(self.entries, f)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--outfile", help="output path", default="netmap.kml")
    parser.add_argument("-H", "--hosts", help="path to hosts configuration / inventory file",
                        type=str, default='hosts.yml')
    parser.add_argument("-c", "--costs", help="path to internal costs configuration",
                        type=str, default='global-config/internal-costs.yml')
    parser.add_argument("-t", "--tunnels", help="path to IGP tunnels configuration",
                        type=str, default='global-config/igp-tunnels.yml')
    parser.add_argument("-gc", "--geocode-cache", help="cache filename for geocode entries",
                        type=str, default='netmap-geocode.db')
    parser.add_argument("-ga", "--geocode-apikey", help="Google Maps API key for geocoding",
                        type=str, default='')
    parser.add_argument("-dn", "--document-name", help="KML document name",
                        type=str, default="AS4242421080 network map")
    args = parser.parse_args()

    hosts = _yaml_load(args.hosts)
    hosts = hosts['dn42routers']['hosts']
    costs = _yaml_load(args.costs)
    tunnels = _yaml_load(args.tunnels)

    geocoder = NetmapGeocoder(args.geocode_cache, args.geocode_apikey)
    node_coords = {}
    node_short_names = {node: data['shortname'] for node, data in hosts.items()}

    kml = simplekml.Kml(name=args.document_name)

    # Create a new point for each node
    for node, nodedata in hosts.items():
        # Fetch the GPS coordinates for each node. Here I reverse this too because
        # KML expects coordinates in longitude,latitude,altitude form
        # The altitude is just an arbitrary value to make sure the line doesn't get buried by terrain
        raw_coords = geocoder.geocode(nodedata['location'])
        coords = node_coords[node_short_names[node]] = (raw_coords[1], raw_coords[0])

        point = kml.newpoint(name=node_short_names[node], description=nodedata['location'], coords=[coords])
        point.style.iconstyle.icon.href = 'https://maps.google.com/mapfiles/kml/paddle/ylw-blank.png'

    # Create a new line for each IGP tunnel
    graphed_tunnels = set()
    for node, neighbours in tunnels['igp_neighbours'].items():
        if node not in hosts:
            continue
        node = node_short_names[node]
        for neighbour in neighbours:
            neighbour = node_short_names[neighbour]
            if f'{neighbour},{node}' not in graphed_tunnels:  # Only add a connection once
                datapair = f'{node},{neighbour}'
                graphed_tunnels.add(datapair)
                cost = costs['internal_costs'].get(datapair) or \
                       costs['internal_costs'].get(f'{neighbour},{node}') or \
                       costs['default_cost']
                line = kml.newlinestring(
                    name=f'{node} to {neighbour}',
                    description=f'~{cost} ms',
                    coords=[node_coords[node], node_coords[neighbour]]
                )
                line.linestyle.color = "#66111111"  # dark gray at ~40% opacity

    kml.save(args.outfile)
    print(f"Wrote map data to {args.outfile}")
    geocoder.save()
    print(f"Wrote geocode cache to {args.geocode_cache}")

if __name__ == "__main__":
    main()
