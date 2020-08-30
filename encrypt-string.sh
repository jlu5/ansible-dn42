#!/bin/bash

read -r -s -p "Enter string to encrypt: " string
echo -n "$string" | ansible-vault encrypt_string --stdin-name "${1:-"unnamed"}"
