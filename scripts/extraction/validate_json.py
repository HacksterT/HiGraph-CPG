"""
Generic JSON Schema Validator

Validates extracted data against JSON schemas and entity-specific business rules.
Works with any extraction template that exposes get_schema() and validate().
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from jsonschema import validate as jsonschema_validate, ValidationError


def validate_against_schema(data: Any, schema: dict) -> Tuple[bool, List[str]]:
    """
    Validate data against a JSON schema.

    Args:
        data: Data to validate (single item or list)
        schema: JSON schema dict

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    items = data if isinstance(data, list) else [data]
    for i, item in enumerate(items):
        try:
            jsonschema_validate(instance=item, schema=schema)
        except ValidationError as e:
            errors.append(f"Item {i}: {e.message}")

    return len(errors) == 0, errors


def validate_with_template(data: List[dict], template_module) -> Dict[str, Any]:
    """
    Validate extracted data using a template module's validate() function.

    Args:
        data: List of extracted items
        template_module: Module with get_schema() and validate() functions

    Returns:
        Validation report dict
    """
    schema = template_module.get_schema()
    report = {
        'total_items': len(data),
        'valid': 0,
        'invalid': 0,
        'errors': [],
    }

    for i, item in enumerate(data):
        # Schema validation
        schema_valid, schema_errors = validate_against_schema(item, schema)

        # Business rule validation
        biz_valid, biz_errors = template_module.validate(item)

        all_errors = schema_errors + biz_errors

        if all_errors:
            report['invalid'] += 1
            report['errors'].append({
                'index': i,
                'item_id': item.get('rec_number') or item.get('kq_number') or item.get('ref_number') or i,
                'errors': all_errors,
            })
        else:
            report['valid'] += 1

    report['validation_rate'] = report['valid'] / report['total_items'] if report['total_items'] > 0 else 0
    return report


def validate_file(json_path: str, template_module) -> Dict[str, Any]:
    """
    Validate a JSON file of extracted entities.

    Args:
        json_path: Path to the JSON file
        template_module: Template module to use for validation

    Returns:
        Validation report
    """
    with open(json_path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        return {
            'total_items': 0,
            'valid': 0,
            'invalid': 0,
            'errors': [{'index': 0, 'errors': ['Expected a JSON array']}],
            'validation_rate': 0,
        }

    return validate_with_template(data, template_module)


def print_report(report: Dict[str, Any], entity_type: str = "items"):
    """Print a formatted validation report."""
    print(f"\nValidation Report: {entity_type}")
    print("=" * 50)
    print(f"Total: {report['total_items']}")
    print(f"Valid: {report['valid']}")
    print(f"Invalid: {report['invalid']}")
    print(f"Validation rate: {report['validation_rate']:.1%}")

    if report['errors']:
        print(f"\nErrors ({len(report['errors'])} items):")
        for err in report['errors'][:10]:  # Show first 10
            print(f"  Item {err['item_id']}:")
            for e in err['errors']:
                print(f"    - {e}")
        if len(report['errors']) > 10:
            print(f"  ... and {len(report['errors']) - 10} more")


__all__ = [
    'validate_against_schema',
    'validate_with_template',
    'validate_file',
    'print_report',
]
