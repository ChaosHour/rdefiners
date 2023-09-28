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

```bash

### Validate the DB and tables with the Views, triggers, procedures, and functions

```go
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
./rename_definers.py -s '`root`@`%`' -r '`flyway`@`%`' -d chaos -i ./chaos_dump.sql -o ./chaos_dump-fixed.sql --defaults-group-suffix=_primary1
All objects with definer '`root`@`%`' have been renamed to '`flyway`@`%`' in database 'chaos'
Database objects from 'chaos' have been restored from './chaos_dump-fixed.sql'
Database objects from 'chaos' have been restored from 'views_chaos-2023-09-28.sql'
```

Read the README.md in the project mysql8-docker for more information on how to use the docker container.