#!/usr/bin/python3

from datetime import datetime, timedelta
from keystoneauth1 import session
from keystoneauth1.identity import v3
from cinderclient import client as cinder_client
from novaclient import client as nova_client
from glanceclient import client as glance_client
from keystoneclient.v3 import client as keystone_client

import argparse
import sys

## Function definitions
def prune_os_snapshots(vm_name, os_images, os_snapshots, os_snapshot_prefix, os_snapshot_date, os_snapshot_retention, projectid):
    for os_snapshot in os_snapshots:
        if os_snapshot.name.startswith("snapshot for " + vm_name + os_snapshot_prefix):
            if datetime.date(os_snapshot_date) - timedelta(days=os_snapshot_retention) >= datetime.strptime(os_snapshot.name[-10:], "%Y-%m-%d").date():
                get_cinder_interface(args, projectid).volume_snapshots.delete(os_snapshot.id)
                print (" DELETED: ", os_snapshot.name)

def prune_os_images(vm_name, os_images, os_snapshot_prefix, os_snapshot_date, os_snapshot_retention, projectid):
    for os_image in os_images:
        if os_image.name.startswith(vm_name + os_snapshot_prefix):
            if datetime.date(os_snapshot_date) - timedelta(days=os_snapshot_retention) >= datetime.strptime(os_image.name[-10:], "%Y-%m-%d").date():
                get_glance_interface(args, projectid).images.delete(os_image.id)
                print (" DELETED: Image", os_image.name)

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
    quit(1)

print("osPy3Bak - Iterating all projects in cloud\r\n")

# dump data need from keystone API
os_projects = get_keystone_interface(args, args.projectid).projects.list()

# Default backup counters
skipped = 0
failed = 0
success = 0


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
    print (os_project.name, " - Snapshotting all VMs")
    os_images = get_nova_interface(args, os_project.id).glance.list()
    os_snapshots = get_cinder_interface(args, os_project.id).volume_snapshots.list()
    os_vms = get_nova_interface(args, os_project.id).servers.list()
    for os_vm in os_vms:
        if os_vm.status == "SHELVED_OFFLOADED" and os_snapshot_retention > 0:
            print (" SKIPPED:", os_vm.name, "is shelved. Snapshotting not permitted")
            skipped += 1
            continue
        if os_vm.name + os_snapshot_prefix + os_snapshot_date.strftime("%Y-%m-%d") in str(os_images) and os_snapshot_retention > 0:
            print(" SKIPPED:", os_vm.name, "already has a image for date", os_snapshot_date.strftime("%Y-%m-%d"))
            skipped += 1
            continue
        for os_snapshot in os_snapshots:
            if ("snapshot for " + os_vm.name + os_snapshot_prefix + os_snapshot_date.strftime("%Y-%m-%d")) in str(os_snapshot.name) and os_snapshot_retention > 0:
                print(" SKIPPED:", os_vm.name, "already has volume sanpshot(s) for date", os_snapshot_date.strftime("%Y-%m-%d"))
                skipped += 1
                os_snapshot_continue = 1
                break
        if os_snapshot_continue == 1:
            os_snapshot_continue = 0
            continue
        if os_snapshot_retention > 0:
            try:
                get_nova_interface(args, os_project.id).servers.create_image(os_vm.id, os_vm.name + os_snapshot_prefix + os_snapshot_date.strftime("%Y-%m-%d"))
            except Exception as e:
                print (" FAILED:", os_vm.name, ":", e)
                failed += 1
                continue
            print (" CREATED: image of", os_vm.name, "backup dated", os_snapshot_date.strftime("%Y-%m-%d"))
            success += 1
        prune_os_images(os_vm.name, os_images, os_snapshot_prefix, os_snapshot_date, os_snapshot_retention, os_project.id)
        prune_os_snapshots(os_vm.name, os_images, os_snapshots, os_snapshot_prefix, os_snapshot_date, os_snapshot_retention, os_project.id)

# Backup completed. Showing stats
print ("Backup completed.", success, "Successful,", skipped, "Skipped,", failed, "Failed")

# Set exit code based on errors

if failed > 0:
        sys.exit(1)
if skipped > 0:
        sys.exit(2)
if skipped == 0 and failed == 0:
        sys.exit(3)
