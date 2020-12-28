# router-map

[![Build Status](https://travis-ci.org/comp-sa/router-map.svg?branch=master)](https://travis-ci.org/comp-sa/router-map)

The program allows to create maps and diagrams with routers and connections between them. 
Uses data detected by the LLDP protocol, collected on each device. 
Information is taken via SNMP or NETCONF protocol.

![Example](sample-data/example.png)

## Supported devices
Router-map was tested on networks with Juniper devices MX, QFX and SRX with Junos version 16.1 and newer.


You have to enable LLDP on all routers. Also SNMP or NETCONF protocol is required

Sample of SRX configuration for SNMP protocol: 

```
snmp {                                  
    name NAME1;       
    community snmp_community {                    
        authorization read-only;        
    }                                   
} 
```
## Running with Docker

#### Building & Running
Run application on port 8080:
```
docker-compose -f production.yml up -d
```

To check the logs out, run:
```
docker-compose -f production.yml logs
```

#### Environment variables
Environment variables for postgres database should be defined in file .envs/.production/.postgres

| Variable name         | Description   |  Default value   |
| -------------         |:-------------:|:-------------:|
| POSTGRES_HOST         | Postgres host. | postgres |
| POSTGRES_PORT         | Postgres port. | 5432 |
| POSTGRES_DB           | Postgres database name. | router-map |
| POSTGRES_USER         | Postgres user name. | router-map |
| POSTGRES_PASSWORD     | Postgres user password. | router-map |

Environment variables for django app should be defined in file .envs/.production/.django

| Variable name             | Description |  Default value   |
| -------------             |:-------------:|:-------------:|
| DJANGO_SETTINGS_MODULE    | Should be set to 'config.settings.production' for production or to 'config.settings.local' for local development. | config.settings.production |
| DJANGO_SECRET_KEY         | Should be set to a unique value. It is used by django to provide cryptographic signing.| gtOQBX7rlOtY1A7 |
| DJANGO_ALLOWED_HOSTS      | A list of strings representing the host/domain names that this Django site can serve. To match anything set value '*'. | * |
| WEB_CONCURRENCY           | Number of gunicorn workers. | 4 |
| REDIS_URL                 | Redis URL (Redis is used as Celery broker). | redis://redis:6379/0 |
| REDIS_HOST                | Redis host. | redis |
| TASK_PERIOD               | Period of time between router connection checks in minutes.| 15 |
| CELERY_FLOWER_USER        | Celery flower user name. | router-map |
| CELERY_FLOWER_PASSWORD    | Celery flower user password. | router-map |
| NETCONF_USER              | Netconf user. Required only if Netconf is used. |  |
| NETCONF_PASSWORD          | Netconf user password. Required only if Netconf is used. |  |

## Usage

#### Prerequisites
Before continuing you must have the following installed and working correctly:
 * Docker
 * docker-compose (1.24 or above) 
 * Environment variables in .envs folder (example is in this repository)
 * `docker-compose.yml` file from this repository 
 
#### Get started

1) Clone this repository  
`git clone git@github.com:comp-sa/router-map.git`

1) Run all services. Web application will be run on port 8080  
`docker-compose up -d`

2) Create admin user (to view any visualisations, user has to be logged in)  
`docker-compose run django python manage.py createsuperuser`

3) You can create further user accounts and assign permissions in admin panel (`http://localhost:8080/admin`). 

4) Open web application and log in on `http://localhost:8080`.

5) To add new visualizations, select `Add visualization` from the menu on the main page. Devices can be added to the created visualization via a csv file or by filling in the form manually using devices previously added to the system.
To edit or add new devices (useful when you do not use the csv file to add devices to the visualization), select `Manage devices` from the menu on the main page. For each device, you can select the protocol used to obtain data from the device: NETCONF or SNMP.

## Updating to new version

To update, you have to install new version. Unfortunately to restore data, you have to define map again by using add form. You can use the same csv file with devices as in old version.

## Development
Steps to build and run
1) Clone this repository
```
git clone git@github.com:comp-sa/router-map.git
```
2) Run as above but with flag `-f development.yml`, for example:
```
docker-compose -f development.yml run django python manage.py createsuperuser
```
