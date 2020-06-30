#!/bin/bash

read -r -s -p "Enter string to encrypt: " string
echo -n "$string" | ansible-vault encrypt_string --vault-password-file ~/ansible-dn42.key --stdin-name "${1:-"unnamed"}"
