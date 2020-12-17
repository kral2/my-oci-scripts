#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script computes the total amount of block storage used in each compartment in a region or all active regions using OCI Python SDK
# Optionnaly list all boot volumes and block volumes
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-15-12: Initial Version
# ---------------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import operator

# ---------- Colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
colored_output=True
if (colored_output):
  COLOR_TITLE0="\033[95m"             # light magenta
  COLOR_TITLE1="\033[91m"             # light red
  COLOR_TITLE2="\033[32m"             # green
  COLOR_AD="\033[94m"                 # light blue
  COLOR_COMP="\033[93m"               # light yellow
  COLOR_BREAK="\033[91m"              # light red
  COLOR_NORMAL="\033[39m"
else:
  COLOR_TITLE0=""
  COLOR_TITLE1=""
  COLOR_TITLE2=""
  COLOR_AD=""
  COLOR_COMP=""
  COLOR_BREAK=""
  COLOR_NORMAL=""

# ---------- Functions

# ---- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---- usage syntax
def usage():
    print ("Usage: {} OCI_PROFILE compartment_ocid".format(sys.argv[0]))
    print ("    or {} OCI_PROFILE compartment_name".format(sys.argv[0]))
    #print ("Usage: {} [-a] [-v] OCI_PROFILE compartment_ocid".format(sys.argv[0]))
    #print ("    or {} [-a] [-v] OCI_PROFILE compartment_name".format(sys.argv[0]))   print ("")
    #print ("    By default, only the region provided in the profile is processed")
    #print ("    If -a is provided, all subscribed regions are processed")
    #print ("    If -v is provided, all boot volumes and blocks in compartments are displayed")
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

# -- Get the complete name of a compartment from its id, including parent and grand-parent..
def get_cpt_name_from_id(cpt_id):
    global compartments

    if cpt_id == RootCompartmentID:
        return "root"

    name=""
    for c in compartments:
        if (c.id == cpt_id):
            name=c.name

            # if the cpt is a direct child of root compartment, return name
            if c.compartment_id == RootCompartmentID:
                return name
            # otherwise, find name of parent and add it as a prefix to name
            else:
                name = get_cpt_name_from_id(c.compartment_id)+":"+name
                return name

# ------------ main

# -- parse arguments
if len(sys.argv) == 2:
    profile  = sys.argv[1] 
else:
    usage()

# -- get info from profile
try:
    config = oci.config.from_file(configfile,profile)

except:
    print ("ERROR: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- Get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query_block_volume = "query volume resources"
query_boot_volume  = "query bootvolume resources"

# -- Clients
gb_used = {}
SearchClient = oci.resource_search.ResourceSearchClient(config)
BlockstorageClient = oci.core.BlockstorageClient(config)
details = False
total_gb_used = 0

# -- Run the search query to get list of BLOCK volumes then for each volume, use get_volume() to get size
# -- Finally store the result in a dictionary
if details:
    print ("LIST OF BLOCK VOLUMES:")

response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query_block_volume))
for item in response.data.items:
    if item.lifecycle_state != "TERMINATED":
        # as size is not returned by the query search, we need to get the size of each block volume.
        response2 = BlockstorageClient.get_volume(item.identifier)
        vol = response2.data
        if gb_used.get(item.compartment_id) == None:
            gb_used[item.compartment_id] = vol.size_in_gbs
        else:
            gb_used[item.compartment_id] += vol.size_in_gbs
        if details:
            print (f"- {vol.id}, {vol.size_in_gbs:5d} GBs, {vol.display_name}")
        total_gb_used += vol.size_in_gbs

# -- Run the search query to get list of BOOT volumes then for each volume, use get_boot_volume() to get size
# -- Finally store the result in the same dictionary
if details:
    print ("")
    print ("LIST OF BOOT VOLUMES:")

response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query_boot_volume))
for item in response.data.items:
    if item.lifecycle_state != "TERMINATED":
        # as size is not returned by the query search, we need to get the size of each boot volume.
        response2 = BlockstorageClient.get_boot_volume(item.identifier)
        vol = response2.data
        if gb_used.get(item.compartment_id) == None:
            gb_used[item.compartment_id] = vol.size_in_gbs
        else:
            gb_used[item.compartment_id] += vol.size_in_gbs
        if details:
            print (f"- {vol.id}, {vol.size_in_gbs:5d} GBs, {vol.display_name}")
        total_gb_used += vol.size_in_gbs

# -- sort the dictionary by descending total size 
gb_used_sorted = dict(sorted(gb_used.items(), key=operator.itemgetter(1), reverse=True))

# -- display the result
if details:
    print ("")

print (f"BLOCK STORAGE CONSUMPTION (boot volumes and block volumes) PER COMPARTMENT IN REGION {config['region']}: ",end="")
print (f"Total =  {total_gb_used} GBs = {total_gb_used/1024:.1f} TBs")
for cpt_id in gb_used_sorted.keys():
    cpt_name = get_cpt_name_from_id(cpt_id)
    gb = gb_used_sorted[cpt_id]
    print (f"- {gb:6d} GBs, {cpt_name} ")

# -- the end
exit (0)