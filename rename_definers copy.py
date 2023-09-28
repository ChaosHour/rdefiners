#! /usr/bin/env python3


'''
Example usage:
Baackticks are required around the definer names. 
 ./rename_definers.py -s '`root`@`%`' -r '`flyway`@`%`' -d char_test_db -i ./char_test_db_dump.sql -o ./char_test_db_dump-fixed.sql --defaults-group-suffix=_primary1
All objects with definer '`root`@`%`' have been renamed to '`flyway`@`%`' in database 'char_test_db'
Database objects from 'char_test_db' have been restored from './char_test_db_dump-fixed.sql'
Database objects from 'char_test_db' have been restored from 'views_char_test_db-2023-09-20.sql'
'''


import argparse
import configparser
import os
import re
import subprocess
import sys
import datetime
import glob

# Define the function to find the path to the MySQL client
def find_mysql_client():
    # Check if the MySQL client is in the system's PATH environment variable
    try:
        subprocess.check_call(['mysql', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 'mysql'
    except subprocess.CalledProcessError:
        pass

    # Check if the MySQL client is installed with Homebrew on macOS
    if sys.platform == 'darwin':
        try:
            brew_prefix = subprocess.check_output(['brew', '--prefix'], universal_newlines=True).strip()
            mysql_client_path = os.path.join(brew_prefix, 'bin', 'mysql')
            subprocess.check_call([mysql_client_path, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return mysql_client_path
        except subprocess.CalledProcessError:
            pass

# Define the path to the my.cnf file
my_cnf_path = os.path.expanduser('~/.my.cnf')

# Parse the command line arguments
parser = argparse.ArgumentParser(description='Rename all objects with a given definer in a MySQL database.')
parser.add_argument('-s', '--source-definer', required=True, help='The definer to search for (e.g. root@localhost)')
parser.add_argument('-r', '--replacement-definer', required=True, help='The definer to replace the source definer with (e.g. flyway@%)')
parser.add_argument('-d', '--database', required=True, help='The name of the database to search in')
parser.add_argument('--defaults-group-suffix', help='The suffix to add to the group name when reading options from the my.cnf file')
parser.add_argument("-i", "--input-file", required=True, help="The path to the input MySQL dump file")
parser.add_argument("-o", "--output-file", required=True, help="The path to the output MySQL dump file")
args = parser.parse_args()

# Find the path to the MySQL client
mysql_client_path = find_mysql_client()

# Read the MySQL credentials from the my.cnf file
config = configparser.ConfigParser()
config.read(my_cnf_path)
mysql_user = config[f'client{args.defaults_group_suffix}']['user']
mysql_password = config[f'client{args.defaults_group_suffix}']['password']
mysql_host = config[f'client{args.defaults_group_suffix}']['host']

# Define the path to the output file
output_file_path = f"{args.database}_dump.sql"

# Define the command to find the path to the mysqldump executable
command = "which mysqldump"

# Run the command and capture the output
output = subprocess.check_output(command, shell=True)

# Decode the output and strip any whitespace
mysqldump_path = output.decode().strip()

# Check if the path exists and is executable
if not os.path.exists(mysqldump_path) or not os.access(mysqldump_path, os.X_OK):
    raise ValueError("mysqldump not found or not executable")

# Check if GTIDs are enabled
gtid_mode = subprocess.check_output([mysql_client_path, '--defaults-group-suffix={}'.format(args.defaults_group_suffix), '-NBe', 'SELECT @@GLOBAL.GTID_MODE']).decode().strip()
if gtid_mode == 'OFF':
    # Define the MySQL command to dump the stored procedures, triggers, events, and views to a SQL file
    dump_command = f"{mysqldump_path} --defaults-group-suffix={args.defaults_group_suffix} -d -E -R -n -t --triggers --add-drop-trigger {args.database} > {output_file_path}"
else:
    # Define the MySQL command to dump the stored procedures, triggers, events, and views to a SQL file with GTIDs
    dump_command = f"{mysqldump_path} --defaults-group-suffix={args.defaults_group_suffix} -d -E -R -n -t --triggers --add-drop-trigger --set-gtid-purged=OFF {args.database} > {output_file_path}"

# Run the MySQL command to dump the stored procedures, triggers, events, and views to a SQL file
subprocess.check_call(dump_command, shell=True)

# Define the name of the output SQL file for the views
new_output_file_name = f"views_{args.database}-{datetime.datetime.now().strftime('%F')}.sql"
new_output_file_path = os.path.join(os.getcwd(), new_output_file_name)

# Define the command to dump views to a SQL file
dump_views_command = f"{mysql_client_path} --defaults-group-suffix={args.defaults_group_suffix} -NBse 'SELECT CONCAT(\"DROP TABLE IF EXISTS \", TABLE_SCHEMA, \".\", TABLE_NAME, \"; CREATE OR REPLACE VIEW \", TABLE_SCHEMA, \".\", TABLE_NAME, \" AS \", VIEW_DEFINITION, \"; \") AS table_name FROM information_schema.views WHERE TABLE_SCHEMA = \"{args.database}\"' > {new_output_file_path}"

# Run the command to dump views to a SQL file
subprocess.check_call(dump_views_command, shell=True)



# Open the views SQL file and read the contents
with open(new_output_file_path, "r") as views_sql_file:
    views_sql_file_contents = views_sql_file.read()
    #print (views_sql_file_contents)


# Add the definer from the -r argument to the views SQL file for every view in that file. 
# Example output: DROP TABLE IF EXISTS char_test_db.my_view; CREATE OR REPLACE DEFINER = `flyway`@`%` VIEW char_test_db.my_view AS select `char_test_db`.`my_table`.`col1` AS `col1`,`char_test_db`.`my_table`.`col2` AS `col2` from `char_test_db`.`my_table` where (`char_test_db`.`my_table`.`col1` > 0);
# Get the definer from the -r argument
replacement_definer = args.replacement_definer

# Add the DEFINER bewteen the CREATE and VIEW keywords in the views SQL file
views_sql_file_contents = views_sql_file_contents.replace("REPLACE VIEW", f"REPLACE DEFINER = {replacement_definer} VIEW")

# Write the modified views SQL file contents to the views SQL file
with open(new_output_file_path, "w") as views_sql_file:
    views_sql_file.write(views_sql_file_contents)

# Define the path to the backup file
backup_file_path = os.path.splitext(output_file_path)[0] + "_backup.sql"

# Make a backup of the SQL file
with open(output_file_path, "r") as sql_file, open(backup_file_path, "w") as backup_file:
    backup_file.write(sql_file.read())

# Define the regular expression pattern to match the source definer
definer_pattern = re.compile(re.escape(args.source_definer))

# Read the input MySQL dump file
with open(args.input_file, "r") as input_file:
    input_data = input_file.read()

# Replace the source definer with the replacement definer in the MySQL dump data
new_definer = f"{args.replacement_definer}"
output_data = definer_pattern.sub(new_definer, input_data)

# Write the modified MySQL dump data to the output file
with open(args.output_file, "w") as output_file:
    output_file.write(output_data)

# Print a message indicating that the definer has been renamed
print(f"All objects with definer '{args.source_definer}' have been renamed to '{args.replacement_definer}' in database '{args.database}'")

'''
# Use the file with a suffix of _dump-fixed.sql to restore the database and let me know if it worked
restore_command = f"{mysql_client_path} --defaults-group-suffix={args.defaults_group_suffix} {args.database} < {args.output_file}"
subprocess.check_call(restore_command, shell=True)
print(f"Database '{args.database}' has been restored from '{args.output_file}'")
'''


'''
# Use the files with a suffix of _dump-fixed.sql and _views-fixed.sql to restore the database and let me know if it worked
for input_file in [args.output_file, "views_char_test_db-2023-09-20.sql"]:
    restore_command = f"{mysql_client_path} --defaults-group-suffix={args.defaults_group_suffix} {args.database} < {input_file}"
    subprocess.check_call(restore_command, shell=True)
    print(f"Database '{args.database}' has been restored from '{input_file}'")
'''

# Find the views SQL file based on its prefix
views_file_pattern = "views*.sql"
views_files = glob.glob(views_file_pattern)
if len(views_files) == 0:
    raise ValueError(f"No views SQL file found matching pattern '{views_file_pattern}'")
elif len(views_files) > 1:
    raise ValueError(f"Multiple views SQL files found matching pattern '{views_file_pattern}': {views_files}")
else:
    views_file = views_files[0]

# Use the files with a suffix of _dump-fixed.sql and _views-fixed.sql to restore the database and let me know if it worked
for input_file in [args.output_file, views_file]:
    restore_command = f"{mysql_client_path} --defaults-group-suffix={args.defaults_group_suffix} {args.database} < {input_file}"
    subprocess.check_call(restore_command, shell=True)
    print(f"Database objects from '{args.database}' have been restored from '{input_file}'")