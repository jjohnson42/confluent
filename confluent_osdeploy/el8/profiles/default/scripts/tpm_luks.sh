#!/bin/sh
cryptdisk=$(blkid -t TYPE="crypto_LUKS"|sed -e s/:.*//)
clevis luks bind -f -d $cryptdisk -k - tpm2 '{}' < /etc/confluent/luks.key
chmod 000 /etc/confluent/luks.key
#cryptsetup luksRemoveKey $cryptdisk < /etc/confluent/confluent.apikey
