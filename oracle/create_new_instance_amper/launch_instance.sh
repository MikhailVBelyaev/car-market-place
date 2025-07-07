#!/bin/bash

# Configuration
JSON_FILE="instance-config.json"
COMPARTMENT_ID="ocid1.tenancy.oc1..aaaaaaaajeyct7efelj4bhwom5pnee4one3mtbjbrmdm7tqpfhfi56mz2eya"
SUBNET_ID="ocid1.subnet.oc1.iad.aaaaaaaas52hzdvziti5oegymjbzezlu5sccevo5kuf5jvmyn4w4yhzpsbwa"
AVAILABILITY_DOMAINS=("zBpp:US-ASHBURN-AD-1" "zBpp:US-ASHBURN-AD-2" "zBpp:US-ASHBURN-AD-3")
RETRY_INTERVAL=30 # 5 minutes in seconds
MAX_ATTEMPTS=1200    # Try for ~1 hour (12 attempts * 5 minutes)
LOG_FILE="launch_instance.log"

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Verify CLI version
CLI_VERSION=$(oci --version 2>/dev/null)
if [[ "$CLI_VERSION" == "3.62.0" ]]; then
    log "WARNING: CLI version 3.62.0 detected, which has known bugs. Attempting to upgrade..."
    pip install oci-cli --upgrade
    NEW_CLI_VERSION=$(oci --version 2>/dev/null)
    log "CLI upgraded to version: $NEW_CLI_VERSION"
else
    log "CLI version: $CLI_VERSION"
fi

# Verify jq is installed
if ! command -v jq &> /dev/null; then
    log "ERROR: jq is not installed. Please install jq to proceed."
    exit 1
fi

# Verify instance-config.json exists
if [ ! -f "$JSON_FILE" ]; then
    log "ERROR: $JSON_FILE not found."
    exit 1
fi

# Function to update availability domain in JSON file
update_availability_domain() {
    local ad=$1
    jq ".availabilityDomain = \"$ad\"" "$JSON_FILE" > tmp.json && mv tmp.json "$JSON_FILE"
    log "Updated $JSON_FILE with availabilityDomain: $ad"
}

# Main loop
attempt=1
while [ $attempt -le $MAX_ATTEMPTS ]; do
    log "Attempt $attempt of $MAX_ATTEMPTS"

    for ad in "${AVAILABILITY_DOMAINS[@]}"; do
        log "Trying availability domain: $ad"
        update_availability_domain "$ad"

        # Launch instance
        oci compute instance launch --from-json file://"$JSON_FILE" \
          --subnet-id "$SUBNET_ID" \
          --debug > debug_tmp.log 2>&1
        EXIT_CODE=$?

        # Check if launch was successful
        if [ $EXIT_CODE -eq 0 ]; then
            log "Instance launched successfully in $ad"
            INSTANCE_OCID=$(jq -r '.data.id' debug_tmp.log)
            log "Instance OCID: $INSTANCE_OCID"
            PUBLIC_IP=$(oci compute instance list-vnics --instance-id "$INSTANCE_OCID" | jq -r '.data[] | select(.publicIp != null) | .publicIp')
            log "Public IP: $PUBLIC_IP"
            cat debug_tmp.log >> "$LOG_FILE"
            rm debug_tmp.log
            exit 0
        else
            # Check for specific errors
            if grep -q "Out of host capacity" debug_tmp.log; then
                log "Out of host capacity in $ad"
            elif grep -q "CannotParseRequest" debug_tmp.log; then
                log "CannotParseRequest error. CLI bug or configuration issue."
            elif grep -q "InternalError" debug_tmp.log; then
                log "InternalError (possibly capacity-related) in $ad"
            else
                log "Unexpected error in $ad"
            fi
            cat debug_tmp.log >> "$LOG_FILE"
        fi
    done

    log "No capacity in any availability domain. Retrying in $RETRY_INTERVAL seconds..."
    attempt=$((attempt + 1))
    sleep $RETRY_INTERVAL
done

log "Failed to launch instance after $MAX_ATTEMPTS attempts."
cat debug_tmp.log >> "$LOG_FILE"
rm debug_tmp.log
exit 1