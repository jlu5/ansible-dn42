#!/bin/bash

cd "${0%/*}" || exit 1

for f in *.yml; do
	echo "$f"
	yq '[.wg_peers[] | select( .remove == null )] | length' "$f"
done
