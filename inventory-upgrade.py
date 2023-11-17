#!/usr/bin/env python

import sys, shutil, traceback, yaml, re
from itertools import chain
from pathlib import Path
from datetime import datetime
from collections import Counter
from argparse import ArgumentParser

DEFAULT_INVENTORIES_PATH = Path(sys.path[0]) / "inventories"
INVENTORY_VARS_RELATIVE_PATH = "group_vars/all"
INVENTORY_BACKUP_SUFFIX = ".backup"
INVENTORY_MANAGED_FILES = [
    "group_vars/all/applications.yml",
    "group_vars/all/connectivity.yml",
    "group_vars/all/databases.yml",
    "group_vars/all/docker_images.yml",
    "group_vars/all/docker.yml",
    "group_vars/all/nginx.yml",
    "group_vars/all/offline.yml",
    "group_vars/all/rabbitmq.yml",
    "group_vars/all/tls.yml",
]
INVENTORY_IGNOIRED_FILENAME = [
    "inventory.ini",
    "vault.yml",
]
INVENTORY_NEW_VARIABLES = "group_vars/all/vars.yml"

DEFAULT_VALUES_PATH = Path(sys.path[0]) / "roles/prepare_vars/defaults/main"

VARS_OPTIONALS = [
    "nginx_vhost_override",
]

# TODO: need to check all the deprecated variables with the git history
DEPRECATED_VARS = {20231116: ["swift_.*", "mapbox_token", ".*extract_quantities.*"]}


class MyDumper(yaml.Dumper):
    """configure better indentation and list & stuff like that
    Ref: https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation/39681672#39681672
    """

    def increase_indent(self, flow=False, indentless=False):
        return super(MyDumper, self).increase_indent(flow, False)


def str_presenter(dumper, data):
    """configures yaml for dumping multiline strings
    Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
    """
    if data.count("\n") > 0:  # check for multiline string
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def print_err(*args, **kwargs):
    """Print on stderr"""
    print(*args, file=sys.stderr, **kwargs)


def check_old_inventory(inventory_path):
    """Check the validity of the Ansible inventory inventory_path"""
    if not inventory_path.exists():
        raise FileNotFoundError(
            f"{inventory_path} is not a directory. Please specify the correct inventory name when you call this script."
        )

    elif not inventory_path.is_dir():
        raise NotADirectoryError(
            f"{inventory_path} is not a directory. Please specify the correct inventory name when you call this script."
        )

    inventory_files = inventory_path.rglob("*")
    unknown_files = []
    for file in inventory_files:
        if (
            file.is_file()
            and str(file.relative_to(inventory_path)) not in INVENTORY_MANAGED_FILES
            and file.name not in INVENTORY_IGNOIRED_FILENAME
        ):
            unknown_files.append(str(file))

    if unknown_files:
        raise ValueError(
            "There are unknown files in the inventory, this script can't be safely use to migrate it to the new format.\nUnknown files:\n"
            + "\n".join(["  - " + file for file in unknown_files]),
        )


def backup_old_inventory(inventory_path):
    """Backup inventory_path"""
    if inventory_path.with_suffix(INVENTORY_BACKUP_SUFFIX).exists():
        suffix = (
            INVENTORY_BACKUP_SUFFIX + "-" + str(int(round(datetime.now().timestamp())))
        )
        print(
            f"Warning: {inventory_path.with_suffix(INVENTORY_BACKUP_SUFFIX)} already exists.\n"
            f"The inventory will be backup up into: {inventory_path.with_suffix(suffix)}\n"
        )
    else:
        suffix = INVENTORY_BACKUP_SUFFIX

    shutil.copytree(inventory_path, inventory_path.with_suffix(suffix))


def get_modified_variables(old_vars, new_vars):
    modified_variables = {}

    added_variables = set(new_vars.keys()) - set(old_vars.keys())
    # removed_variables = set(old_vars.keys()) - set(new_vars.keys())

    common_variables = set(old_vars.keys()) & set(new_vars.keys())
    common_changed_variables = {
        key: (old_vars[key], new_vars[key])
        for key in common_variables
        if old_vars[key] != new_vars[key]
    }

    deprecated_vars = list(chain.from_iterable(DEPRECATED_VARS.values()))
    for var_name in sorted(added_variables):
        deprecated = False
        for pattern in deprecated_vars:
            if re.match(pattern, var_name):
                deprecated = True
                print(f"Warning: deprecated variable '{var_name}', ignored.")
        if not deprecated:
            modified_variables[var_name] = new_vars[var_name]

    for var_name in common_changed_variables:
        modified_variables[var_name] = new_vars[var_name]

    return modified_variables


def yaml_load_files(yaml_files):
    """Load YAML file defining the default value of the quickstart variables"""
    yaml_vars = []

    for file in yaml_files:
        # Ignore the vault
        if file.name not in INVENTORY_IGNOIRED_FILENAME:
            with file.open() as f:
                yaml_vars.append(yaml.safe_load(f))

    # Check for duplicate keys accross files
    all_var_names = [key for dictionary in yaml_vars for key in dictionary]
    var_names_counts = Counter(all_var_names)
    duplicate_var_names = {key for key, count in var_names_counts.items() if count > 1}

    if duplicate_var_names:
        raise ValueError(f"Some keys are duplicated: {duplicate_var_names}")

    return {key: value for dictionary in yaml_vars for key, value in dictionary.items()}


def main() -> int:
    args_parser = ArgumentParser()
    args_parser.add_argument("inventory_name")
    args_parser.add_argument("--no-backup", action="store_true", default=False)
    args_parser.add_argument("--inventories-path", default=DEFAULT_INVENTORIES_PATH)
    args = args_parser.parse_args()

    # Configure the style of multiline str dump
    yaml.add_representer(str, str_presenter)

    inventory_path = Path(args.inventories_path) / args.inventory_name

    # Check in we can migrate the inventory
    try:
        check_old_inventory(inventory_path)
    except Exception as e:
        print_err(e)
        return 1

    # Do a backup of the inventory
    if not args.no_backup:
        try:
            backup_old_inventory(inventory_path)
        except Exception as e:
            print_err(
                "Error: something went wrong with the inventory backup. Stopping.\n"
                "Technical details:\n"
            )
            traceback.print_exc()
            return 1

    # Load default variables
    try:
        default_variables = yaml_load_files(DEFAULT_VALUES_PATH.rglob("*"))
    except Exception as e:
        print_err(f"Error: {DEFAULT_VALUES_PATH}: {e}\n" "Technical details:\n")
        traceback.print_exc()
        return 1

    # Load inventory variables
    try:
        vars_path = inventory_path / INVENTORY_VARS_RELATIVE_PATH
        inventory_variables = yaml_load_files(vars_path.rglob("*"))
    except Exception as e:
        print_err(f"Error: {vars_path}: {e}\n" "Technical details:\n")
        traceback.print_exc()
        return 1

    # TODO: More readable file, sort and commented
    # In function of what will be put in  the example file vars.yml in the sample inventory
    new_vars_path = inventory_path / INVENTORY_NEW_VARIABLES
    modified_variables = get_modified_variables(default_variables, inventory_variables)
    with new_vars_path.open(mode="w+") as file:
        yaml.dump(
            modified_variables,
            file,
            indent=2,
            allow_unicode=True,
            default_flow_style=False,
            explicit_start=True,
            sort_keys=True,
            Dumper=MyDumper,
        )


if __name__ == "__main__":
    sys.exit(main())
