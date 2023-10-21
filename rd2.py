#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" UPDATE: 2023-10-20 in a more Pythonic way 
ChaosHour - Kurt Larsen
"""

import os
import re
import subprocess
import datetime
import glob
from configparser import ConfigParser
from os import path
import mysql.connector


def get_client_config(file_path="~/.my.cnf"):
    """
    Parse file_path into dict
    :param file_path str: /path/to/mysql-config.txt
    Barrowed from modules/my_sql/files/move_procs.py
    """
    file_path = path.expanduser(file_path)
    cparser = ConfigParser()
    result = {}

    if path.exists(file_path):
        cparser.read(file_path)
        section = "client"
        if section in cparser.sections():
            result = cparser.items(section=section)
    config = {
        ("unix_socket" if key == "socket" else key): (
            value.strip("'") if key == "password" else value
        )
        for key, value in result
    }
    config.update({"use_pure": True, "charset": "utf8"})
    return config


def check_flyway_user_exists(database, mysql_client_path, my_cnf_path):
    """
    Make sure that the flyway user exists in the database and if not, raise an error.
    """
    # Define the command to check if the flyway user exists in the database
    check_flyway_user_exists_command = f"{mysql_client_path} -BNe 'SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = \"flyway\")'"
    # Run the command and capture the output
    check_flyway_user_exists_output = subprocess.check_output(
        check_flyway_user_exists_command, shell=True, text=True
    )
    # Decode the output and strip any whitespace
    check_flyway_user_exists_output = check_flyway_user_exists_output.strip()
    # If the output is 0, the user does not exist
    if check_flyway_user_exists_output == "0":
        # Raise an error
        raise ValueError(
            f"User 'flyway' does not exist in database '{database}'. Please create the user and try again."
        )
    # If the output is 1, the user exists
    elif check_flyway_user_exists_output == "1":
        # Print a message indicating that the user exists
        print(f"User 'flyway' exists in database '{database}'")
    # If the output is anything else, raise an error
    else:
        raise ValueError(
            f"Unexpected output from command '{check_flyway_user_exists_command}': {check_flyway_user_exists_output}"
        )


def dump_database(database, mysqldump_path, mysql_client_path, my_cnf_path, source_definer, replacement_definer):
    """
    Dump the stored procedures, triggers, events, and views to a SQL file, modify the definer, and restore the database.
    """
    # Read the MySQL credentials from the my.cnf file
    config = get_client_config(my_cnf_path)

    input_file = f"{database}_dump.sql"
    output_file = f"{database}_dump-fixed.sql"
    output_file_path = f"{database}_dump.sql"

    # Check if GTIDs are enabled
    gtid_mode = (
        subprocess.check_output(
            [
                mysql_client_path,
                "-NBe",
                "SELECT @@GLOBAL.GTID_MODE",
            ]
        )
        .decode()
        .strip()
    )
    if gtid_mode == "OFF":
        # Define the MySQL command to dump the stored procedures, triggers, events, and views to a SQL file
        dump_command = f"{mysqldump_path} -d -E -R -n -t --triggers --add-drop-trigger {database} > {output_file_path}"
    else:
        # Define the MySQL command to dump the stored procedures, triggers, events, and views to a SQL file with GTIDs
        dump_command = f"{mysqldump_path} -d -E -R -n -t --triggers --add-drop-trigger --set-gtid-purged=OFF {database} > {output_file_path}"

    # Run the MySQL command to dump the stored procedures, triggers, events, and views to a SQL file
    subprocess.check_call(dump_command, shell=True)

    # Define the name of the output SQL file for the views
    new_output_file_name = (
        f"views_{database}-{datetime.datetime.now().strftime('%F')}.sql"
    )
    new_output_file_path = os.path.join(os.getcwd(), new_output_file_name)

    # Define the command to dump views to a SQL file
    dump_views_command = f'{mysql_client_path} -NBse \'SELECT CONCAT("DROP TABLE IF EXISTS ", TABLE_SCHEMA, ".", TABLE_NAME, "; CREATE OR REPLACE VIEW ", TABLE_SCHEMA, ".", TABLE_NAME, " AS ", VIEW_DEFINITION, "; ") AS table_name FROM information_schema.views WHERE TABLE_SCHEMA = "{database}"\' > {new_output_file_path}'

    # Run the command to dump views to a SQL file
    subprocess.check_call(dump_views_command, shell=True)

    # Open the views SQL file and read the contents
    with open(new_output_file_path, "r") as views_sql_file:
        views_sql_file_contents = views_sql_file.read()

    # Add the definer from the -r argument to the views SQL file for every view in that file.
    # Example output: DROP TABLE IF EXISTS char_test_db.my_view; CREATE OR REPLACE DEFINER = `flyway`@`%` VIEW char_test_db.my_view AS select `char_test_db`.`my_table`.`col1` AS `col1`,`char_test_db`.`my_table`.`col2` AS `col2` from `char_test_db`.`my_table` where (`char_test_db`.`my_table`.`col1` > 0);
    # Get the definer from the -r argument
    replacement_definer = replacement_definer

    # Add the DEFINER bewteen the CREATE and VIEW keywords in the views SQL file
    views_sql_file_contents = views_sql_file_contents.replace(
        "REPLACE VIEW", f"REPLACE DEFINER = {replacement_definer} VIEW"
    )

    # Write the modified views SQL file contents to the views SQL file
    with open(new_output_file_path, "w") as views_sql_file:
        views_sql_file.write(views_sql_file_contents)

    # Define the path to the backup file
    backup_file_path = os.path.splitext(output_file_path)[0] + "_backup.sql"

    # Make a backup of the SQL file
    with open(output_file_path, "r") as sql_file, open(
        backup_file_path, "w"
    ) as backup_file:
        backup_file.write(sql_file.read())

    # Define the regular expression pattern to match the source definer
    definer_pattern = re.compile(source_definer)

    # Read the input MySQL dump file
    with open(input_file, "r") as f:
        input_data = f.read()

    # Replace the source definer with the replacement definer in the MySQL dump data
    new_definer = f"{replacement_definer}"
    output_data = definer_pattern.sub(new_definer, input_data)

    # Write the modified MySQL dump data to the output file
    with open(output_file, "w") as output_file:
        output_file.write(output_data)

    # Print a message indicating that the definer has been renamed
    print(
        f"All objects have been renamed to '{replacement_definer}' in database '{database}'"
    )

    # Define the name of the output SQL file for the stored procedures, triggers, and events
    output_file_name = f"{database}_dump-fixed.sql"
    output_file_path = os.path.join(os.getcwd(), output_file_name)

    # Find the views SQL file based on its prefix
    views_file_pattern = f"views_{database}*.sql"
    views_files = glob.glob(views_file_pattern)
    if len(views_files) == 0:
        raise ValueError(
            f"No views SQL file found matching pattern '{views_file_pattern}'"
        )
    elif len(views_files) > 1:
        raise ValueError(
            f"Multiple views SQL files found matching pattern '{views_file_pattern}': {views_files}"
        )
    else:
        views_file = views_files[0]

    # Print out the file paths
    print(f"Output file path: {output_file_path}")
    print(f"Views file path: {views_file}")

    # Use the files with a suffix of _dump-fixed.sql and _views-fixed.sql to restore the database
    for input_file in [output_file_path, views_file]:
        restore_command = f"{mysql_client_path} {database} < {input_file}"
        subprocess.check_call(restore_command, shell=True)
        print(
            f"Database objects from '{database}' have been restored from '{input_file}'"
        )


def main():
    # Define the path to the my.cnf file
    my_cnf_path = "~/.my.cnf"

    # Get the MySQL client configuration
    mysql_config = get_client_config(my_cnf_path)

    # Use the MySQL client configuration to connect to the database
    cnx = mysql.connector.connect(**mysql_config)

    # Set the command line arguments
    source_definer = "`[^`]+`@`[^`]+`"
    replacement_definer = "`flyway`@`%`"
    excluded_databases = ["mysql", "information_schema", "performance_schema", "sys"]
    defaults_group_suffix = "_primary1"

    command2 = "which mysql"

    # Run the command and capture the output
    output2 = subprocess.check_output(command2, shell=True)

    # Decode the output and strip any whitespace
    mysql_client_path = output2.decode().strip()

    list_databases_command = f"{mysql_client_path} -BNe 'SHOW DATABASES'"
    list_databases_output = subprocess.check_output(
        list_databases_command, shell=True, text=True
    )
    all_databases = list_databases_output.strip().split("\n")

    valid_databases = [db for db in all_databases if db not in excluded_databases]

    # Define the command to find the path to the mysqldump executable
    command = "which mysqldump"

    # Run the command and capture the output
    output = subprocess.check_output(command, shell=True)

    # Decode the output and strip any whitespace
    mysqldump_path = output.decode().strip()

    print(valid_databases)

    for database in valid_databases:
        # Call the check_flyway_user_exists() function
        check_flyway_user_exists(database, mysql_client_path, my_cnf_path)
        dump_database(database, mysqldump_path, mysql_client_path, my_cnf_path, source_definer, replacement_definer)


if __name__ == "__main__":
    main()