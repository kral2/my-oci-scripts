#!/usr/bin/env python3

# ----------------------------------------------------------------------------------------
# This script removes a defined tag key (using tag namespace) from a compute instance
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-04-16: Initial Version
# ----------------------------------------------------------------------------------------

# -- import
import oci
import sys

# ---------- Functions

# ---- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---- usage syntax
def usage():
    print ("Usage: {} OCI_PROFILE instance_ocid tag_namespace tag_key".format(sys.argv[0]))
    print ("")
    print ("")
    print ("note: OCI_PROFILE must exist in {} file (see example below)".format(configfile))
    print ("")
    print ("[EMEAOSCf]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

# ------------ main
global config

# -- parse arguments
if len(sys.argv) == 5:
    profile  = sys.argv[1]
    inst_id  = sys.argv[2] 
    tag_ns   = sys.argv[3]
    tag_key  = sys.argv[4]
else:
    usage()

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)

except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Get Defined-tags for the compute instance
ComputeClient = oci.core.ComputeClient(config)

try:
    response = ComputeClient.get_instance(inst_id)
    instance = response.data
except:
    print ("ERROR 03: instance with OCID '{}' not found !".format(inst_id))
    exit (3)

# -- Remove tag key from tag namespace
tags = instance.defined_tags
try:
    del tags[tag_ns][tag_key]
except:
    print ("ERROR 04: this tag key does not exist for this compute instance !")
    exit (3)

# -- Update compute instance
ComputeClient.update_instance(inst_id, oci.core.models.UpdateInstanceDetails(defined_tags=tags))

# -- the end
exit (0)