#!/usr/bin/env python

import sys, shutil, yaml, re
from pathlib import Path
from datetime import datetime
from collections import Counter
from argparse import ArgumentParser
from jinja2 import Template

DEFAULT_INVENTORIES_PATH = Path(sys.path[0]) / "inventories"
INVENTORY_VARS_RELATIVE_PATH = "group_vars/all"
INVENTORY_OLD_MANAGED_FILES = [
    "applications.yml",
    "connectivity.yml",
    "databases.yml",
    "docker_images.yml",
    "docker.yml",
    "nginx.yml",
    "offline.yml",
    "rabbitmq.yml",
    "tls.yml",
]
REFERENCE_VALUES_PATH = Path(sys.path[0]) / "roles/prepare_vars/defaults/main"

TEMPLATED_VARS = [
    "app_dns_domain",
    "docker_private_registry_login",
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_pass",
    "smtp_use_tls",
    "smtp_default_email",
    "debug_mail_to",
]

VARS_TEMPLATE_DEFINITION = """---
# DNS Domain
app_dns_domain: {{ app_dns_domain }}

# smtp service
smtp_host: "{{ smtp_host if smtp_host }}"
smtp_port: {{ smtp_port }}
smtp_user: "{{ smtp_user if smtp_user }}"
smtp_pass: "{{ smtp_pass if smtp_pass }}"
smtp_use_tls: {{ smtp_use_tls | lower }}
smtp_default_email: "{{ smtp_default_email if smtp_default_email }}"
debug_mail_to: "{{ debug_mail_to if debug_mail_to }}"

{%- if docker_private_registry_login is defined and docker_private_registry_login | length %}

# Docker registry
docker_private_registry_login: {{ docker_private_registry_login }}

{% endif -%}

# Add your other configurations after this comment
"""

DEPRECATED_VARS = {
    20221118: [".*extract_quantities.*"],
    20220928: ["mapbox_token"],
    20230309: ["swift_.*"],
    20240905: ["bimdata_venv_path"],
}


class Inventory:
    def __init__(self, path):
        self.path = Path(path)
        self.inventory_file_path = self.path / "inventory.ini"
        self.vars_path = self.path / INVENTORY_VARS_RELATIVE_PATH / "vars.yml"
        self.vault_path = self.path / INVENTORY_VARS_RELATIVE_PATH / "vault.yml"

        # Check that the inventory folder exists
        if not self.path.exists():
            raise FileNotFoundError(
                f"{self.path} not found. Please specify the correct inventory name when you call this script."
            )
        elif not self.path.is_dir():
            raise NotADirectoryError(
                f"{self.path} is not a directory. Please specify the correct inventory name when you call this script."
            )

        # Set legacy vars if vars.yml doesn't exist yet
        self.legacy_vars_paths = []
        if self.vars_path.exists():
            self.is_legacy = False
        else:
            self.is_legacy = True
            for file in INVENTORY_OLD_MANAGED_FILES:
                file_path = self.path / INVENTORY_VARS_RELATIVE_PATH / file
                if file_path.exists():
                    self.legacy_vars_paths.append(file_path)
                else:
                    print(f"Warning: Legacy inventory, but missing file {file_path}.")

        # Retrieve content
        self.content = self.read_inventory()

    def get_unknown_files(self):
        """Returns a list of files that are not managed by this class"""
        unknown_files = []
        existing_files = self.path.rglob("*")
        for file in existing_files:
            if (
                file.is_file()
                and file != self.inventory_file_path
                and file != self.vars_path
                and file != self.vault_path
                and file not in self.legacy_vars_paths
            ):
                unknown_files.append(file)
        return unknown_files

    def read_inventory(self):
        """Reads the inventory files and returns a dictionary containing the content of the inventory"""
        files = self.legacy_vars_paths if self.is_legacy else [self.vars_path]
        # In some previous versions, not all files exists.
        files = [file for file in files if file.exists()]
        return yaml_load_files(files)

    def migrate_legacy(self, ref_values={}):
        """
        Migrates the data by removing variables that have values matching those specified in ref_values.

        Parameters:
        - ref_values (dict): A dictionary containing reference values. Variables with values matching
        those in this dictionary will be removed during the migration process.
        """

        # Remove variables that have a value matching those in ref_values
        for key, value in ref_values.items():
            if (
                key not in TEMPLATED_VARS
                and key in self.content
                and self.content[key] == value
            ):
                del self.content[key]

        # If docker_bimdata_tag is defined, but look like our default tag
        # Remove it, next time the upgrade will be automatic
        if "docker_bimdata_tag" in self.content and is_valid_date(
            self.content["docker_bimdata_tag"]
        ):
            del self.content["docker_bimdata_tag"]

        self.is_legacy = False

    def upgrade(self, ref_values={}, version=None):
        if self.is_legacy:
            self.migrate_legacy(ref_values)

        if version:
            self.content["bimdata_version"] = version
        elif "bimdata_version" in self.content:
            version = self.content["bimdata_version"]
        else:
            version = ref_values.get("bimdata_version")

        # Remove variables that are deprecated
        for version_depreciation in DEPRECATED_VARS.keys():
            if version >= version_depreciation:
                for pattern in DEPRECATED_VARS[version_depreciation]:
                    for key in list(self.content.keys()):
                        if re.match(pattern, key):
                            del self.content[key]
                            print(f"Warning: deprecated variable '{key}', removed.")

        # Upgrade docker_registries syntax to simplify mandatory vars.yml content when possible
        if (
            "docker_registries" in self.content
            and "docker_private_registry_login" not in self.content
            and len(self.content["docker_registries"]) == 1
        ):
            current_registry = self.content["docker_registries"][0]
            ref_registry = ref_values["docker_registries"][0]
            if (
                current_registry["url"] == ref_registry["url"]
                and current_registry["password"] == ref_registry["password"]
            ):
                self.content["docker_private_registry_login"] = current_registry[
                    "username"
                ]
                del self.content["docker_registries"]

    def use_custom_tag(self):
        """Returns True if the inventory contains custom images / tags"""

        ignored_images = [
            "docker_rabbitmq.*",
            "docker_postgres.*",
            "docker_nginx.*",
            "docker_acme_companion.*",
            "docker_bimdata_tag",
        ]
        # If one the tag doesn't use docker_bimdata_tag as ref value, custom tag are use
        for key in self.content:
            if re.match("docker_.*_tag", key):
                if (
                    not match_any_regex(key, ignored_images)
                    and self.content[key] != "{{ docker_bimdata_tag }}"
                ):
                    return True
        # if the version is defined (new inventory)
        # and if docker_bimdata_tag doesn't use bimdata_version as ref value
        if (
            "docker_bimdata_tag" in self.content
            and self.content["docker_bimdata_tag"] != "{{ bimdata_version }}"
        ):
            return True
        return False

    def backup(self, backup_suffix):
        """Backup the inventory"""
        backup_path = self.path.with_suffix(backup_suffix)
        if backup_path.exists():
            suffix = backup_suffix + "-" + str(int(round(datetime.now().timestamp())))
            backup_path = self.path.with_suffix(suffix)
            print(
                f"Warning: {self.path.with_suffix(backup_suffix)} already exists.\n"
                f"The inventory will be backup up into: {backup_path}"
            )
        shutil.copytree(self.path, backup_path)

    def write_inventory(self, backup=True, backup_suffix=".backup", delete_legacy=True):
        if self.is_legacy:
            raise ValueError(
                "This script can't write legacy inventory. Please upgrade it first."
            )
        if backup:
            self.backup(backup_suffix)

        # Segregate the mandatory variables from the custom ones, there are is the template.
        # The custom variables are written at the end of the file
        templated_variables = {}
        grouped_variables = []
        for key, value in self.content.items():
            if key in TEMPLATED_VARS:
                templated_variables[key] = value
            else:
                # Group custom vars in list of dicts to be able to add comments
                prefix = key.split("_")[0]
                # if list not empty and same prefix, add to same dict
                if grouped_variables and grouped_variables[-1]["prefix"] == prefix:
                    grouped_variables[-1]["variables"][key] = value
                # Else create a new group
                else:
                    grouped_variables.append(
                        {"prefix": prefix, "variables": {key: value}}
                    )

        template = Template(VARS_TEMPLATE_DEFINITION)
        with self.vars_path.open(mode="w+") as file:
            file.write(template.render(templated_variables))
            if grouped_variables:
                for group in grouped_variables:
                    if len(group["variables"]) > 1:
                        file.write(f"\n## {group['prefix']}\n")
                    else:
                        file.write(f"\n")
                    yaml.dump(
                        group["variables"],
                        file,
                        indent=2,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False,
                        Dumper=MyDumper,
                        width=160,
                    )
            else:
                file.write(f"\n")

        if delete_legacy:
            for path in self.legacy_vars_paths:
                if path.exists():
                    path.unlink()


class MyDumper(yaml.Dumper):
    """configure better indentation and list & stuff like that
    Ref: https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation/39681672#39681672
    """

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def str_presenter(dumper, data):
    """configures yaml for dumping multiline strings
    Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
    """
    # If newline in the string (not at the end) use | style
    if data[:-1].count("\n") > 0:  # check for multiline string
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    # if long string, use > style
    if len(data) > 160:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def yaml_load_files(yaml_files):
    """Load YAML file defining the default value of the quickstart variables"""
    yaml_vars = []

    for file in yaml_files:
        with file.open() as f:
            yaml_vars.append(yaml.safe_load(f))

    # Check for duplicate keys accross files
    all_var_names = [key for dictionary in yaml_vars for key in dictionary]
    var_names_counts = Counter(all_var_names)
    duplicate_var_names = {key for key, count in var_names_counts.items() if count > 1}

    if duplicate_var_names:
        raise ValueError(f"Some keys are duplicated: {duplicate_var_names}")

    return {key: value for dictionary in yaml_vars for key, value in dictionary.items()}


# Try to convert tag as date with the expected format
# If it failed, it's not a date
def is_valid_date(tag):
    try:
        datetime.strptime(str(tag), "%Y%m%d")
    except ValueError:
        return False
    return True


def match_any_regex(data, patterns):
    for pattern in patterns:
        if re.match(pattern, data):
            return True
    return False


def main() -> int:
    args_parser = ArgumentParser()
    args_parser.add_argument("inventory_name")
    args_parser.add_argument("--no-backup", action="store_true", default=False)
    args_parser.add_argument("--no-delete", action="store_true", default=False)
    args_parser.add_argument("--inventories-path", default=DEFAULT_INVENTORIES_PATH)
    args_parser.add_argument("--version", default=None)
    args = args_parser.parse_args()

    # Configure the style of multiline str dump
    yaml.add_representer(str, str_presenter)

    # Define the inventory
    inventory = Inventory(path=f"{args.inventories_path}/{args.inventory_name}")
    inventory_unknown_files = inventory.get_unknown_files()
    if inventory_unknown_files:
        raise ValueError(
            "There are unknown files in the inventory, this script can't be safely use.\nUnknown files:\n"
            + "\n".join(["  - " + str(file) for file in inventory_unknown_files]),
        )

    # Read the reference values
    ref_values = yaml_load_files(REFERENCE_VALUES_PATH.rglob("*"))

    # Upgrade the inventory
    inventory.upgrade(ref_values, args.version)
    inventory.write_inventory(
        backup=not args.no_backup, delete_legacy=not args.no_delete
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
