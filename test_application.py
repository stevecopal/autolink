#!/usr/bin/env python
"""
Root test runner for AutoLink.

Usage:
    python test_application.py

This module configures Django with the project settings and runs the
existing project tests collected from the installed apps.
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autolink.settings')

import django
django.setup(set_prefix=False)

from django.test.runner import DiscoverRunner


def main():
    try:
        runner = DiscoverRunner(verbosity=2, failfast=False)
        failures = runner.run_tests(['test_application'])
        sys.exit(bool(failures))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
