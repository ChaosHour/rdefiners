# rdefiners

## Prep for testing

### Install Docker 
[mysql8-docker](https://github.com/ChaosHour/mysql8-docker)

```bash
docker-compose up -d --wait

[+] Running 3/3
 ✔ Network mysql8-docker_db-network         Created                                                                                                                                                                               0.1s
 ✔ Container mysql8-docker-mysql-primary-1  Healthy                                                                                                                                                                               0.0s
 ✔ Container mysql8-docker-mysql-replica-1  Healthy                                                                                                                                                                               0.0s 
```

### Assuming Python is installed

```bash
pipenv shell

pip install -r requirements.txt
```

### Create the DB and tables with the Views, triggers, procedures, and functions

```bash
cat primary/test.sql | mysql --defaults-group-suffix=_primary1

```

### Validate the DB and tables with the Views, triggers, procedures, and functions

[go-pvt](https://github.com/ChaosHour/go-pvt)

```Go
go-pvt -s 192.168.50.50 -d chaos
Connected to 192.168.50.50 (114f42533e88): ✔

Total: 5

Objects:

NAME               	TYPE        	DEFINER 	
my_proc           	(PROCEDURE)	root@% 	
my_view           	(VIEW)     	root@% 	
my_view2          	(VIEW)     	root@% 	
set_default_salary	(TRIGGER)  	root@% 	
my_event          	(EVENT)    	root@% 	

```

### Run the tests

```python
rdefiners on  chaos_testing [✘!?] via 🐍 v3.11.5 (rdefiners) 
❯ ./rd.py
['chaos', 'char_test_db', 'jester']
All objects have been renamed to '`flyway`@`%`' in database 'chaos'
Output file path: /Users/klarsen/projects/rdefiners/chaos_dump-fixed.sql
Views file path: views_chaos-2023-09-29.sql
Database objects from 'chaos' have been restored from '/Users/klarsen/projects/rdefiners/chaos_dump-fixed.sql'
Database objects from 'chaos' have been restored from 'views_chaos-2023-09-29.sql'
All objects have been renamed to '`flyway`@`%`' in database 'char_test_db'
Output file path: /Users/klarsen/projects/rdefiners/char_test_db_dump-fixed.sql
Views file path: views_char_test_db-2023-09-29.sql
Database objects from 'char_test_db' have been restored from '/Users/klarsen/projects/rdefiners/char_test_db_dump-fixed.sql'
Database objects from 'char_test_db' have been restored from 'views_char_test_db-2023-09-29.sql'
All objects have been renamed to '`flyway`@`%`' in database 'jester'
Output file path: /Users/klarsen/projects/rdefiners/jester_dump-fixed.sql
Views file path: views_jester-2023-09-29.sql
Database objects from 'jester' have been restored from '/Users/klarsen/projects/rdefiners/jester_dump-fixed.sql'
Database objects from 'jester' have been restored from 'views_jester-2023-09-29.sql'
```

```Go
go-pvt -s 192.168.50.50 -d chaos
Connected to 192.168.50.50 (114f42533e88): ✔

Total: 5

Objects:

NAME               	TYPE        	DEFINER  	
my_proc           	(PROCEDURE)	flyway@%	
my_view           	(VIEW)     	flyway@%	
my_view2          	(VIEW)     	flyway@%	
set_default_salary	(TRIGGER)  	flyway@%	
my_event          	(EVENT)    	flyway@%	
```

## Added. refactored and tested rd2.py

```python
❯ ./rd2.py
['chaos']
User 'flyway' exists in database 'chaos'
All objects have been renamed to '`flyway`@`%`' in database 'chaos'
Output file path: /Users/KLarsen/projects/python_code/rdefiners/chaos_dump-fixed.sql
Views file path: views_chaos-2023-10-20.sql
Database objects from 'chaos' have been restored from '/Users/KLarsen/projects/python_code/rdefiners/chaos_dump-fixed.sql'
Database objects from 'chaos' have been restored from 'views_chaos-2023-10-20.sql'
```
## Reason
```bash
""" UPDATE: 2023-10-20 in a more Pythonic way 
ChaosHour - Kurt Larsen
"""
```

Read the README.md in the project mysql8-docker for more information on how to use the docker container.