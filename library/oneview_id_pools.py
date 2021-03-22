#!/usr/bin/python
# -*- coding: utf-8 -*-
###
# Copyright (2021) Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###

ANSIBLE_METADATA = {'status': ['stableinterface'],
                    'supported_by': 'community',
                    'metadata_version': '1.1'}

DOCUMENTATION = '''
---
module: oneview_id_pools
short_description: Manage OneView Id Pools.
description:
    - Provides an interface to manage Id pools. Can retrieve, update.
version_added: "2.4"
requirements:
    - "python >= 3.4.2"
    - "hpeOneView >= 5.6.0"
author: "Yuvarani Chidambaram(@yuvirani)"
options:
    state:
        description:
            - Indicates the desired state for the ID Pools resource.
              C(schema) will fetch the schema of the ID Pool
              C(get_pool_type) will get ID pool
              C(update_pool_type_ will enable or disable the pool
              C(allocate) will allocate set of ID's from IPv4 Subnet.
              C(collect) will collect the allocated ID's.
              C(validate) will verify ids are valid or not.
              C(validate_id_pool) will validates the list of ID's from IPv4 Subnet.
              C(generate) will generate random ID's list.
              C(checkrangeavailability) will verify the available range of ID's list.
        choices: ['schema', 'get_pool_type', 'update_pool_type', 'allocate', 'collect',
                  'validate', 'validate_id_pool', 'generate', 'check_range_availability']
    data:
        description:
            - dict with required params.
        required: true
extends_documentation_fragment:
    - oneview
    - oneview.validateetag
'''

EXAMPLES = '''
     - name: Get schema of the id pools
      oneview_id_pools:
        config: "{{ config }}"
        state: schema
        data:
          description: 'ID pool schema'
      delegate_to: localhost

    - name: Generates a random range
      oneview_id_pools:
        config: "{{ config }}"
        state: generate
        data:
          poolType: '{{ poolType }}'
      delegate_to: localhost

    - name: Get the ID Pools type
      oneview_id_pools:
        config: "{{ config }}"
        state: get_pool_type
        data:
          poolType: '{{ poolType }}'
      delegate_to: localhost
    - debug: var=id_pool

    - name: Enables or disables the pool type
      oneview_id_pools:
        config: "{{ config }}"
        state: update_pool_type
        data:
          poolType: '{{ poolType }}'
          rangeUris: '{{ id_pool["rangeUris"] }}'
          enabled: True
      delegate_to: localhost

    - name: Allocates one or more IDs from a pool
      oneview_id_pools:
        config: "{{ config }}"
        state: allocate
        data:
          poolType: '{{ poolType }}'
          count: 2
      delegate_to: localhost

    - name: Checks the range availability in the ID pool
      oneview_id_pools:
        config: "{{ config }}"
        state: check_range_availability
        data:
          poolType: '{{ poolType }}'
          idList: '{{ id_pool["idList"] }}'
      delegate_to: localhost

    - name: Validates the list of ID's from IPv4 Subnet
      oneview_id_pools:
        config: "{{ config }}"
        state: validate_id_pool
        data:
          poolType: 'ipv4'
          idList: ['172.18.9.11']
      delegate_to: localhost

    - name: Validates a set of IDs to reserve in the pool
      oneview_id_pools:
        config: "{{ config }}"
        state: validate
        data:
          poolType: '{{ poolType }}'
          idList: '{{ id_pool["idList"] }}'
      delegate_to: localhost

    - name: Collects one or more IDs to be returned to a pool
      oneview_id_pools:
        config: "{{ config }}"
        state: collect
        data:
          poolType: '{{ poolType }}'
          rangeUris: '{{ id_pool["idList"] }}'
      delegate_to: localhost
'''

RETURN = '''
id_pool:
    description: Has the facts about the Id Pools.
    returned: On all states
    type: dict

'''

from ansible.module_utils.oneview import OneViewModule, OneViewModuleValueError


class IDPoolModule(OneViewModule):
    MSG_UPDATED = 'Pool updated successfully.'
    MSG_ALLOCATED = 'Given set of IDs have been reserved.'
    MSG_VALIDATED = 'Pool IDs are valid'
    MSG_ALREADY_PRESENT = 'Pool Updated already.'
    MSG_IDS_NOT_AVAILABLE = 'This set of IDs already allocated'
    RESOURCE_FACT_NAME = 'id_pools'

    def __init__(self):

        argument_spec = dict(
            state=dict(
                required=True,
                choices=['allocate', 'collect', 'validate', 'generate', 'validate_id_pool',
                         'check_range_availability', 'get_pool_type', 'update_pool_type', 'schema']
            ),
            data=dict(required=True, type='dict'),
        )

        super(IDPoolModule, self).__init__(additional_arg_spec=argument_spec, validate_etag_support=True)

        self.set_resource_object(self.oneview_client.id_pools)

    def execute_module(self):

        changed, msg, id_pool = False, '', {}

        poolType = self.data.pop('poolType', '')
        idList = self.data.pop('idList', [])
        count = self.data.pop('count', 0)

        if self.state == 'schema':
            id_pool = self.resource_client.get_schema()
        elif self.state == 'get_pool_type':
            id_pool = self.resource_client.get_pool_type(poolType).data
        elif self.state == 'update_pool_type':
            changed, msg, id_pool = self.__update_pool_type(poolType)
        elif self.state == 'allocate':
            changed, msg, id_pool = self.__allocate({'count': count}, poolType)
        elif self.state == 'collect':
            id_pool = self.resource_client.collect({'idList': idList}, poolType)
        elif self.state == 'generate':
            id_pool = self.resource_client.generate(poolType).data
        elif self.state == 'validate_id_pool':
            id_pool = self.resource_client.validate_id_pool(poolType, idList).data
        elif self.state == 'validate':
            changed, msg, id_pool = self.__validate({'idList': idList}, poolType)
        else:
            id_pool = self.resource_client.get_check_range_availability(poolType, idList).data

        return dict(changed=changed, msg=msg, ansible_facts=dict(id_pool=id_pool))

    def __update_pool_type(self, poolType):
        updated_pool = self.resource_client.update_pool_type(self.data, poolType)

        if self.data['enabled'] != updated_pool['enabled']:
            return True, self.MSG_UPDATED, updated_pool
        else:
            return False, self.MSG_ALREADY_PRESENT, updated_pool

    def __allocate(self, count, poolType):
        try:
            allocate = self.resource_client.allocate(count, poolType)
            return True, self.MSG_ALLOCATED, allocate
        except OneViewModuleValueError:
            raise OneViewModuleValueError(self.MSG_IDS_NOT_AVAILABLE)

    def __validate(self, idDict, poolType):
        validate = eval(self.resource_client.validate(idDict, poolType))

        if validate['idList'] and validate['valid']:
            return True, self.MSG_VALIDATED, validate
        else:
            return False, self.MSG_IDS_NOT_AVAILABLE, validate


def main():
    IDPoolModule().run()


if __name__ == '__main__':
    main()
