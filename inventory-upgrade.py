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

REQUIRED_VARS = [
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
smtp_host: "{{ smtp_host }}"
smtp_port: {{ smtp_port }}
smtp_user: "{{ smtp_user }}"
smtp_pass: "{{ smtp_pass }}"
smtp_use_tls: {{ smtp_use_tls }}
smtp_default_email: "{{ smtp_default_email }}"
debug_mail_to: "{{ debug_mail_to }}"

{%- if docker_private_registry_login is defined and docker_private_registry_login | length %}

# Docker registry
docker_private_registry_login: {{ docker_private_registry_login }}

{% endif -%}

# Add your other configurations after this comment

"""

# TODO: need to check all the deprecated variables with the git history
DEPRECATED_VARS = {
        20221118: [".*extract_quantities.*"],
        20220928: ["mapbox_token"],
        20230309: ["swift_.*"],
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
                f"{self.path} is not a directory. Please specify the correct inventory name when you call this script."
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
                    print(
                        f"Warning: Legacy inventory, but missing file {file_path}."
                    )

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
            if key in self.content and self.content[key] == value:
                del self.content[key]

        # If docker_bimdata_tag is defined, but no custom images
        # Remove it, next time the upgrade will be automatic
        if not self.use_custom_tag():
            if "docker_bimdata_tag" in self.content:
                del self.content["docker_bimdata_tag"]

        self.is_legacy = False

    def upgrade(self, ref_values={}, version=None):
        if self.is_legacy:
            self.migrate_legacy(ref_values)

        if version:
            self.content["docker_bimdata_tag"] = version
        elif "docker_bimdata_tag" in self.content:
            version = self.content["docker_bimdata_tag"]
        else:
            version = ref_values.get("docker_bimdata_tag")
            # Skip if no specified version and custom images
            # We can't be sure the last version is used
            if self.use_custom_tag():
                print(
                    f"Warning: this inventory use custom Docker images or tags."
                    f"You should launch this script with --version XXXXXXXX."
                    f"The inventory upgrade is skipped."
                )
                return 1

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
        # TODO: this is not working when there are deprecated images in the inventory
        # Not sure how to managed this case yet
        ignored_images = [
            "docker_rabbitmq.*",
            "docker_postgres.*",
            "docker_nginx.*",
            "docker_acme_companion.*",
            "docker_bimdata_tag",
        ]
        for key in self.content:
            if re.match("docker_.*_tag", key):
                if self.content[key] == "{{ docker_bimdata_tag }}":
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
                f"The inventory will be backup up into: {backup_path}\n"
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
        required_variables, custom_variables = {}, {}
        for key, value in self.content.items():
            if key in REQUIRED_VARS:
                required_variables[key] = value
            else:
                custom_variables[key] = value

        template = Template(VARS_TEMPLATE_DEFINITION)
        with self.vars_path.open(mode="w+") as file:
            file.write(template.render(required_variables))
            if custom_variables:
                yaml.dump(
                    custom_variables,
                    file,
                    indent=2,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                    Dumper=MyDumper,
                    width=200,
                )
        if delete_legacy:
            for path in self.legacy_vars_paths:
                path.unlink()


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
            + "\n".join(["  - " + file for file in inventory_unknown_files]),
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
