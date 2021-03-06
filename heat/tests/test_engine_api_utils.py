# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import uuid

import heat.engine.api as api

from heat.common import template_format
from heat.engine import parser
from heat.engine import parameters
from heat.engine import resource
from heat.engine.event import Event
from heat.common.identifier import EventIdentifier
from heat.rpc import api as rpc_api
from heat.tests.common import HeatTestCase
from heat.tests import generic_resource as generic_rsrc
from heat.tests import utils


class EngineApiTest(HeatTestCase):
    def test_timeout_extract(self):
        p = {'timeout_mins': '5'}
        args = api.extract_args(p)
        self.assertEqual(5, args['timeout_mins'])

    def test_timeout_extract_zero(self):
        p = {'timeout_mins': '0'}
        args = api.extract_args(p)
        self.assertNotIn('timeout_mins', args)

    def test_timeout_extract_garbage(self):
        p = {'timeout_mins': 'wibble'}
        args = api.extract_args(p)
        self.assertNotIn('timeout_mins', args)

    def test_timeout_extract_none(self):
        p = {'timeout_mins': None}
        args = api.extract_args(p)
        self.assertNotIn('timeout_mins', args)

    def test_timeout_extract_not_present(self):
        args = api.extract_args({})
        self.assertNotIn('timeout_mins', args)

    def test_adopt_stack_data_extract_present(self):
        p = {'adopt_stack_data': {'Resources': {}}}
        args = api.extract_args(p)
        self.assertTrue(args.get('adopt_stack_data'))

    def test_adopt_stack_data_extract_not_present(self):
        args = api.extract_args({})
        self.assertNotIn('adopt_stack_data', args)

    def test_disable_rollback_extract_true(self):
        args = api.extract_args({'disable_rollback': True})
        self.assertIn('disable_rollback', args)
        self.assertTrue(args.get('disable_rollback'))

        args = api.extract_args({'disable_rollback': 'True'})
        self.assertIn('disable_rollback', args)
        self.assertTrue(args.get('disable_rollback'))

        args = api.extract_args({'disable_rollback': 'true'})
        self.assertIn('disable_rollback', args)
        self.assertTrue(args.get('disable_rollback'))

    def test_disable_rollback_extract_false(self):
        args = api.extract_args({'disable_rollback': False})
        self.assertIn('disable_rollback', args)
        self.assertFalse(args.get('disable_rollback'))

        args = api.extract_args({'disable_rollback': 'False'})
        self.assertIn('disable_rollback', args)
        self.assertFalse(args.get('disable_rollback'))

        args = api.extract_args({'disable_rollback': 'false'})
        self.assertIn('disable_rollback', args)
        self.assertFalse(args.get('disable_rollback'))

    def test_disable_rollback_extract_bad(self):
        self.assertRaises(ValueError, api.extract_args,
                          {'disable_rollback': 'bad'})


class FormatTest(HeatTestCase):
    def setUp(self):
        super(FormatTest, self).setUp()
        utils.setup_dummy_db()

        template = parser.Template({
            'Resources': {
                'generic1': {'Type': 'GenericResourceType'},
                'generic2': {
                    'Type': 'GenericResourceType',
                    'DependsOn': 'generic1'}
            }
        })
        resource._register_class('GenericResourceType',
                                 generic_rsrc.GenericResource)
        self.stack = parser.Stack(utils.dummy_context(), 'test_stack',
                                  template, stack_id=str(uuid.uuid4()))

    def _dummy_event(self, event_id):
        resource = self.stack['generic1']
        return Event(utils.dummy_context(), self.stack, 'CREATE', 'COMPLETE',
                     'state changed', 'z3455xyc-9f88-404d-a85b-5315293e67de',
                     resource.properties, resource.name, resource.type(),
                     id=event_id)

    def test_format_stack_resource(self):
        res = self.stack['generic1']

        resource_keys = set((
            rpc_api.RES_UPDATED_TIME,
            rpc_api.RES_NAME,
            rpc_api.RES_PHYSICAL_ID,
            rpc_api.RES_METADATA,
            rpc_api.RES_ACTION,
            rpc_api.RES_STATUS,
            rpc_api.RES_STATUS_DATA,
            rpc_api.RES_TYPE,
            rpc_api.RES_ID,
            rpc_api.RES_STACK_ID,
            rpc_api.RES_STACK_NAME,
            rpc_api.RES_REQUIRED_BY))

        resource_details_keys = resource_keys.union(set(
            (rpc_api.RES_DESCRIPTION, rpc_api.RES_METADATA)))

        formatted = api.format_stack_resource(res, True)
        self.assertEqual(resource_details_keys, set(formatted.keys()))

        formatted = api.format_stack_resource(res, False)
        self.assertEqual(resource_keys, set(formatted.keys()))

    def test_format_stack_resource_required_by(self):
        res1 = api.format_stack_resource(self.stack['generic1'])
        res2 = api.format_stack_resource(self.stack['generic2'])
        self.assertEqual(['generic2'], res1['required_by'])
        self.assertEqual([], res2['required_by'])

    def test_format_event_id_integer(self):
        self._test_format_event('42')

    def test_format_event_id_uuid(self):
        self._test_format_event('a3455d8c-9f88-404d-a85b-5315293e67de')

    def _test_format_event(self, event_id):
        event = self._dummy_event(event_id)

        event_keys = set((
            rpc_api.EVENT_ID,
            rpc_api.EVENT_STACK_ID,
            rpc_api.EVENT_STACK_NAME,
            rpc_api.EVENT_TIMESTAMP,
            rpc_api.EVENT_RES_NAME,
            rpc_api.EVENT_RES_PHYSICAL_ID,
            rpc_api.EVENT_RES_ACTION,
            rpc_api.EVENT_RES_STATUS,
            rpc_api.EVENT_RES_STATUS_DATA,
            rpc_api.EVENT_RES_TYPE,
            rpc_api.EVENT_RES_PROPERTIES))

        formatted = api.format_event(event)
        self.assertEqual(event_keys, set(formatted.keys()))

        event_id_formatted = formatted[rpc_api.EVENT_ID]
        event_identifier = EventIdentifier(event_id_formatted['tenant'],
                                           event_id_formatted['stack_name'],
                                           event_id_formatted['stack_id'],
                                           event_id_formatted['path'])
        self.assertEqual(event_id, event_identifier.event_id)


class FormatValidateParameterTest(HeatTestCase):

    base_template = '''
    {
        "AWSTemplateFormatVersion" : "2010-09-09",
        "Description" : "test",
        "Parameters" : {
            %s
        }
    }
    '''

    base_template_hot = '''
    {
        "heat_template_version" : "2013-05-23",
        "description" : "test",
        "parameters" : {
            %s
        }
    }
    '''

    scenarios = [
        ('simple',
         dict(template=base_template,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "Type": "String",
                        "Description": "Name of SSH key pair"
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'NoEcho': 'false'
              })
         ),
        ('default',
         dict(template=base_template,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "Type": "String",
                        "Description": "Name of SSH key pair",
                        "Default": "dummy"
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'Default': 'dummy',
                  'NoEcho': 'false'
              })
         ),
        ('min_length_constraint',
         dict(template=base_template,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "Type": "String",
                        "Description": "Name of SSH key pair",
                        "MinLength": 4
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'MinLength': 4,
                  'NoEcho': 'false'
              })
         ),
        ('max_length_constraint',
         dict(template=base_template,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "Type": "String",
                        "Description": "Name of SSH key pair",
                        "MaxLength": 10
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'MaxLength': 10,
                  'NoEcho': 'false'
              })
         ),
        ('min_max_length_constraint',
         dict(template=base_template,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "Type": "String",
                        "Description": "Name of SSH key pair",
                        "MinLength": 4,
                        "MaxLength": 10
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'MinLength': 4,
                  'MaxLength': 10,
                  'NoEcho': 'false'
              })
         ),
        ('min_value_constraint',
         dict(template=base_template,
              param_name='MyNumber',
              param='''
                    "MyNumber": {
                        "Type": "Number",
                        "Description": "A number",
                        "MinValue": 4
                    }
                    ''',
              expected={
                  'Type': 'Number',
                  'Description': 'A number',
                  'MinValue': 4,
                  'NoEcho': 'false'
              })
         ),
        ('max_value_constraint',
         dict(template=base_template,
              param_name='MyNumber',
              param='''
                    "MyNumber": {
                        "Type": "Number",
                        "Description": "A number",
                        "MaxValue": 10
                    }
                    ''',
              expected={
                  'Type': 'Number',
                  'Description': 'A number',
                  'MaxValue': 10,
                  'NoEcho': 'false'
              })
         ),
        ('min_max_value_constraint',
         dict(template=base_template,
              param_name='MyNumber',
              param='''
                    "MyNumber": {
                        "Type": "Number",
                        "Description": "A number",
                        "MinValue": 4,
                        "MaxValue": 10
                    }
                    ''',
              expected={
                  'Type': 'Number',
                  'Description': 'A number',
                  'MinValue': 4,
                  'MaxValue': 10,
                  'NoEcho': 'false'
              })
         ),
        ('allowed_values_constraint',
         dict(template=base_template,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "Type": "String",
                        "Description": "Name of SSH key pair",
                        "AllowedValues": [ "foo", "bar", "blub" ]
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'AllowedValues': ['foo', 'bar', 'blub'],
                  'NoEcho': 'false'
              })
         ),
        ('allowed_pattern_constraint',
         dict(template=base_template,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "Type": "String",
                        "Description": "Name of SSH key pair",
                        "AllowedPattern": "[a-zA-Z0-9]+"
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'AllowedPattern': "[a-zA-Z0-9]+",
                  'NoEcho': 'false'
              })
         ),
        ('multiple_constraints',
         dict(template=base_template,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "Type": "String",
                        "Description": "Name of SSH key pair",
                        "MinLength": 4,
                        "MaxLength": 10,
                        "AllowedValues": [
                            "foo", "bar", "blub"
                        ],
                        "AllowedPattern": "[a-zA-Z0-9]+"
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'MinLength': 4,
                  'MaxLength': 10,
                  'AllowedValues': ['foo', 'bar', 'blub'],
                  'AllowedPattern': "[a-zA-Z0-9]+",
                  'NoEcho': 'false'
              })
         ),
        ('simple_hot',
         dict(template=base_template_hot,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "type": "string",
                        "description": "Name of SSH key pair"
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'NoEcho': 'false'
              })
         ),
        ('default_hot',
         dict(template=base_template_hot,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "type": "string",
                        "description": "Name of SSH key pair",
                        "default": "dummy"
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'Default': 'dummy',
                  'NoEcho': 'false'
              })
         ),
        ('min_length_constraint_hot',
         dict(template=base_template_hot,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "type": "string",
                        "description": "Name of SSH key pair",
                        "constraints": [
                            { "length": { "min": 4} }
                        ]
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'MinLength': 4,
                  'NoEcho': 'false'
              })
         ),
        ('max_length_constraint_hot',
         dict(template=base_template_hot,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "type": "string",
                        "description": "Name of SSH key pair",
                        "constraints": [
                            { "length": { "max": 10} }
                        ]
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'MaxLength': 10,
                  'NoEcho': 'false'
              })
         ),
        ('min_max_length_constraint_hot',
         dict(template=base_template_hot,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "type": "string",
                        "description": "Name of SSH key pair",
                        "constraints": [
                            { "length": { "min":4, "max": 10} }
                        ]
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'MinLength': 4,
                  'MaxLength': 10,
                  'NoEcho': 'false'
              })
         ),
        ('min_value_constraint_hot',
         dict(template=base_template_hot,
              param_name='MyNumber',
              param='''
                    "MyNumber": {
                        "type": "number",
                        "description": "A number",
                        "constraints": [
                            { "range": { "min": 4} }
                        ]
                    }
                    ''',
              expected={
                  'Type': 'Number',
                  'Description': 'A number',
                  'MinValue': 4,
                  'NoEcho': 'false'
              })
         ),
        ('max_value_constraint_hot',
         dict(template=base_template_hot,
              param_name='MyNumber',
              param='''
                    "MyNumber": {
                        "type": "number",
                        "description": "A number",
                        "constraints": [
                            { "range": { "max": 10} }
                        ]
                    }
                    ''',
              expected={
                  'Type': 'Number',
                  'Description': 'A number',
                  'MaxValue': 10,
                  'NoEcho': 'false'
              })
         ),
        ('min_max_value_constraint_hot',
         dict(template=base_template_hot,
              param_name='MyNumber',
              param='''
                    "MyNumber": {
                        "type": "number",
                        "description": "A number",
                        "constraints": [
                            { "range": { "min": 4, "max": 10} }
                        ]
                    }
                    ''',
              expected={
                  'Type': 'Number',
                  'Description': 'A number',
                  'MinValue': 4,
                  'MaxValue': 10,
                  'NoEcho': 'false'
              })
         ),
        ('allowed_values_constraint_hot',
         dict(template=base_template_hot,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "type": "string",
                        "description": "Name of SSH key pair",
                        "constraints": [
                            { "allowed_values": [
                                "foo", "bar", "blub"
                              ]
                            }
                        ]
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'AllowedValues': ['foo', 'bar', 'blub'],
                  'NoEcho': 'false'
              })
         ),
        ('allowed_pattern_constraint_hot',
         dict(template=base_template_hot,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "type": "string",
                        "description": "Name of SSH key pair",
                        "constraints": [
                            { "allowed_pattern": "[a-zA-Z0-9]+" }
                        ]
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'AllowedPattern': "[a-zA-Z0-9]+",
                  'NoEcho': 'false'
              })
         ),
        ('multiple_constraints_hot',
         dict(template=base_template_hot,
              param_name='KeyName',
              param='''
                    "KeyName": {
                        "type": "string",
                        "description": "Name of SSH key pair",
                        "constraints": [
                            { "length": { "min": 4, "max": 10} },
                            { "allowed_values": [
                                "foo", "bar", "blub"
                              ]
                            },
                            { "allowed_pattern": "[a-zA-Z0-9]+" }
                        ]
                    }
                    ''',
              expected={
                  'Type': 'String',
                  'Description': 'Name of SSH key pair',
                  'MinLength': 4,
                  'MaxLength': 10,
                  'AllowedValues': ['foo', 'bar', 'blub'],
                  'AllowedPattern': "[a-zA-Z0-9]+",
                  'NoEcho': 'false'
              })
         ),
    ]

    def test_format_validate_parameter(self):
        """
        Test format of a parameter.
        """

        t = template_format.parse(self.template % self.param)
        tmpl = parser.Template(t)

        tmpl_params = parameters.Parameters(None, tmpl, validate_value=False)
        param = tmpl_params.params[self.param_name]
        param_formated = api.format_validate_parameter(param)
        self.assertEqual(self.expected, param_formated)
