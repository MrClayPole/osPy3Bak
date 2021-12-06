#!/usr/bin/python3

from datetime import datetime, timedelta
from keystoneauth1 import session
from keystoneauth1.identity import v3
from cinderclient import client as cinder_client
from novaclient import client as nova_client
from glanceclient import client as glance_client
from keystoneclient.v3 import client as keystone_client

import argparse

## Function definitions
def get_nova_interface(args, projectid):
    return nova_client.Client(2.1, session=set_session(args, projectid) )

def get_cinder_interface(args, projectid):
    return cinder_client.Client(3.59, session=set_session(args, projectid) )

def get_glance_interface(args, projectid):
    return glance_client.Client(2, session=set_session(args, projectid) )

def get_keystone_interface(args, projectid): 
    return keystone_client.Client (interface='public', session=set_session(args, projectid) )

def set_session(args, projectid):
    auth = v3.Password(
        auth_url=args.keystoneurl,
        username=args.username,
        password=args.password,
        project_id=projectid,
        user_domain_id="default",
        user_domain_name="default")
    return session.Session(auth=auth)

## Main program
# Set program varibles
os_snapshot_prefix = "_osPy3Bak_"
os_snapshot_date = datetime.now()
#os_snapshot_date = datetime.now() - timedelta(days=4)
os_snapshot_continue = 0

#Process cli agruments
parser = argparse.ArgumentParser(description='Openstack snapshot creation script')
parser.add_argument('--keystone-url', '-k', dest='keystoneurl', help='URL to keystone API')
parser.add_argument('--username', '-u', help='username to connect to openstack API')
parser.add_argument('--password', '-p', help='password to connect to openstack API')
parser.add_argument('--project-id', '-i', dest='projectid', help='project id of user that connects to openstack API')
args = parser.parse_args()

# Verify command line options are not empty
if not args.keystoneurl or not args.username or not args.password or not args.projectid:
    print ("--keystone-url, --username, --password & --project-id paramters can't be empty")
    quit()

print("osPy3Bak-quota - List any quota changes required\r\n")

# dump data need from keystone API
os_projects = get_keystone_interface(args, args.projectid).projects.list()

for os_project in os_projects:
    try:
        os_snapshot_retention = os_project.osPy3Bak
    except:
        print (os_project.name, "- Skipping as osPy3Bak property is missing from project")
        continue
    try:
        os_snapshot_retention = int(os_snapshot_retention)
    except:
        print (os_project.name, "- Skipping as osPy3Bak property is not a number")
        continue
    if os_snapshot_retention < 0:
        print (os_project.name, "- Skipping as osPy3Bak property is a negative number")
        continue
    print (os_project.name, " - Checking if quota changes are required")
    os_volume = get_cinder_interface(args, os_project.id).volumes.list()
    os_volume_attachments = get_cinder_interface(args, os_project.id).attachments.list()
    os_snapshots = get_cinder_interface(args, os_project.id).volume_snapshots.list()
    os_quotas = (get_cinder_interface(args, os_project.id).quotas.get(os_project.id))
    os_snapshot_count = 0
    os_ospybak_snapshot_count = 0
    os_ospybak_snapshot_total_size = 0
    os_snapshot_total_size = 0
    os_ospybak_gb_per_snapshot = 0
    os_ospybak_volumes_per_snapshot = 0
    for os_snapshot in os_snapshots:
        if os_snapshot_prefix in os_snapshot.name:
            os_ospybak_snapshot_total_size = os_ospybak_snapshot_total_size + os_snapshot.size
            os_ospybak_snapshot_count = os_ospybak_snapshot_count + 1
        else:
            os_snapshot_total_size = os_snapshot_total_size + os_snapshot.size
            os_snapshot_count = os_snapshot_count + 1
    #print (os_project.name, "-", os_snapshot_count + os_ospybak_snapshotcount, "disk snapshots,", os_snapshot_total_size, "unmanged GB,", os_ospybak_snapshot_total_size, "managed GB,", os_ospybak_snapshot_total_size + os_snapshot_total_size, "Total GB" )
    for os_volume_attachment in os_volume_attachments:
        os_ospybak_volumes_per_snapshot = os_ospybak_volumes_per_snapshot + 1
        os_ospybak_gb_per_snapshot = os_ospybak_gb_per_snapshot + get_cinder_interface(args, os_project.id).volumes.get(os_volume_attachment.volume_id).size
    if os_snapshot_count + (os_ospybak_volumes_per_snapshot * os_snapshot_retention) > (os_quotas.snapshots):
        print (" Volume snapshot count quota on needs to change from", os_quotas.snapshots, "to", os_snapshot_count + (os_ospybak_volumes_per_snapshot * os_snapshot_retention))
    if os_snapshot_total_size + (os_ospybak_gb_per_snapshot * os_snapshot_retention) > (os_quotas.gigabytes):
        print (" Volume size quota on needs to change from", os_quotas.gigabytes, "to", os_snapshot_total_size + (os_ospybak_gb_per_snapshot * os_snapshot_retention))

# Backup completed. Showing stats
print ("Quota audit completed.")