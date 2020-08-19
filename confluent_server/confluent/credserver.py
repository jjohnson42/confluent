# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2019 Lenovo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import confluent.config.configmanager as cfm
import confluent.netutil as netutil
import confluent.util as util
import datetime
import eventlet
import eventlet.green.socket as socket
import eventlet.greenpool
import os

class CredServer(object):
    def __init__(self):
        self.cfm = cfm.ConfigManager(None)

    def handle_client(self, client, peer):
        try:
            if not netutil.address_is_local(peer[0]):
                client.close()
                return
            client.send(b'\xc2\xd1-\xa8\x80\xd8j\xba')
            tlv = bytearray(client.recv(2))
            if tlv[0] != 1:
                client.close()
                return
            nodename = util.stringify(client.recv(tlv[1]))
            tlv = bytearray(client.recv(2))
            apiarmed = self.cfm.get_node_attributes(nodename, 'deployment.apiarmed')
            apiarmed = apiarmed.get(nodename, {}).get('deployment.apiarmed', {}).get(
                'value', None)
            if not apiarmed:
                client.close()
                return
            if apiarmed not in ('once', 'continuous'):
                now = datetime.datetime.utcnow()
                expiry = datetime.datetime.strptime(apiarmed, "%Y-%m-%dT%H:%M:%SZ")
                if now > expiry:
                    self.cfm.set_node_attributes({nodename: {'deployment.apiarmed': ''}})
                    client.close()
                    return
            client.send(b'\x02\x20')
            rttoken = os.urandom(32)
            client.send(rttoken)
            client.send(b'\x00\x00')
            tlv = bytearray(client.recv(2))
            if tlv[0] != 3:
                client.close()
                return
            echotoken = client.recv(tlv[1])
            if echotoken != rttoken:
                client.close()
                return
            tlv = bytearray(client.recv(2))
            if tlv[0] != 4:
                client.close()
                return
            echotoken = util.stringify(client.recv(tlv[1]))
            cfgupdate = {nodename: {'crypted.selfapikey': {'hashvalue': echotoken}, 'deployment.apiarmed': ''}}
            if apiarmed == 'continuous':
                del cfgupdate[nodename]['deployment.apiarmed']
            self.cfm.set_node_attributes(cfgupdate)
            client.recv(2)  # drain end of message
            client.send(b'\x05\x00') # report success
        finally:
            client.close()

if __name__ == '__main__':
    a = CredServer()
    while True:
        eventlet.sleep(86400)
