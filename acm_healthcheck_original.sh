#!/bin/bash
#
# acm_heathcheck.sh
#
#*----------------------------------------------------------------------
#*
#* All software provided below is unsupported and provided as-is, without
#* warranty of any kind.
#*
#* To the extent possible under law, Red Hat, Inc. has dedicated all copyright
#* to this software to the public domain worldwide, pursuant to the CC0 Public
#* Domain Dedication. This software is distributed without any warranty.  See
#* <http://creativecommons.org/publicdomain/zero/1.0/>.
#*
#*----------------------------------------------------------------------
#*
#
# Author:      Ryan Spagnola (rspagnol AT redhat.com)
# Version:     1.0
# Description: This script is designed to read a customer provided must-gather and provide relevant details
#
# Usage:       This script is designed to be run in supportshell
#
# TODO:
#
#
# #####################################################################

### Varialbles ###
Esc="$( printf '\033' )"
_norm_="${Esc}[0m" #returns to "normal"
_bold_="${Esc}[0;1m" #set bold
_green_="${Esc}[0;32m" #set green
_yellow_="${Esc}[0;33m" #set yellow
_cyan_="${Esc}[0;36m" #set cyan
_red_="${Esc}[0;31m" #set red
_boldred_="${Esc}[0;1;31m" #set bold and red.

### Select case & must-gather ###
#cd ~
echo "Select case number"
select cnum in 0* ; do test -n "$cnum" && break; echo ">>> Invalid Selection"; done
cd "$cnum"; echo

echo "Select must-gather:"
select mg in *; do test -n "$mg" && break; echo ">>> Invalid Selection"; done
cd "$mg"; echo
DIR=$(pwd)

### Set OMG & OMC ToolS ###
omg use $DIR 1> /dev/null 2>&1;
omc use $DIR 1> /dev/null 2>&1;

### Validate must-gather ###
    if  find "$DIR" -type d -name "namespaces" 1> /dev/null 2>&1; then
        printf "${_bold_}Collecting environment details using must-gather: ${_norm_}\n"
        printf "$DIR" | awk -F "/" '{print $NF}'; echo
    else
        printf "${_red_}Not a valid must-gather${_norm_}\n"
        exit 1
    fi

NAMESPACES=$(find . -name 'namespaces' -type d)

### Validate ACM Hub must-gather directories ###
function ns_check () {
cd $DIR
NAMESPACES=$(find . -name 'namespaces' -type d)
arr=(
        "$NAMESPACES/multicluster-engine" \
        "$NAMESPACES/open-cluster-management" \
        "$NAMESPACES/open-cluster-management-addon-observability" \
        "$NAMESPACES/open-cluster-management-agent" \
        "$NAMESPACES/open-cluster-management-agent-addon" \
        "$NAMESPACES/open-cluster-management-observability" \
        )
for d in "${arr[@]}"; do
    if [ -d "$d" ]; then
        ACM_DIRS=${_cyan_}"All Present"
    else
        ACM_DIRS=${_red_}"Not all directories present"
        #printf "${_bold_}Namespaces directory check: ${_norm_}""${_red_}Not all directories present.${_norm_}\n\n"
    fi
done
    printf "${_bold_}Namespaces directory check: $ACM_DIRS${_norm_}\n\n"
}

### Product ###
    cd $DIR
    if  [[ $(find . -type f -name 'gather-acm.log') ]]; then
        MG_IMAGE=ACM
    else
        MG_IMAGE=OCP
    fi
    printf "${_bold_}Must-Gather Image: ${_norm_}${_cyan_}$MG_IMAGE${_norm_}\n"

### Hub or Managed Cluster ###
    cd $DIR
    if [[ $(find $NAMESPACES -name open-cluster-management-hub -type d) ]]; then
        HUB=Yes
    else
        HUB=No
    fi
printf "${_bold_}Hub Cluster: ${_norm_}${_cyan_}$HUB${_norm_}\n"

### Version ###
    if [[ $MG_IMAGE = ACM ]] && [[ $HUB = Yes  ]]; then
        cd $DIR
        if find $NAMESPACES/open-cluster-management/operators.coreos.com/subscriptions -type d 1> /dev/null 2>&1; then
        cd -- $NAMESPACES/open-cluster-management/operators.coreos.com/subscriptions
        ACM_VERSION=$(grep -i installedcsv *-cluster-management.yaml | grep -v '{' | awk -F "v" '{print $3}' | xargs)
        printf "${_bold_}ACM Version: ${_norm_}${_cyan_}$ACM_VERSION${_norm_}\n"
                else
                printf "${_bold_}ACM Version: ${_norm_}${_red_}ACM subscription directory not available${_norm_}\n"
                fi
            cd $DIR
            if find $NAMESPACES/multicluster-engine/operators.coreos.com/subscriptions -type d 1> /dev/null 2>&1; then
            cd -- $NAMESPACES/multicluster-engine/operators.coreos.com/subscriptions
            MCE_VERSION=$(grep -i installedcsv multicluster-engine.yaml | grep -v '{' | awk -F "v" '{print $2}' | xargs)
            printf "${_bold_}MCE Version: ${_norm_}${_cyan_}$MCE_VERSION${_norm_}\n"
            else
            printf "${_bold_}MCE Version: ${_norm_}${_red_}MCE subscription directory not available${_norm_}\n"
            fi
    else
        cd $DIR
        CLUSTER_SCOPED_RESOURCES=$(find . -name "cluster-scoped-resources" -type d)
        cd $CLUSTER_SCOPED_RESOURCES/config.openshift.io
        VERSION=$(grep -R "Cluster version is" clusterversions.yaml | sort -u | awk -F " " '{print $NF}')
        printf "${_bold_}OCP Version: ${_norm_}${_cyan_}$VERSION${_norm_}\n"
    fi

### Check ACM for Connected/Disconnected Environment ###
    function acm_connection () {
    cd $DIR
    if [[ $(find . -type d -name registry-redhat-io*) ]]; then
        ENV_TYPE=${_cyan_}Connected
    else
        ENV_TYPE=${_yellow_}Disconnected
    fi
    printf "${_bold_}Environment Type: $ENV_TYPE${_norm_}\n"; echo
}

### Check OCP for Connected/Disconnected Environment ###
    function ocp_connection () {
    ENV_TYPE_CHECK=$(grep image clusterversions.yaml | grep -v "{\|message" | awk -F ":" '{print $2}' | awk -F "/" '{print $1}' | sort -u | xargs)
    if [[ $ENV_TYPE_CHECK = quay.io ]]; then
         ENV_TYPE=${_cyan_}Connected
    else
         ENV_TYPE=${_yellow_}Disconnected
    fi
    printf "${_bold_}Environment Type: $ENV_TYPE${_norm_}\n"; echo
}

### OCP Cluster Platform ###
function cluster_platform () {
        printf "${_bold_}Cluster Platform: ${_norm_}"
        PLATFORM=$(grep 'platform:' infrastructures.yaml | grep -v "{" | awk -F ":" '{print $NF}' | xargs)
        printf ${_cyan_}$PLATFORM${_norm_}; echo
}

### MCH Operator Health ###
function mch_health () {
cd $DIR
MCH_DIR=$(find . -type d -name "multiclusterhubs")
cd $MCH_DIR
MCH_ARRAY=$(ls)
mch_yaml=$( printf '%s\n' "${MCH_ARRAY[@]}" )
CURRENT_VERSION=$(egrep "^\s currentVersion" $mch_yaml | awk '{print $NF}')
DESIRED_VERSION=$(egrep "^\s desiredVersion" $mch_yaml | awk '{print $NF}')
MCH_PHASE=$(egrep "^\s phase" $mch_yaml | awk '{print $NF}' | xargs)
BACKUP_ENABLED=$(egrep '^\s enableClusterBackup' $mch_yaml | awk '{print $NF}')
VERSION_CHECK="2.5.0"
if [ $CURRENT_VERSION == $DESIRED_VERSION ]; then
read -r -d '' MCH_HEALTH << EOM
Current Version: ${_green_}$CURRENT_VERSION${_norm_}
    Desired Version: ${_green_}$DESIRED_VERSION${_norm_}
EOM
else
read -r -d '' MCH_HEALTH << EOM
Current Version: ${_red_}$CURRENT_VERSION${_norm_}
    Desired Version: ${_red_}$DESIRED_VERSION${_norm_}
EOM
fi

printf "${_bold_}MCH Health: ${_norm_}\n""    $MCH_HEALTH\n"
    if [[ $MCH_PHASE = Running ]]; then
        printf "    Phase: ${_green_}$MCH_PHASE${_norm_}\n"
    else
        printf "    Phase: ${_red_}$MCH_PHASE${_norm_}\n"
    fi
printf "    Backup Enabled: ${_cyan_}$BACKUP_ENABLED${_norm_}\n"
  function version { echo "$@" | awk -F. '{ printf("%d%03d%03d%03d\n", $1,$2,$3,$4); }'; }
    if [[ $BACKUP_ENABLED = true ]]  && [[ $(version $CURRENT_VERSION) -le $(version $VERSION_CHECK) ]]; then
        printf "${_boldred_}    Warning!! Disable backup before upgrading to ACM 2.5${_norm_}\n"
    else
        :
    fi; echo
}

### MCE Health ###
function mce_health () {
cd $DIR
MCE_YAML=$(find "$CLUSTER_RESOURCES" -name "multiclusterengine.yaml")
CURRENT_VERSION=$(egrep "^\s currentVersion" $MCE_YAML | awk '{print $NF}')
DESIRED_VERSION=$(egrep "^\s desiredVersion" $MCE_YAML | awk '{print $NF}')
MCE_PHASE=$(egrep "^\s phase" $MCE_YAML | awk '{print $NF}' | xargs)
if [ $CURRENT_VERSION == $DESIRED_VERSION ]; then
read -r -d '' MCE_HEALTH << EOM
Current Version: ${_green_}$CURRENT_VERSION${_norm_}
    Desired Version: ${_green_}$DESIRED_VERSION${_norm_}
EOM
else
read -r -d '' MCH_HEALTH << EOM
Current Version: ${_red_}$CURRENT_VERSION${_norm_}
    Desired Version: ${_red_}$DESIRED_VERSION${_norm_}
EOM
fi

printf "${_bold_}MCE Health: ${_norm_}\n""    $MCE_HEALTH\n"
    if [[ $MCE_PHASE = Available ]]; then
        printf "    Phase: ${_green_}$MCE_PHASE${_norm_}\n"; echo
    else
        printf "    Phase: ${_red_}$MCE_PHASE${_norm_}\n"; echo
    fi
}

### Hub Cluster Details ###
function hub_details () {
    cd $DIR
    printf "${_bold_}Hub Cluster Details: ${_norm_}\n"
    if [ $(find . -name 'managedclusters' -type d) ]; then
      cd -- "$(find . -name 'managedclusters' -type d)"
      HUB_NAME=$(grep "url" local-cluster.yaml | grep -v consoleurl | awk -F '.' '{print $2}')
      HUB_CLUSTER_ID=$(grep "clusterID" local-cluster.yaml | grep -v {} | awk '{print $NF}')
      HUB_OCP_VERSION=$(grep "openshiftVersion" local-cluster.yaml | grep -v {} | grep -v \" | awk '{print $NF}')
      cd $DIR && cd -- "$(find . -path "*/namespaces/local-cluster/*/managedclusterinfos" -type d)"
      HUB_DESIRED_VERSION=$(grep "desiredVersion" local-cluster.yaml | grep -v {} | awk '{print $NF}')
      if [ $HUB_OCP_VERSION == $HUB_DESIRED_VERSION ]; then
      HUB_OCP_VERSION=${_green_}$HUB_OCP_VERSION${_norm_}
      HUB_DESIRED_VERSION=${_green_}$HUB_DESIRED_VERSION${_norm_}
      else
      HUB_OCP_VERSION=${_red_}$HUB_OCP_VERSION${_norm_}
      HUB_DESIRED_VERSION=${_red_}$HUB_DESIRED_VERSION${_norm_}
      fi
      CLOUDVENDOR=$(grep "cloudVendor" local-cluster.yaml | grep -v {} | awk '{print $NF}')
      MASTER_NODE_COUNT=$(grep "node-role.kubernetes.io/master" local-cluster.yaml | grep -v {} | wc -l | xargs)
      WORKER_NODE_COUNT=$(grep "node-role.kubernetes.io/worker" local-cluster.yaml | grep -v {} | wc -l | xargs)
      if [[ $MASTER_NODE_COUNT = "0" ]]; then
      cd $DIR && cd -- "$(find . -path "*/namespaces/open-cluster-management-agent/core" -type d)"
      MASTER_NODE_COUNT=$(grep "nodeName" pods.yaml | grep master | awk -F ":" '{print $2}' |sort -u | wc -l | xargs)
      WORKER_NODE_COUNT=$(grep "nodeName" pods.yaml | grep worker | awk -F ":" '{print $2}' |sort -u | wc -l | xargs)
      fi
      read -r -d '' HUB_DETAILS << EOM
        Cluster Name: ${_cyan_}$HUB_NAME${_norm_}
    ClusterID: ${_cyan_}$HUB_CLUSTER_ID${_norm_}
    OpenShift Version: $HUB_OCP_VERSION
    Desired Version: $HUB_DESIRED_VERSION
    Cluster Platform: ${_cyan_}$CLOUDVENDOR${_norm_}
    Control Plane Nodes: ${_cyan_}$MASTER_NODE_COUNT${_norm_}
    Compute Nodes: ${_cyan_}$WORKER_NODE_COUNT${_norm_}
EOM
        printf "    $HUB_DETAILS\n"; echo
      else
        printf "    ${_red_}Cluster Details Not Available.${_norm_}\n"; echo
      fi
}

### Managed Clusters Details ###
function managed_details () {
cd $DIR
echo -e "${_bold_}Managed Clusters Details: ${_norm_}"
cd -- "$(find . -name 'cluster-scoped-resources' -type d)"
MANAGED_COUNT=$(ls cluster.open-cluster-management.io/managedclusters | wc -l | xargs)
#MANAGED_COUNT=$(grep -rvi "the\|name\|version" * --include gather-managed.log | wc -l | xargs)
cd $DIR
echo -ne "    Number of Managed Clusters: ${_cyan_}$MANAGED_COUNT${_norm_}\n\n"
}

### Insights ###
        cd $DIR
        if [[ $MG_IMAGE = ACM  ]]; then
          printf "${_bold_}Insights rule check: ${_norm_}\n"
          insights run -p ccx_rules_ocp.internal.cloud_management .; echo
        else
          printf "${_bold_}Insights rule check: ${_norm_}\n"
          insights run -p ccx_rules_ocp.common.conditions .; echo
        fi

### Addons status ###
function addon_status () {
echo -e "${_bold_}Addons Status: ${_norm_}\n"
cd $DIR
ADDON_DIR=$(find . -name open-cluster-management-agent-addon -type d)
ADDON_PODS_DIR=${ADDON_DIR}/pods
    if [ -d "${ADDON_PODS_DIR}" ]; then
        (cd -- "${ADDON_PODS_DIR}" 1> /dev/null 2>&1;
        ADDON_PODS=(*/*.yaml)
        for FILE in "${ADDON_PODS[@]}"; do
        echo -n "    Name:  ${_cyan_}" ; egrep '^\s name:' $FILE | awk -F ":" '{print $NF}' | xargs;
        ADDON_PHASE=$(egrep '^\s phase' $FILE | awk -F ":" '{print $NF}')
          if [ $ADDON_PHASE == "Running" ]; then
             printf "    ${_norm_}Phase: ${_green_}$ADDON_PHASE${_norm_}\n\n"
          else
             ADDON_MESSAGE=$(grep message $FILE | grep -v "{" | sort -u | awk -F ":" '{$1=""; print $0}' | xargs)
             printf "    ${_norm_}Phase: ${_red_}$ADDON_PHASE${_norm_}\n"
             printf "    Info: ${_red_}$ADDON_MESSAGE${_norm_}\n\n"
          fi
         done)
    else
      echo "    ${_red_}Error: Directory open-cluster-management-agent-addon/pods does not exist.${_norm_}"
    fi; echo
}

### Klusterlet status ###
function klusterlet_status () {
cd $DIR
KLUSTERLET_DIR=$(find . -name open-cluster-management-agent -type d)
KLUSTERLET_PODS_DIR=${KLUSTERLET_DIR}/pods
echo -e "${_bold_}ACM Klusterlet Status: ${_norm_}\n"
    if [ -d "$KLUSTERLET_PODS_DIR" ]; then
       (cd -- "${KLUSTERLET_PODS_DIR}" 1> /dev/null 2>&1;
       KLUSTERLET_PODS=(*/*.yaml)
       for FILE in "${KLUSTERLET_PODS[@]}"; do
       echo -n "    Name:  ${_cyan_}" ; egrep '^\s name:' $FILE | awk -F ":" '{print $2}' | xargs;
       KLUSTERLET_PHASE=$(egrep '^\s phase' $FILE | awk -F ":" '{print $2}')
         if [ $KLUSTERLET_PHASE == "Running" ]; then
            printf "    ${_norm_}Phase: ${_green_}$KLUSTERLET_PHASE${_norm_}\n\n"
         else
            KLUSTERLET_MESSAGE=$(grep message $FILE | grep -v "{" | sort -u | awk -F ":" '{$1=""; print $0}' | xargs)
            printf "    ${_norm_}Phase: ${_red_}$KLUSTERLET_PHASE${_norm_}\n"
            printf "    Info: ${_red_}$KLUSTERLET_MESSAGE${_norm_}\n\n"
         fi
        done)
    else
      echo "    ${_red_}Error: Directory open-cluster-management-agent/pods does not exist.${_norm_}"
    fi; echo
}

### Observability ###
function observability () {
cd $DIR
OBSERVABILITY_OPERATOR=$(find . -name open-cluster-management-observability -type d)
cd $OBSERVABILITY_OPERATOR
OBSERVABILITY_OPERATOR_YAML=$(find . -name open-cluster-management-observability.yaml)
OBSERVABILITY_OPERATOR_STATUS=$(less $OBSERVABILITY_OPERATOR_YAML | grep "phase:" | grep -v {} | awk -F ":" '{print $2}' | xargs)

cd $DIR
MULTICLUSTER_OBSERVABILITY_OPERATOR=$(find . -name multicluster-observability-operator-* -type d)
cd $MULTICLUSTER_OBSERVABILITY_OPERATOR
MULTICLUSTER_OBSERVABILITY_OPERATOR_YAML=$(find . -name multicluster-observability-operator*.yaml)
MULTICLUSTER_OBSERVABILITY_OPERATOR_STATUS=$(less $MULTICLUSTER_OBSERVABILITY_OPERATOR_YAML | grep "phase:" | grep -v {} | awk -F ":" '{print $2}' | xargs)

cd $DIR
ENDPOINT_OBSERVABILITY_OPERATOR=$(find . -name endpoint-observability-operator-* -type d)
cd $ENDPOINT_OBSERVABILITY_OPERATOR
ENDPOINT_OBSERVABILITY_OPERATOR_YAML=$(find . -name endpoint-observability-operator*.yaml)
ENDPOINT_OBSERVABILITY_OPERATOR_STATUS=$(less $ENDPOINT_OBSERVABILITY_OPERATOR_YAML | grep "phase:" | grep -v {} | awk -F ":" '{print $2}' | xargs)

cd $DIR
METRICS_COLLECTOR_DEPLOYMENT=$(find . -name metrics-collector-deployment-* -type d)
cd $METRICS_COLLECTOR_DEPLOYMENT
METRICS_COLLECTOR_DEPLOYMENT_YAML=$(find . -name metrics-collector-deployment*.yaml)
METRICS_COLLECTOR_DEPLOYMENT_STATUS=$(less $METRICS_COLLECTOR_DEPLOYMENT_YAML | grep "phase:" | grep -v {} | awk -F ":" '{print $2}' | xargs)

cd $DIR
THANOS_COMPACTOR=$(find . -name observability-thanos-compact-0 -type d)
cd $THANOS_COMPACTOR
THANOS_COMPACTOR_YAML=$(find . -name observability-thanos-compact-0.yaml)
THANOS_COMPACTOR_PVC=$(less $THANOS_COMPACT_YAML | grep "claimName:" | grep -v {} | awk -F ":" '{print $2}' | xargs)
cd thanos-compact/thanos-compact/logs/
THANOS_COMPACTOR_ERROR=$(less current.log | grep -i "level=error" | awk -F ":" '{print substr($NF, 1, length($NF)-1)}' | uniq)
THANOS_COMPACTOR_HALTED=$(less current.log | grep -i "halted")
THANOS_COMPACTOR_INVALID_NUM=$(less current.log | grep -i "invalid magic number")
THANOS_COMPACTOR_NO_SPACE=$(less current.log | grep -i "no space left on device")
THANOS_COMPACTOR_CONN_REFUSED=$(less current.log | grep -i "connection refused")
THANOS_COMPACTOR_S3_QUOTA_EXCEEDED=$(less current.log | grep -i "upload s3 object: Check if quota has been exceeded")

printf "${_bold_}Observability:\n${_norm_}"
if [[ $OBSERVABILITY_OPERATOR_STATUS == "Active" ]]; then
    printf "    Observability Status: ${_green_}Active${_norm_}"; echo

    if [ $MULTICLUSTER_OBSERVABILITY_OPERATOR_STATUS == "Running" ]; then
        printf "    Multicluster Observability Operator Status: ${_green_}$MULTICLUSTER_OBSERVABILITY_OPERATOR_STATUS${_norm_}"; echo
    else
        printf "    Multicluster Observability Operator Status: ${_red_}$MULTICLUSTER_OBSERVABILITY_OPERATOR_STATUS${_norm_}"; echo
    fi

    if [[ $ENDPOINT_OBSERVABILITY_OPERATOR_STATUS == "Running" ]]; then
        printf "    Endpoint Observability Operator Status: ${_green_}$ENDPOINT_OBSERVABILITY_OPERATOR_STATUS${_norm_}"; echo
    else
        printf "    Endpoing Observability Operator Status: ${_red_}$ENDPOINT_OBSERVABILITY_OPERATOR_STATUS${_norm_}"; echo
    fi

    if [[ $METRICS_COLLECTOR_DEPLOYMENT_STATUS == "Running" ]]; then
        printf "    Metrics Collector Deployment Status: ${_green_}$METRICS_COLLECTOR_DEPLOYMENT_STATUS${_norm_}"; echo
    else
        printf "    Metrics Collector Deployment Status: ${_red_}$METRICS_COLLECTOR_DEPLOYMENT_STATUS${_norm_}"; echo
    fi

    if [[ -n $THANOS_COMPACTOR_ERROR ]]; then
        printf "    Compactor Health: ${_red_}Errors Detected "; echo
    else
        printf "    Compactor Health: ${_green_}OK${_norm_}"; echo
    fi

    if [[ -n $THANOS_COMPACTOR_HALTED ]]; then
        printf "        Compactor Halted"; echo
    else
        :
    fi
    if [[ -n $THANOS_COMPACTOR_INVALID_NUM ]]; then
        printf "        Invalid Magic Number Error"; echo
    else
        :
    fi
    if [[ -n $THANOS_COMPACTOR_NO_SPACE ]]; then
        printf "        No Space Left On Device"; echo
    else
        :
    fi
    if [[ -n $THANOS_COMPACTOR_CONN_REFUSED ]]; then
        printf "        Connection Refused"; echo
    else
        :
    fi
    if [[ -n $THANOS_COMPACTOR_S3_QUOTA_EXCEEDED ]]; then
        printf "        Upload to S3 failed. Check if quota has been exceeded"; echo
    else
        :
    fi

    echo

else
    printf "    Observability Status: ${_yellow_}Inactive${_norm_}\n"; echo
fi

printf "${_bold_}Observability Pods:${_norm_}"; echo
OBSERVABILITY_PODS=$(omc get pods -n open-cluster-management-observability | sed 's/^/    /')
printf "$OBSERVABILITY_PODS\n\n"

printf "${_bold_}Observability Pods With Errors:${_norm_}"; echo
OBSERVABILITY_PODS_ERROR=$(omc get pods -n open-cluster-management-observability | grep observability | grep -v Running |  awk -F " " '{ print $1 }' | sed 's/^/    /')
printf "$OBSERVABILITY_PODS_ERROR\n"

cd $DIR
for each in "${OBSERVABILITY_PODS_ERROR[@]}"; do
    POD_ERROR=$(find . -name "$each".yaml -exec grep msg '{}' \;)
    printf "$POD_ERROR\n"
done
}

### PodCount per ACM Namespace ###
function acm_pod_ct () {
cd $DIR
NAMESPACES=$(find . -name namespaces -type d)
cd $NAMESPACES
echo -e "${_bold_}ACM Namespaces Pod Count:${_norm_}"
OCM_NS=(open-cluster-management)
OCM_AGENT_NS=(open-cluster-management-agent*)
OCM_HUB_NS=(open-cluster-management-hub)
OCM_OBSERV_NS=(open-cluster-management*observability)
MCE_NS=(multicluster-engine)
for COUNT in "${OCM_NS[@]}" "${OCM_HUB_NS[@]}" "${OCM_AGENT_NS[@]}" "${OCM_OBSERV_NS[@]}" "${MCE_NS[@]}"; do
        PODCOUNT=$(find "$COUNT"/pods -mindepth 1 -maxdepth 1 -type d 2> /dev/null | wc -l | xargs)
        echo -n "    $COUNT: " ; $PODCOUNT 2>/dev/null
        if [ $PODCOUNT -gt 0 ]; then
            printf "${_cyan_}$PODCOUNT${_norm_}\n"
        else
            printf "${_red_}$PODCOUNT${_norm_}\n"
        fi
done; echo
}

### Pods in error or unknown state ###
function pods_error () {
printf "${_bold_}Pods in error state on cluster:${_norm_}\n"
ERROR_PODS=$(omc get pods -A | grep -vi "Running\|Succeeded\|Phase\|Version\|Completed" | sed 's/^/    /')
printf "$ERROR_PODS\n"; echo

printf "${_bold_}Pods with restarts greater than 10 on cluster:${_norm_}\n"
RESTART_PODS=$(omc get pods -A | awk '$5 > 10  {print ;}' | sed 's/^/    /')
printf "$RESTART_PODS\n"; echo

}

### etcd status ###
function etcd_status () {
printf "${_bold_}ETCD Status:${_norm_}\n"
omc etcd status | sed 's/^/    /'; echo
printf "${_bold_}ETCD Pods:${_norm_}\n"
omc get pods -o wide -l app=etcd -n openshift-etcd | sed 's/^/    /'; echo

}

### Alerts firing ###
function alerts () {
ALERTS_FIRING=$(omc alert rule -s firing,pending -o wide | awk '$5 > 1 {print ;}' | sed 's/^/    /')
printf "${_bold_}Repeated alerts firing:${_norm_}\n$ALERTS_FIRING\n"; echo
}

### OCP Nodes ###
function nodes () {
printf "${_bold_}Cluster Nodes:${_norm_}\n"
omc get nodes | sed 's/^/    /'; echo
}

### Events ###
function events () {
printf "${_bold_}Events:${_norm_}\n"
omc get events | sed 's/^/    /'; echo
}

##################################################
##################################################

### Hub Cluster ###
    if [[ $HUB = Yes ]] && [[ $MG_IMAGE = ACM ]]; then
      acm_connection
      mch_health
      hub_details
      ns_check
      managed_details
      acm_pod_ct
      observability
      addon_status
      klusterlet_status
      pods_error
    else
      :
    fi

### Managed Cluster ###
    if [[ $HUB = No ]] && [[ $MG_IMAGE = ACM ]]; then
      ocp_connection
      addon_status
      klusterlet_status
      pods_error
    else
      :
    fi

### OCP Cluster ###
    if [[ $MG_IMAGE = OCP ]]; then
      cluster_platform
      ocp_connection
      etcd_status
      nodes
      alerts
      events
      pods_error
    else
      :
    fi