#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Import stock packages
import sys

# Import opinel
try:
    from opinel.utils import check_opinel_version, configPrintException, get_opinel_requirement, read_creds
except Exception as e:
    print('Error: Scout2 now depends on the opinel package (previously AWSUtils submodule). Install all the requirements with the following command:')
    print('  $ pip install -r requirements.txt')
    print(e)
    sys.exit(42)

# Import Scout2 tools
from AWSScout2.rules.exceptions import process_exceptions
from AWSScout2.rules.ruleset import Ruleset
from AWSScout2.configs.scout2 import  Scout2Config
from AWSScout2.configs.services import postprocessing
from AWSScout2.rules.postprocessing import do_postprocessing
from AWSScout2.cli_parser import Scout2ArgumentParser
from AWSScout2.report.fs import Scout2Report


########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = Scout2ArgumentParser()
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    min_opinel, max_opinel = get_opinel_requirement()
    if not check_opinel_version(min_opinel):
        return 42

    # Set the profile name
    profile_name = args.profile[0]

    # Search for AWS credentials
    if not args.fetch_local:
        credentials = read_creds(args.profile[0], args.csv_credentials, args.mfa_serial, args.mfa_code)
        if credentials['AccessKeyId'] is None:
            return 42

    # Create a new Scout2 config
    report = Scout2Report(profile_name, args.report_dir, args.timestamp)
    aws_config = Scout2Config(args.services, args.skipped_services)

    # Fetch data from AWS APIs if not running a local analysis
    if not args.fetch_local:
        aws_config.fetch(credentials, regions=args.regions, partition_name=args.partition_name)
        aws_config.update_metadata()
        report.save(aws_config, {}, args.force_write, args.debug)

    # Reload to flatten everything into a python dictionary
    aws_config = report.load()

    # Analyze config
    ruleset = Ruleset(profile_name)
    ruleset.analyze(aws_config)

    # Create display filters
    filters = Ruleset(ruleset_filename = 'rulesets/filters.json', rule_type = 'filters')
    filters.analyze(aws_config)

    # Finalize
    postprocessing(aws_config)
    do_postprocessing(aws_config)

    # Handle exceptions
    process_exceptions(aws_config, args.exceptions[0])

    # Save config and create HTML report
    report.save(aws_config, {}, args.force_write, args.debug)