
# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from heat.engine import signal_responder
from heat.engine import clients
from heat.engine import resource
from heat.engine import scheduler

from heat.common import exception
from heat.openstack.common.gettextutils import _
from heat.openstack.common import log as logging

logger = logging.getLogger(__name__)

class MuranoServiceUnit(resource.Resource):
    # AWS does not require InstanceType but Heat does because the nova
    # create api call requires a flavor
    
    properties_schema = {'InstanceId': {'Type': 'String',
                                        'Required': True}}
    attributes_schema = {
    }
    def __init__(self, name, json_snippet, stack):
        super(MuranoServiceUnit, self).__init__(name, json_snippet, stack)
        self.ipaddress = None
        self.mime_string = None
        
    def _create(self):
        pass

    def handle_create(self):
        pass
    
    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        pass
    
    def metadata_update(self, new_metadata=None):
        pass
    
    def validate(self):
        pass
    
    def handle_delete(self):
        pass
    
    def handle_suspend(self):
        pass
    
    def handle_resume(self):
        pass
    
class MuranoLaunchConfiguration(resource.Resource):
    tags_schema = {'Key': {'Type': 'String',
                           'Required': True},
                   'Value': {'Type': 'String',
                             'Required': True}}
    properties_schema = {
        'ImageId': {'Type': 'String',
                    'Required': True},
        'InstanceType': {'Type': 'String',
                         'Required': True},
        'KeyName': {'Type': 'String'},
        'UserData': {'Type': 'String'},
        'SecurityGroups': {'Type': 'List'},
        'KernelId': {'Type': 'String',
                     'Implemented': False},
        'MuranoServiceId' : {'Type': 'String',
                             'Required': True},
        'RamDiskId': {'Type': 'String',
                      'Implemented': False},
        'BlockDeviceMappings': {'Type': 'String',
                                'Implemented': False},
        'NovaSchedulerHints': {'Type': 'List',
                               'Schema': {'Type': 'Map',
                                          'Schema': tags_schema}},
    }

    
def resource_mapping():
    return {
        'OS::Murano::ServiceUnit': MuranoServiceUnit,
        'OS::Murano::LaunchConfiguration' : MuranoLaunchConfiguration
    }