for f in *.yml; do
	echo "$f"
	yq '[.wg_peers[] | select( .remove == null ) | select( .name | startswith("dn42") )] | length' "$f"
done
