# Openstack_snapshot_scripts
Python scripts to walk all Openstack projects and snapshot all VMs in that project and then removes any snapshots/images past a configure number of days.

Which projects get backed up and their retention is set by assigning a number to the property "osPyBak" against a project.

osPy3Bak > 1 
    The number of daily snapshots to be kept

osPy3Bak = 0
    Don't create snapshots but delete all osPy3Bak managed snapshots

osPy3Bak < 0 or osPy3Bak property missing
    Backup is disabled. skip this project

# Usage 
./opPy3Bak --keystone-url <keysone v3 URL> --username <username> --password <password> --project-id <project id of username>

example:
    ./opPy3Bak --keystone-url https://my.cloud.com:5000/v3 --username admin --password myunguessablepassword --project-id a2735df57a3644eab853876b7bb8fd2f
