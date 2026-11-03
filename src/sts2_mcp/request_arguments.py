"""Normalize public arguments before acquiring a session or sending a request."""
from dataclasses import dataclass
from copy import deepcopy
import re

from sts2_mcp.tool_registry import binding
from sts2_mcp.output.null_fields import apply_preset


def validate_schema(value, schema, field='arguments'):
    kinds = schema.get('type', [])
    if isinstance(kinds, str): kinds = [kinds]
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool, 'null': type(None)}
    if kinds and not any(type(value) is types[kind] for kind in kinds):
        raise ValueError(f'{field} must be {" or ".join(kinds)}.')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{field} must be one of: {", ".join(map(str, schema["enum"]))}.')
    if isinstance(value, dict):
        properties = schema.get('properties', {})
        extra = value.keys() - properties.keys()
        if extra and schema.get('additionalProperties') is False:
            raise ValueError(f'{", ".join(sorted(extra))} is not accepted; allowed fields: {", ".join(properties) or "none"}.')
        for key in schema.get('required', []):
            if key not in value: raise ValueError(f'{key} is required.')
        for key, item in value.items():
            if key in properties: validate_schema(item, properties[key], key)
        for key, required in schema.get('dependentRequired', {}).items():
            if key in value and any(name not in value for name in required):
                raise ValueError(f'{key} requires {", ".join(required)}.')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_schema(item, schema['items'], f'{field}[{index}]')
    elif type(value) is int:
        if 'minimum' in schema and value < schema['minimum'] or 'maximum' in schema and value > schema['maximum']:
            raise ValueError(f'{field} must be an integer from {schema.get("minimum", "unbounded")} to {schema.get("maximum", "unbounded")}.')
    elif isinstance(value, str):
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            raise ValueError(f'{field} must match {schema["pattern"]}.')
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', float('inf')):
            raise ValueError(f'{field} length must be from {schema.get("minLength", 0)} to {schema.get("maxLength", "unbounded")}.')

    alternatives = schema.get('oneOf') or schema.get('anyOf')
    if alternatives:
        matches = 0
        for branch in alternatives:
            try:
                validate_schema(value, branch, field)
                matches += 1
            except ValueError:
                pass
        if not matches or 'oneOf' in schema and matches != 1:
            if schema.get('type') == 'object':
                choices = ', '.join('/'.join(branch.get('required', [])) for branch in alternatives)
                raise ValueError(f'{field} requires exactly one of: {choices}.')
            raise ValueError(f'{field} must match one allowed type/value: {alternatives}.')


@dataclass(frozen=True)
class NormalizedRequest:
    spec: object
    preset: str | None
    native_arguments: dict | None
    output_arguments: dict
    effect: str
    media_required: bool

    @property
    def operation(self): return self.spec.native_operation
    @property
    def requires_permission(self): return self.spec.requires_permission
    @property
    def returns_transition(self): return self.spec.returns_transition
    @property
    def refreshes_permission(self): return self.spec.refreshes_permission

    def project(self, payload):
        if self.spec.projector:
            payload = binding(self.spec.projector)(payload, **self.output_arguments)
        compact = self.preset == 'summary' and self.spec.category != 'observation'
        return apply_preset(payload, 'default' if compact else self.preset)


def normalize_request(spec, arguments):
    arguments = {} if arguments is None else deepcopy(arguments)
    validate_schema(arguments, spec.input_schema)
    preset = arguments.get('preset', 'default') if spec.presets else None
    normalized = dict(arguments)
    if spec.presets:
        normalized.pop('preset', None)
        if 'preset' in spec.schema['properties']:
            normalized['preset'] = 'full' if preset == 'default' else preset
    if spec.parser:
        parse = binding(spec.parser)
        normalized = parse(spec.native_operation, normalized) if spec.parser_operation else parse(normalized)
    if spec.native_keys is not None:
        native = {key: normalized[key] for key in spec.native_keys if key in normalized} or None
        output = {key: value for key, value in normalized.items() if key not in spec.native_keys}
    elif spec.projector:
        native = dict(normalized)
        output = {'preset': native.pop('preset', 'full')}
    else:
        native, output = (normalized if spec.parser else normalized or None), {}
    if spec.projector and 'preset' in normalized:
        output['preset'] = normalized['preset']
    if native is not None:
        for source, target in spec.native_renames:
            native[target] = native.pop(source)
    effect = spec.effect_for(native)
    media = spec.media and preset not in {'actions_only', 'top_bar'}
    return NormalizedRequest(spec, preset, native, output, effect, media)
